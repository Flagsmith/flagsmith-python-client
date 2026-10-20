from __future__ import annotations

import typing
from collections import ChainMap
from functools import cached_property

from flag_engine import engine
from flag_engine.context.types import SegmentContext

from flagsmith.mappers import (
    get_identity_overrides_identifiers,
    map_context_and_identity_data_to_context,
    map_identifiers_to_identity_overrides_rules,
)
from flagsmith.models import (
    Flag,
    SegmentContexts,
    SegmentOverridesIndex,
    build_segment_overrides_index,
)
from flagsmith.types import (
    FeatureMetadata,
    SDKEvaluationContext,
    SegmentMetadata,
    TraitMapping,
)


class LocalEvaluation:
    """Per-environment-document state for local evaluation.

    Built once each time the environment document is refreshed, so the
    work here is amortised across every evaluation until the next refresh.

    Identity overrides are mapped to segments matching the identifiers
    they apply to. Left in the context, every one of them would be
    matched on every identity evaluation. Instead, they're indexed by
    identifier, and each identity is evaluated with only its own.
    """

    def __init__(self, context: SDKEvaluationContext) -> None:
        self.context = context

        segments: SegmentContexts = {}
        self._identity_overrides_segment_keys: typing.Dict[str, typing.List[str]] = {}
        for segment_key, segment_context in (context.get("segments") or {}).items():
            identifiers = get_identity_overrides_identifiers(segment_context)
            if identifiers is None:
                segments[segment_key] = segment_context
                continue
            for identifier in identifiers:
                self._identity_overrides_segment_keys.setdefault(identifier, []).append(
                    segment_key
                )

        # The context without identity overrides segments.
        self.base_context: SDKEvaluationContext = {**context, "segments": segments}
        self.overrides_index: SegmentOverridesIndex = build_segment_overrides_index(
            self.base_context
        )

    @cached_property
    def environment_flags(self) -> typing.Dict[str, Flag]:
        """Environment flags, which depend on the environment document only."""
        # Omit segments from evaluation context for environment flags
        # as they are only relevant for identity-specific evaluations
        context_without_segments = self.context.copy()
        context_without_segments.pop("segments", None)
        evaluation_result = engine.get_evaluation_result(
            context=context_without_segments,
        )
        return {
            feature_name: Flag.from_evaluation_result(flag_result)
            for feature_name, flag_result in evaluation_result["flags"].items()
        }

    def get_identity_context(
        self,
        identifier: str,
        traits: typing.Optional[TraitMapping] = None,
    ) -> typing.Tuple[SDKEvaluationContext, SegmentOverridesIndex]:
        """Evaluation context and overrides index for an identity.

        The context carries the identity's own identity overrides segments,
        narrowed to its identifier, so that their size doesn't depend on how
        many identities share the same overrides.
        """
        context = map_context_and_identity_data_to_context(
            context=self.base_context,
            identifier=identifier,
            traits=traits,
        )
        if not (segment_keys := self._identity_overrides_segment_keys.get(identifier)):
            return context, self.overrides_index

        identity_segments: SegmentContexts = {}
        identity_overrides_index: SegmentOverridesIndex = {}
        segment_contexts = self.context.get("segments") or {}
        for segment_key in segment_keys:
            segment_context: SegmentContext[SegmentMetadata, FeatureMetadata] = {
                **segment_contexts[segment_key],
                "rules": map_identifiers_to_identity_overrides_rules([identifier]),
            }
            identity_segments[segment_key] = segment_context
            for override in segment_context.get("overrides") or ():
                feature_name = override["name"]
                if feature_name not in identity_overrides_index:
                    identity_overrides_index[feature_name] = dict(
                        self.overrides_index.get(feature_name) or {}
                    )
                identity_overrides_index[feature_name][segment_key] = segment_context

        context["segments"] = {**(context.get("segments") or {}), **identity_segments}
        return context, ChainMap(identity_overrides_index, self.overrides_index)
