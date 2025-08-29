import json
import typing
from collections import defaultdict
from datetime import datetime, timezone
from operator import itemgetter

import sseclient
from flag_engine.context.types import (
    EvaluationContext,
    FeatureContext,
    SegmentContext,
    SegmentRule,
)
from flag_engine.segments.types import ContextValue

from flagsmith.types import StreamEvent, TraitConfig

OverrideKey = typing.Tuple[
    str,
    str,
    bool,
    typing.Any,
]
OverridesKey = typing.Tuple[OverrideKey, ...]


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
    if (
        updated_at := datetime.fromisoformat(environment_document["updated_at"])
    ).tzinfo is None:
        return updated_at.replace(tzinfo=timezone.utc)
    return updated_at.astimezone(tz=timezone.utc)


def map_context_and_identity_data_to_context(
    context: EvaluationContext,
    identifier: str,
    traits: typing.Optional[
        typing.Mapping[
            str,
            typing.Union[
                ContextValue,
                TraitConfig,
            ],
        ]
    ],
) -> EvaluationContext:
    return {
        **context,
        "identity": {
            "identifier": identifier,
            "key": f"{context['environment']['key']}_{identifier}",
            "traits": {
                trait_key: (
                    trait_value_or_config["value"]
                    if isinstance(trait_value_or_config, dict)
                    else trait_value_or_config
                )
                for trait_key, trait_value_or_config in (traits or {}).items()
            },
        },
    }


def map_environment_document_to_context(
    environment_document: dict[str, typing.Any],
) -> EvaluationContext:
    return {
        "environment": {
            "key": environment_document["api_key"],
            "name": "Test Environment",
        },
        "features": {
            feature["name"]: feature
            for feature in _map_environment_document_feature_states_to_feature_contexts(
                environment_document["feature_states"]
            )
        },
        "segments": {
            **{
                (segment_key := str(segment["id"])): {
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
                }
                for segment in environment_document["project"]["segments"]
            },
            **_map_identity_overrides_to_segments(
                environment_document.get("identity_overrides") or []
            ),
        },
    }


def _map_identity_overrides_to_segments(
    identity_overrides: list[dict[str, typing.Any]],
) -> dict[str, SegmentContext]:
    features_to_identifiers: typing.Dict[
        OverridesKey,
        typing.List[str],
    ] = defaultdict(list)
    for identity_override in identity_overrides:
        identity_features: list[dict[str, typing.Any]] = identity_override[
            "identity_features"
        ]
        if not identity_features:
            continue
        overrides_key = tuple(
            (
                str(feature_state["feature"]["id"]),
                feature_state["feature"]["name"],
                feature_state["enabled"],
                feature_state["feature_state_value"],
            )
            for feature_state in sorted(
                identity_features,
                key=lambda feature_state: feature_state["feature"]["name"],
            )
        )
        features_to_identifiers[overrides_key].append(identity_override["identifier"])
    segment_contexts: typing.Dict[str, SegmentContext] = {}
    for overrides_key, identifiers in features_to_identifiers.items():
        # Create a segment context for each unique set of overrides
        # Generate a unique key to avoid collisions
        segment_key = str(hash(overrides_key))
        segment_contexts[segment_key] = SegmentContext(
            key="",  # Identity override segments never use % Split operator
            name="identity_overrides",
            rules=[
                {
                    "type": "ALL",
                    "conditions": [
                        {
                            "property": "$.identity.identifier",
                            "operator": "IN",
                            "value": identifiers,
                        }
                    ],
                }
            ],
            overrides=[
                {
                    "key": "",  # Identity overrides never carry multivariate options
                    "feature_key": feature_key,
                    "name": feature_name,
                    "enabled": feature_enabled,
                    "value": feature_value,
                    "priority": float("-inf"),  # Highest possible priority
                }
                for feature_key, feature_name, feature_enabled, feature_value in overrides_key
            ],
        )
    return segment_contexts


def _map_environment_document_rules_to_context_rules(
    rules: list[dict[str, typing.Any]],
) -> list[SegmentRule]:
    return [
        dict(
            type=rule["type"],
            conditions=[
                dict(
                    property=condition.get("property_"),
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
    feature_states: list[dict[str, typing.Any]],
) -> typing.Iterable[FeatureContext]:
    for feature_state in feature_states:
        feature_context = FeatureContext(
            key=str(feature_state["id"]),
            feature_key=str(feature_state["feature"]["id"]),
            name=feature_state["feature"]["name"],
            enabled=feature_state["enabled"],
            value=feature_state["feature_state_value"],
        )
        if multivariate_feature_state_values := feature_state.get(
            "multivariate_feature_state_values"
        ):
            feature_context["variants"] = [
                {
                    "value": multivariate_feature_state_value[
                        "multivariate_feature_option"
                    ]["value"],
                    "weight": multivariate_feature_state_value["percentage_allocation"],
                }
                for multivariate_feature_state_value in sorted(
                    multivariate_feature_state_values,
                    key=itemgetter("id"),
                )
            ]
        if (
            priority := (feature_state.get("feature_segment") or {}).get("priority")
            is not None
        ):
            feature_context["priority"] = priority

        yield feature_context
