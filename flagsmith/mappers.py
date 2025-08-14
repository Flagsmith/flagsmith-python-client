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
    FeatureStateModel,
    MultivariateFeatureStateValueModel,
)
from flag_engine.identities.models import IdentityModel
from flag_engine.identities.traits.models import TraitModel
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
    identity: IdentityModel,
    override_traits: typing.Optional[typing.List[TraitModel]],
) -> EvaluationContext:
    """
    Map an EnvironmentModel and IdentityModel to an EvaluationContext.

    :param environment: The environment model object.
    :param identity: The identity model object.
    :param override_traits: A list of TraitModel objects, to be used in place of `identity.identity_traits` if provided.
    :return: An EvaluationContext containing the environment and identity.
    """
    features = map_feature_states_to_feature_contexts(environment.feature_states)
    segments: typing.Dict[str, SegmentContext] = {}
    for segment in environment.project.segments:
        segment_ctx_data: SegmentContext = {
            "key": str(segment.id),
            "name": segment.name,
            "rules": map_segment_rules_to_segment_context_rules(segment.rules),
        }
        if segment_feature_states := segment.feature_states:
            segment_ctx_data["overrides"] = list(
                map_feature_states_to_feature_contexts(segment_feature_states).values()
            )
        segments[segment.name] = segment_ctx_data
    # Concatenate feature states overriden for identities
    # to segment contexts
    features_to_identifiers: typing.Dict[
        OverridesKey,
        typing.List[str],
    ] = defaultdict(list)
    for identity_override in (*environment.identity_overrides, identity):
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
    for overrides_key, identifiers in features_to_identifiers.items():
        segment_name = f"overrides_{abs(hash(overrides_key))}"
        segments[segment_name] = SegmentContext(
            key="",  # Identity override segments never use % Split operator
            name=segment_name,
            rules=[
                {
                    "type": "ALL",
                    "rules": [
                        {
                            "type": "ALL",
                            "conditions": [
                                {
                                    "property": "$.identity.identifier",
                                    "operator": "IN",
                                    "value": ",".join(identifiers),
                                }
                            ],
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
    return {
        "environment": {
            "key": environment.api_key,
            "name": environment.name or "",
        },
        "identity": {
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
        },
        "features": features,
        "segments": segments,
    }


def map_feature_states_to_feature_contexts(
    feature_states: typing.List[FeatureStateModel],
) -> typing.Dict[str, FeatureContext]:
    """
    Map feature states to feature contexts.

    :param feature_states: A list of FeatureStateModel objects.
    :return: A dictionary mapping feature names to their contexts.
    """
    features: typing.Dict[str, FeatureContext] = {}
    for feature_state in feature_states:
        feature_ctx_data: FeatureContext = {
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
            feature_ctx_data["variants"] = [
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
                feature_ctx_data["priority"] = priority
        features[feature_state.feature.name] = feature_ctx_data
    return features


def _get_multivariate_feature_state_value_id(
    multivariate_feature_state_value: MultivariateFeatureStateValueModel,
) -> int:
    return (
        multivariate_feature_state_value.id
        or multivariate_feature_state_value.mv_fs_value_uuid.int
    )


def map_segment_rules_to_segment_context_rules(
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
            "rules": map_segment_rules_to_segment_context_rules(rule.rules),
        }
        for rule in rules
    ]


def _get_name(feature_state: FeatureStateModel) -> str:
    return feature_state.feature.name
