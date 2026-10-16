from __future__ import annotations

import typing
from dataclasses import dataclass, field
from functools import lru_cache

import jsonpath_rfc9535
from flag_engine import engine
from flag_engine.context.types import SegmentContext, SegmentRule
from jsonpath_rfc9535.segments import JSONPathChildSegment
from jsonpath_rfc9535.selectors import NameSelector

from flagsmith.analytics import AnalyticsProcessor
from flagsmith.exceptions import FlagsmithFeatureDoesNotExistError
from flagsmith.types import (
    FeatureMetadata,
    SDKEvaluationContext,
    SDKEvaluationResult,
    SDKFlagResult,
    SegmentMetadata,
)

SegmentOverridesIndex = typing.Dict[
    str, typing.Dict[str, SegmentContext[SegmentMetadata, FeatureMetadata]]
]


def build_segment_overrides_index(
    context: SDKEvaluationContext,
) -> SegmentOverridesIndex:
    """Map feature_name -> segments that carry an override for that feature.

    Computed once per environment-document refresh so the lazy eval path
    can walk only the segments actually relevant to a given flag.

    Each entry keeps the context's own segment keys, so the trimmed
    contexts built by `Flags._resolve_flag` stay a faithful subset of
    the environment. Re-keying them by anything else risks collisions
    silently dropping segments.
    """
    index: SegmentOverridesIndex = {}
    for segment_key, segment_context in (context.get("segments") or {}).items():
        for override in segment_context.get("overrides") or ():
            index.setdefault(override["name"], {})[segment_key] = segment_context
    return index


@lru_cache(maxsize=1024)
def _property_may_read_flags(condition_property: str) -> bool:
    """Whether a condition property may read the engine's `$.flags`.

    Mirrors how the engine reads properties: only those starting with
    `$.` that compile as JSONPath are queried against the context;
    anything else is a trait key. The compiled query is then checked
    the way the engine would run it, rather than by pattern matching.

    Errs on the side of `True`: a false positive only costs a
    full-context evaluation, whereas a false negative would evaluate a
    flag without its dependencies. So the property is ruled out only
    when its first segment selects top-level keys by name, none of them
    `flags`. Wildcards, filters, indices and descendant segments
    (`$..`) are all assumed to reach `flags`.
    """
    if not condition_property.startswith("$."):
        return False
    try:
        query = jsonpath_rfc9535.compile(condition_property)
    except jsonpath_rfc9535.JSONPathSyntaxError:
        return False
    if not query.segments:
        return False
    first_segment = query.segments[0]
    return not (
        type(first_segment) is JSONPathChildSegment
        and all(
            isinstance(selector, NameSelector) and selector.name != "flags"
            for selector in first_segment.selectors
        )
    )


def _rules_read_flags(rules: typing.Iterable[SegmentRule]) -> bool:
    return any(
        any(
            _property_may_read_flags(condition.get("property") or "")
            for condition in rule.get("conditions") or ()
        )
        or _rules_read_flags(rule.get("rules") or ())
        for rule in rules
    )


def build_flag_dependent_feature_names(
    context: SDKEvaluationContext,
) -> typing.FrozenSet[str]:
    """Names of features overridden by a segment with a `$.flags` condition.

    Such a feature depends on other flags, which the engine resolves
    from the context's features and segments. The trimmed contexts used
    by `Flags._resolve_flag` leave those out, so these features are
    resolved against the full context instead.
    """
    return frozenset(
        override["name"]
        for segment_context in (context.get("segments") or {}).values()
        if _rules_read_flags(segment_context["rules"])
        for override in segment_context.get("overrides") or ()
    )


@dataclass(frozen=True)
class ExperimentMetadata:
    """The running experiment a flag was evaluated under; identity evaluations only."""

    id: int
    name: str
    in_experiment: bool

    @classmethod
    def from_api_metadata(
        cls,
        metadata: typing.Optional[typing.Mapping[str, typing.Any]],
    ) -> typing.Optional[ExperimentMetadata]:
        if not metadata or not (experiment := metadata.get("experiment")):
            return None
        return cls(
            id=experiment["id"],
            name=experiment["name"],
            in_experiment=experiment["in_experiment"],
        )


