import json
import typing
import uuid
from datetime import datetime, timezone

import sseclient
from flag_engine.context.types import (
    FeatureContext,
    FeatureValue,
    InOperatorSegmentCondition,
    SegmentContext,
    SegmentRule,
    StrValueSegmentCondition,
)
from flag_engine.result.types import SegmentResult

from flagsmith.api.types import (
    EnvironmentModel,
    FeatureStateModel,
    SegmentRuleModel,
)
from flagsmith.models import Segment
from flagsmith.types import (
    FeatureMetadata,
    SDKEvaluationContext,
    SegmentMetadata,
    StreamEvent,
    TraitMapping,
)
from flagsmith.utils.datetime import fromisoformat

# Each identity is evaluated with its own identity overrides segment only.
IDENTITY_OVERRIDES_SEGMENT_KEY = "identity_overrides"


def map_segment_results_to_identity_segments(
    segment_results: list[SegmentResult[SegmentMetadata]],
) -> list[Segment]:
    identity_segments: list[Segment] = []
    for segment_result in segment_results:
        if metadata := segment_result.get("metadata"):
            if metadata.get("source") == "api" and (
                (segment_id := metadata.get("id")) is not None
            ):
                identity_segments.append(
                    Segment(
                        id=segment_id,
                        name=segment_result["name"],
                    )
                )
    return identity_segments


def map_sse_event_to_stream_event(event: sseclient.Event) -> StreamEvent:
    event_data = json.loads(event.data)
    return {
        "updated_at": datetime.fromtimestamp(
            event_data["updated_at"],
            tz=timezone.utc,
        )
    }


def map_environment_document_to_environment_updated_at(
    environment_document: dict[str, typing.Any],
) -> datetime:
    if (updated_at := fromisoformat(environment_document["updated_at"])).tzinfo is None:
        return updated_at.replace(tzinfo=timezone.utc)
    return updated_at.astimezone(tz=timezone.utc)


def resolve_trait_values(
    traits: typing.Optional[TraitMapping],
) -> typing.Optional[typing.Dict[str, typing.Any]]:
    if not traits:
        return None
    return {
        key: (val["value"] if isinstance(val, dict) else val)
        for key, val in traits.items()
    }


def map_context_and_identity_data_to_context(
    context: SDKEvaluationContext,
    identifier: str,
    traits: typing.Optional[TraitMapping] = None,
) -> SDKEvaluationContext:
    return {
        **context,
        "identity": {
            "identifier": identifier,
            "traits": resolve_trait_values(traits) or {},
        },
    }


def map_environment_document_to_context(
    environment_document: EnvironmentModel,
) -> SDKEvaluationContext:
    return {
        "environment": {
            "key": environment_document["api_key"],
            "name": environment_document["name"],
        },
        "features": {
            feature["name"]: feature
            for feature in _map_environment_document_feature_states_to_feature_contexts(
                environment_document["feature_states"]
            )
        },
        "segments": {
            (segment_key := str(segment_id := segment["id"])): {
                "key": segment_key,
                "name": segment["name"],
                "rules": _map_environment_document_rules_to_context_rules(
                    segment["rules"]
                ),
                "overrides": list(
                    _map_environment_document_feature_states_to_feature_contexts(
                        segment.get("feature_states") or []
                    )
                ),
                "metadata": SegmentMetadata(
                    id=segment_id,
                    source="api",
                ),
            }
            for segment in environment_document["project"]["segments"]
        },
    }


def map_environment_document_to_identity_overrides_segments(
    environment_document: EnvironmentModel,
) -> typing.Dict[str, SegmentContext[SegmentMetadata, FeatureMetadata]]:
    """Map identity overrides to segment contexts by identifier, each matching
    its identity alone and carrying its overrides."""
    return {
        identity_override["identifier"]: {
            "key": IDENTITY_OVERRIDES_SEGMENT_KEY,
            "name": "identity_overrides",
            "rules": [
                map_identifiers_to_identity_overrides_rule(
                    [identity_override["identifier"]]
                )
            ],
            "overrides": [
                {
                    "key": "",  # Identity overrides never carry multivariate options
                    "name": feature_state["feature"]["name"],
                    "enabled": feature_state["enabled"],
                    "value": feature_state["feature_state_value"],
                    "priority": float("-inf"),  # Highest possible priority
                    "metadata": {"id": feature_state["feature"]["id"]},
                }
                for feature_state in identity_features
            ],
            "metadata": SegmentMetadata(source="identity_overrides"),
        }
        for identity_override in environment_document.get("identity_overrides") or []
        if (identity_features := identity_override["identity_features"])
    }


def map_identifiers_to_identity_overrides_rule(
    identifiers: typing.List[str],
) -> SegmentRule:
    condition: InOperatorSegmentCondition = {
        "property": "$.identity.identifier",
        "operator": "IN",
        "value": identifiers,
    }
    return {"type": "ALL", "conditions": [condition]}


def _map_environment_document_rules_to_context_rules(
    rules: list[SegmentRuleModel],
) -> list[SegmentRule]:
    return [
        dict(
            type=rule["type"],
            conditions=[
                StrValueSegmentCondition(
                    property=condition.get("property_") or "",
                    operator=condition["operator"],
                    value=condition["value"],
                )
                for condition in rule.get("conditions", [])
            ],
            rules=_map_environment_document_rules_to_context_rules(
                rule.get("rules", [])
            ),
        )
        for rule in rules
    ]


def _map_environment_document_feature_states_to_feature_contexts(
    feature_states: list[FeatureStateModel],
) -> typing.Iterable[FeatureContext[FeatureMetadata]]:
    for feature_state in feature_states:
        metadata: FeatureMetadata = {"id": feature_state["feature"]["id"]}
        feature_context = FeatureContext[FeatureMetadata](
            key=str(
                feature_state.get("django_id") or feature_state["featurestate_uuid"]
            ),
            name=feature_state["feature"]["name"],
            enabled=feature_state["enabled"],
            value=feature_state["feature_state_value"],
            metadata=metadata,
        )
        if multivariate_feature_state_values := feature_state.get(
            "multivariate_feature_state_values"
        ):
            variants: list[FeatureValue] = []
            for multivariate_feature_state_value in multivariate_feature_state_values:
                multivariate_feature_option = multivariate_feature_state_value[
                    "multivariate_feature_option"
                ]
                variant: FeatureValue = {
                    "value": multivariate_feature_option["value"],
                    "weight": multivariate_feature_state_value["percentage_allocation"],
                    "priority": (
                        multivariate_feature_state_value.get("id")
                        or uuid.UUID(
                            multivariate_feature_state_value["mv_fs_value_uuid"]
                        ).int
                    ),
                }
                if (key := multivariate_feature_option.get("key")) is not None:
                    variant["key"] = key
                variants.append(variant)
            feature_context["variants"] = variants

        if feature_segment := feature_state.get("feature_segment"):
            feature_context["priority"] = feature_segment["priority"]

        yield feature_context
