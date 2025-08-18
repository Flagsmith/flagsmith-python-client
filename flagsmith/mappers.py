import json
import typing
from collections import defaultdict

from flag_engine.context.types import (
    EvaluationContext,
    FeatureContext,
    SegmentContext,
    SegmentRule,
)
from flag_engine.environments.models import EnvironmentModel
from flag_engine.features.models import (
    FeatureModel,
    FeatureStateModel,
    MultivariateFeatureStateValueModel,
)
from flag_engine.identities.models import IdentityModel
from flag_engine.identities.traits.models import TraitModel
from flag_engine.result.types import FlagResult
from flag_engine.segments.models import SegmentRuleModel

OverrideKey = typing.Tuple[
    str,
    str,
    bool,
    typing.Any,
]
OverridesKey = typing.Tuple[OverrideKey, ...]


def map_environment_identity_to_context(
    environment: EnvironmentModel,
    identity: typing.Optional[IdentityModel],
    override_traits: typing.Optional[typing.List[TraitModel]],
) -> EvaluationContext:
    """
    Map an EnvironmentModel and IdentityModel to an EvaluationContext.

    :param environment: The environment model object.
    :param identity: The identity model object.
    :param override_traits: A list of TraitModel objects, to be used in place of `identity.identity_traits` if provided.
    :return: An EvaluationContext containing the environment and identity.
    """
    features = _map_feature_states_to_feature_contexts(environment.feature_states)
    segments: typing.Dict[str, SegmentContext] = {}
    for segment in environment.project.segments:
        segment_ctx_data: SegmentContext = {
            "key": str(segment.id),
            "name": segment.name,
            "rules": _map_segment_rules_to_segment_context_rules(segment.rules),
        }
        if segment_feature_states := segment.feature_states:
            segment_ctx_data["overrides"] = list(
                _map_feature_states_to_feature_contexts(segment_feature_states).values()
            )
        segments[str(segment.id)] = segment_ctx_data
    identity_overrides = environment.identity_overrides + [identity] if identity else []
    segments.update(_map_identity_overrides_to_segment_contexts(identity_overrides))
    return {
        "environment": {
            "key": environment.api_key,
            "name": environment.name or "",
        },
        "identity": (
            {
                "identifier": identity.identifier,
                "key": str(identity.django_id or identity.composite_key),
                "traits": {
                    trait.trait_key: trait.trait_value
                    for trait in (
                        override_traits
                        if override_traits is not None
                        else identity.identity_traits
                    )
                },
            }
            if identity
            else None
        ),
        "features": features,
        "segments": segments,
    }


def _map_identity_overrides_to_segment_contexts(
    identity_overrides: typing.List[IdentityModel],
) -> typing.Dict[str, SegmentContext]:
    """
    Map identity overrides to segment contexts.

    :param identity_overrides: A list of IdentityModel objects.
    :return: A dictionary mapping segment ids to SegmentContext objects.
    """
    features_to_identifiers: typing.Dict[
        OverridesKey,
        typing.List[str],
    ] = defaultdict(list)
    for identity_override in identity_overrides:
        identity_features: typing.List[FeatureStateModel] = (
            identity_override.identity_features
        )
        if not identity_features:
            continue
        overrides_key = tuple(
            (
                str(feature_state.feature.id),
                feature_state.feature.name,
                feature_state.enabled,
                feature_state.feature_state_value,
            )
            for feature_state in sorted(identity_features, key=_get_name)
        )
        features_to_identifiers[overrides_key].append(identity_override.identifier)
    segment_contexts: typing.Dict[str, SegmentContext] = {}
    for overrides_key, identifiers in features_to_identifiers.items():
        segment_contexts[str(hash(overrides_key))] = SegmentContext(
            key="",  # Identity override segments never use % Split operator
            name="identity_overrides",
            rules=[
                {
                    "type": "ALL",
                    "conditions": [
                        {
                            "property": "$.identity.identifier",
                            "operator": "IN",
                            "value": json.dumps(identifiers),
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


def _map_feature_states_to_feature_contexts(
    feature_states: typing.List[FeatureStateModel],
) -> typing.Dict[str, FeatureContext]:
    """
    Map feature states to feature contexts.

    :param feature_states: A list of FeatureStateModel objects.
    :return: A dictionary mapping feature names to their contexts.
    """
    features: typing.Dict[str, FeatureContext] = {}
    for feature_state in feature_states:
        feature_context: FeatureContext = {
            "key": str(feature_state.django_id or feature_state.featurestate_uuid),
            "feature_key": str(feature_state.feature.id),
            "name": feature_state.feature.name,
            "enabled": feature_state.enabled,
            "value": feature_state.feature_state_value,
        }
        multivariate_feature_state_values: typing.List[
            MultivariateFeatureStateValueModel
        ]
        if (
            multivariate_feature_state_values := feature_state.multivariate_feature_state_values
        ):
            feature_context["variants"] = [
                {
                    "value": multivariate_feature_state_value.multivariate_feature_option.value,
                    "weight": multivariate_feature_state_value.percentage_allocation,
                }
                for multivariate_feature_state_value in sorted(
                    multivariate_feature_state_values,
                    key=_get_multivariate_feature_state_value_id,
                )
            ]
        if feature_segment := feature_state.feature_segment:
            if (priority := feature_segment.priority) is not None:
                feature_context["priority"] = priority
        features[feature_state.feature.name] = feature_context
    return features


def _map_segment_rules_to_segment_context_rules(
    rules: typing.List[SegmentRuleModel],
) -> typing.List[SegmentRule]:
    """
    Map segment rules to segment rules for the evaluation context.

    :param rules: A list of SegmentRuleModel objects.
    :return: A list of SegmentRule objects.
    """
    return [
        {
            "type": rule.type,
            "conditions": [
                {
                    "property": condition.property_ or "",
                    "operator": condition.operator,
                    "value": condition.value or "",
                }
                for condition in rule.conditions
            ],
            "rules": _map_segment_rules_to_segment_context_rules(rule.rules),
        }
        for rule in rules
    ]


def map_flag_results_to_feature_states(
    flag_results: typing.List[FlagResult],
) -> typing.List[FeatureStateModel]:
    """
    Map flag results to feature states.

    :param flag_results: A list of FlagResult objects.
    :return: A list of FeatureStateModel objects.
    """
    return [
        FeatureStateModel(
            feature=FeatureModel(
                id=flag_result["feature_key"],
                name=flag_result["name"],
                type=(
                    "MULTIVARIATE"
                    if flag_result["reason"].startswith("SPLIT")
                    else "STANDARD"
                ),
            ),
            enabled=flag_result["enabled"],
            feature_state_value=flag_result["value"],
        )
        for flag_result in flag_results
    ]


def _get_multivariate_feature_state_value_id(
    multivariate_feature_state_value: MultivariateFeatureStateValueModel,
) -> int:
    return (
        multivariate_feature_state_value.id
        or multivariate_feature_state_value.mv_fs_value_uuid.int
    )


def _get_name(feature_state: FeatureStateModel) -> str:
    return feature_state.feature.name