@dataclass
class BaseFlag:
    enabled: bool
    value: typing.Union[str, int, float, bool, None]


@dataclass
class DefaultFlag(BaseFlag):
    is_default: bool = field(default=True)


@dataclass
class Flag(BaseFlag):
    feature_id: int
    feature_name: str
    variant: typing.Optional[str] = None
    reason: typing.Optional[str] = None
    is_default: bool = field(default=False)
    experiment: typing.Optional[ExperimentMetadata] = None

    @classmethod
    def from_evaluation_result(
        cls,
        flag_result: SDKFlagResult,
    ) -> Flag:
        if metadata := flag_result.get("metadata"):
            return Flag(
                enabled=flag_result["enabled"],
                value=flag_result["value"],
                feature_name=flag_result["name"],
                feature_id=metadata["id"],
                variant=flag_result.get("variant"),
                reason=flag_result["reason"],
            )
        raise ValueError(
            "FlagResult metadata is missing. Cannot create Flag instance. "
            "This means a bug in the SDK, please report it."
        )

    @classmethod
    def from_api_flag(cls, flag_data: typing.Mapping[str, typing.Any]) -> Flag:
        return Flag(
            enabled=flag_data["enabled"],
            value=flag_data["feature_state_value"],
            feature_name=flag_data["feature"]["name"],
            feature_id=flag_data["feature"]["id"],
            variant=flag_data.get("variant"),
            reason=flag_data.get("reason"),
            experiment=ExperimentMetadata.from_api_metadata(flag_data.get("metadata")),
        )


