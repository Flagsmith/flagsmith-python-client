from __future__ import annotations

import typing
from dataclasses import dataclass, field

from flag_engine import engine
from flag_engine.context.types import SegmentContext

from flagsmith.analytics import AnalyticsProcessor, PipelineAnalyticsProcessor
from flagsmith.exceptions import FlagsmithFeatureDoesNotExistError
from flagsmith.types import (
    FeatureMetadata,
    SDKEvaluationContext,
    SDKEvaluationResult,
    SDKFlagResult,
    SegmentMetadata,
)

SegmentOverridesIndex = typing.Dict[
    str, typing.List[SegmentContext[SegmentMetadata, FeatureMetadata]]
]


def build_segment_overrides_index(
    context: SDKEvaluationContext,
) -> SegmentOverridesIndex:
    """Map feature_name -> segments that carry an override for that feature.

    Computed once per environment-document refresh so the lazy eval path
    can walk only the segments actually relevant to a given flag.
    """
    index: SegmentOverridesIndex = {}
    for segment_context in (context.get("segments") or {}).values():
        for override in segment_context.get("overrides") or ():
            index.setdefault(override["name"], []).append(segment_context)
    return index


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
    is_default: bool = field(default=False)

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
        )


@dataclass
class Flags:
    flags: typing.Dict[str, Flag] = field(default_factory=dict)
    default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]] = None
    _analytics_processor: typing.Optional[AnalyticsProcessor] = None
    _pipeline_analytics_processor: typing.Optional[PipelineAnalyticsProcessor] = None
    _identity_identifier: typing.Optional[str] = None
    _traits: typing.Optional[typing.Dict[str, typing.Any]] = None
    # Lazy-evaluation state. When ``_context`` is set, ``flags`` is a
    # per-feature memo rather than a fully-materialised snapshot; unseen
    # features are resolved on demand via the engine primitives and
    # cached back into ``flags``. Left as ``None`` by the eager code
    # paths (``from_evaluation_result`` / ``from_api_flags``).
    _context: typing.Optional[SDKEvaluationContext] = None
    _overrides_index: typing.Optional[SegmentOverridesIndex] = None
    _fully_materialised: bool = False

    @classmethod
    def from_evaluation_result(
        cls,
        evaluation_result: SDKEvaluationResult,
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
        pipeline_analytics_processor: typing.Optional[
            PipelineAnalyticsProcessor
        ] = None,
        identity_identifier: typing.Optional[str] = None,
        traits: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> Flags:
        return cls(
            flags={
                flag_name: flag
                for flag_name, flag_result in evaluation_result["flags"].items()
                if (flag := Flag.from_evaluation_result(flag_result))
            },
            default_flag_handler=default_flag_handler,
            _analytics_processor=analytics_processor,
            _pipeline_analytics_processor=pipeline_analytics_processor,
            _identity_identifier=identity_identifier,
            _traits=traits,
        )

    @classmethod
    def from_evaluation_context(
        cls,
        context: SDKEvaluationContext,
        overrides_index: SegmentOverridesIndex,
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
        pipeline_analytics_processor: typing.Optional[
            PipelineAnalyticsProcessor
        ] = None,
        identity_identifier: typing.Optional[str] = None,
        traits: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> Flags:
        """Build a lazy ``Flags`` backed by an evaluation context.

        No engine work is done here — flags are resolved on first access
        via :meth:`_resolve_flag`. Reusing the same ``overrides_index``
        across calls amortises its construction cost (it's rebuilt only
        when the environment doc refreshes, not per identity).
        """
        return cls(
            flags={},
            default_flag_handler=default_flag_handler,
            _analytics_processor=analytics_processor,
            _pipeline_analytics_processor=pipeline_analytics_processor,
            _identity_identifier=identity_identifier,
            _traits=traits,
            _context=context,
            _overrides_index=overrides_index,
        )

    @classmethod
    def from_api_flags(
        cls,
        api_flags: typing.Sequence[typing.Mapping[str, typing.Any]],
        analytics_processor: typing.Optional[AnalyticsProcessor],
        default_flag_handler: typing.Optional[typing.Callable[[str], DefaultFlag]],
        pipeline_analytics_processor: typing.Optional[
            PipelineAnalyticsProcessor
        ] = None,
        identity_identifier: typing.Optional[str] = None,
        traits: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> Flags:
        flags = {
            flag_data["feature"]["name"]: Flag.from_api_flag(flag_data)
            for flag_data in api_flags
        }

        return cls(
            flags=flags,
            default_flag_handler=default_flag_handler,
            _analytics_processor=analytics_processor,
            _pipeline_analytics_processor=pipeline_analytics_processor,
            _identity_identifier=identity_identifier,
            _traits=traits,
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
            result = engine.get_evaluation_result(self._context)
            for feature_name, flag_result in result["flags"].items():
                if feature_name not in self.flags:
                    self.flags[feature_name] = Flag.from_evaluation_result(
                        flag_result,
                    )
            self._fully_materialised = True
        return list(self.flags.values())

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
            # Lazy path: if this ``Flags`` wraps an evaluation context and
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

        if self._pipeline_analytics_processor and hasattr(flag, "feature_name"):
            self._pipeline_analytics_processor.record_evaluation_event(
                flag_key=flag.feature_name,
                enabled=flag.enabled,
                value=flag.value,
                identity_identifier=self._identity_identifier,
                traits=self._traits,
            )

        return flag

    def _resolve_flag(self, feature_name: str) -> Flag:
        """Evaluate a single feature against the lazy context.

        Goes through the engine's public ``get_evaluation_result`` so
        identity-key enrichment, multivariate hashing, percentage-split
        rules and override-priority handling all stay where they
        belong (in the engine). The performance win comes from passing
        a *trimmed* context — just the queried feature plus the segments
        that could override it, looked up in O(1) via the precomputed
        reverse index — so the engine's full pipeline runs against an
        input small enough to evaluate in ~1 µs.
        """
        context = self._context
        overrides_index = self._overrides_index
        # ``get_flag`` / ``all_flags`` gate this call behind the same
        # non-None checks; assert here so type checkers can narrow.
        assert context is not None and overrides_index is not None

        trimmed: SDKEvaluationContext = {
            **context,
            "features": {feature_name: context["features"][feature_name]},
            "segments": {
                segment_context["key"]: segment_context
                for segment_context in overrides_index.get(feature_name, ())
            },
        }
        result = engine.get_evaluation_result(trimmed)
        return Flag.from_evaluation_result(result["flags"][feature_name])


@dataclass
class Segment:
    id: int
    name: str
