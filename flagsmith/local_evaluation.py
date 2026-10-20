from __future__ import annotations

import typing
from collections import ChainMap
from functools import cached_property

from flag_engine import engine
from flag_engine.context.types import SegmentContext

from flagsmith.api.types import EnvironmentModel
from flagsmith.mappers import (
    map_context_and_identity_data_to_context,
    map_environment_document_to_context,
    map_environment_document_to_identity_overrides_segments,
)
from flagsmith.models import (
    Flag,
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
    """Per-environment-document state for local evaluation."""

    def __init__(
        self,
        context: SDKEvaluationContext,
        identity_overrides_segments: typing.Optional[
            typing.Mapping[str, SegmentContext[SegmentMetadata, FeatureMetadata]]
        ] = None,
    ) -> None:
        self.context = context
        self.overrides_index: SegmentOverridesIndex = build_segment_overrides_index(
            context
        )
        self._identity_overrides = {
            identifier: (segment_context, self._index_overrides(segment_context))
            for identifier, segment_context in (
                identity_overrides_segments or {}
            ).items()
        }

    @classmethod
    def from_environment_document(
        cls,
        environment_document: EnvironmentModel,
    ) -> LocalEvaluation:
        return cls(
            context=map_environment_document_to_context(environment_document),
            identity_overrides_segments=(
                map_environment_document_to_identity_overrides_segments(
                    environment_document
                )
            ),
        )

    @cached_property
    def environment_flags(self) -> typing.Dict[str, Flag]:
        """Environment flags, which depend on the environment document only."""
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
        """Evaluation context and overrides index for an identity, including
        its own identity overrides segment, if any."""
        context = map_context_and_identity_data_to_context(
            context=self.context,
            identifier=identifier,
            traits=traits,
        )
        if (identity_overrides := self._identity_overrides.get(identifier)) is None:
            return context, self.overrides_index

        segment_context, identity_overrides_index = identity_overrides
        context["segments"] = {
            **(context.get("segments") or {}),
            segment_context["key"]: segment_context,
        }
        return context, ChainMap(identity_overrides_index, self.overrides_index)

    def _index_overrides(
        self,
        segment_context: SegmentContext[SegmentMetadata, FeatureMetadata],
    ) -> SegmentOverridesIndex:
        """The overrides index, for the features `segment_context` overrides."""
        return {
            feature_name: {
                **(self.overrides_index.get(feature_name) or {}),
                segment_context["key"]: segment_context,
            }
            for override in segment_context.get("overrides") or ()
            if (feature_name := override["name"])
        }