@dataclass
class Flags:
    flags: typing.Dict[str, Flag] = field(default_factory=dict)
    default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]] = None
    _analytics_processor: typing.Optional[AnalyticsProcessor] = None
    # Lazy-evaluation state. When `_context` is set, `flags` is a
    # per-feature memo rather than a fully-materialised snapshot; unseen
    # features are resolved on demand via the engine primitives and
    # cached back into `flags`. Left as `None` by the eager code
    # paths (`from_evaluation_result` / `from_api_flags`).
    _context: typing.Optional[SDKEvaluationContext] = None
    _overrides_index: typing.Optional[SegmentOverridesIndex] = None
    _flag_dependent_features: typing.FrozenSet[str] = frozenset()
    _fully_materialised: bool = False

    @classmethod
    def from_evaluation_result(
        cls,
        evaluation_result: SDKEvaluationResult,
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
    ) -> Flags:
        return cls(
            flags={
                flag_name: flag
                for flag_name, flag_result in evaluation_result["flags"].items()
                if (flag := Flag.from_evaluation_result(flag_result))
            },
            default_flag_handler=default_flag_handler,
            _analytics_processor=analytics_processor,
        )

    @classmethod
    def from_evaluation_context(
        cls,
        context: SDKEvaluationContext,
        overrides_index: SegmentOverridesIndex,
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
        flag_dependent_features: typing.Optional[typing.FrozenSet[str]] = None,
    ) -> Flags:
        """Build a lazy `Flags` backed by an evaluation context.

        No engine work is done here — flags are resolved on first access
        via :meth:`_resolve_flag`. Reusing the same `overrides_index`
        and `flag_dependent_features` across calls amortises their
        construction cost (they're rebuilt only when the environment doc
        refreshes, not per identity). When `flag_dependent_features` is
        omitted, it is derived from `context`.
        """
        if flag_dependent_features is None:
            flag_dependent_features = build_flag_dependent_feature_names(context)
        return cls(
            flags={},
            default_flag_handler=default_flag_handler,
            _analytics_processor=analytics_processor,
            _context=context,
            _overrides_index=overrides_index,
            _flag_dependent_features=flag_dependent_features,
        )

    @classmethod
    def from_api_flags(
        cls,
        api_flags: typing.Sequence[typing.Mapping[str, typing.Any]],
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
    ) -> Flags:
        flags = {
            flag_data["feature"]["name"]: Flag.from_api_flag(flag_data)
            for flag_data in api_flags
        }

        return cls(
            flags=flags,
            default_flag_handler=default_flag_handler,
            _analytics_processor=analytics_processor,
        )

    def all_flags(self) -> typing.List[Flag]:
        """
        Get a list of all Flag objects.

        In lazy mode, the caller has signalled they want every flag, so
        we run the bulk evaluator once on the full context and copy the
        results into the per-flag cache. Cheaper than asking the engine
        for each feature one at a time.

        :return: list of Flag objects.
        """
        if self._context is not None and not self._fully_materialised:
            self._materialise_all()
        return list(self.flags.values())

    def _materialise_all(self) -> None:
        assert self._context is not None
        result = engine.get_evaluation_result(self._context)
        for feature_name, flag_result in result["flags"].items():
            if feature_name not in self.flags:
                self.flags[feature_name] = Flag.from_evaluation_result(
                    flag_result,
                )
        self._fully_materialised = True

    def is_feature_enabled(self, feature_name: str) -> bool:
        """
        Check whether a given feature is enabled.

        :param feature_name: the name of the feature to check if enabled.
        :return: Boolean representing the enabled state of a given feature.
        :raises FlagsmithClientError: if feature doesn't exist
        """
        return self.get_flag(feature_name).enabled

    def get_feature_value(self, feature_name: str) -> typing.Any:
        """
        Get the value of a particular feature.

        :param feature_name: the name of the feature to retrieve the value of.
        :return: the value of the given feature.
        :raises FlagsmithClientError: if feature doesn't exist
        """
        return self.get_flag(feature_name).value

    def get_flag(self, feature_name: str) -> typing.Union[DefaultFlag, Flag]:
        """
        Get a specific flag given the feature name.

        :param feature_name: the name of the feature to retrieve the flag for.
        :return: DefaultFlag | Flag object.
        :raises FlagsmithClientError: if feature doesn't exist
        """
        try:
            flag = self.flags[feature_name]
        except KeyError:
            # Lazy path: if this `Flags` wraps an evaluation context and
            # the feature exists in it, resolve and memoise now. Otherwise
            # fall through to the default_flag_handler / not-found error,
            # preserving the eager-mode behaviour byte-for-byte.
            if (
                self._context is not None
                and self._overrides_index is not None
                and feature_name in (self._context.get("features") or {})
            ):
                flag = self._resolve_flag(feature_name)
                self.flags[feature_name] = flag
            elif self.default_flag_handler:
                return self.default_flag_handler(feature_name)
            else:
                raise FlagsmithFeatureDoesNotExistError(
                    "Feature does not exist: %s" % feature_name
                )

        if self._analytics_processor and hasattr(flag, "feature_name"):
            self._analytics_processor.track_feature(flag.feature_name)

        return flag

    def _resolve_flag(self, feature_name: str) -> Flag:
        """Evaluate a single feature against the lazy context.

        Goes through the engine's public `get_evaluation_result` so
        identity-key enrichment, multivariate hashing, percentage-split
        rules and override-priority handling all stay where they
        belong (in the engine). The performance win comes from passing
        a *trimmed* context — just the queried feature plus the segments
        that could override it, looked up in O(1) via the precomputed
        reverse index — so the engine's full pipeline runs against an
        input small enough to evaluate in ~1 µs.

        Features overridden by a segment with a `$.flags` condition
        depend on other flags, which a trimmed context would leave out,
        so they are resolved with the full context instead. Every flag
        that evaluation yields is memoised.
        """
        context = self._context
        overrides_index = self._overrides_index
        # `get_flag` / `all_flags` gate this call behind the same
        # non-None checks; assert here so type checkers can narrow.
        assert context is not None and overrides_index is not None

        if feature_name in self._flag_dependent_features:
            self._materialise_all()
            return self.flags[feature_name]

        trimmed: SDKEvaluationContext = {
            **context,
            "features": {feature_name: context["features"][feature_name]},
            "segments": overrides_index.get(feature_name, {}),
        }
        result = engine.get_evaluation_result(trimmed)
        return Flag.from_evaluation_result(result["flags"][feature_name])


@dataclass
class Segment:
    id: int
    name: str
