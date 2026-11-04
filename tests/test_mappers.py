import typing

from flagsmith.api.types import (
    EnvironmentModel,
    ExperimentModel,
    FeatureStateMetadataModel,
    FeatureStateModel,
)
from flagsmith.mappers import (
    map_environment_document_to_context,
    map_environment_document_to_identity_overrides_segments,
)


def _environment_with_keyed_variant() -> EnvironmentModel:
    return {
        "api_key": "test-key",
        "name": "Test",
        "project": {"segments": []},
        "identity_overrides": [],
        "feature_states": [
            {
                "enabled": True,
                "feature": {"id": 1, "name": "mv_feature"},
                "feature_state_value": "control_value",
                "featurestate_uuid": "00000000-0000-0000-0000-000000000001",
                "multivariate_feature_state_values": [
                    {
                        "id": 10,
                        "mv_fs_value_uuid": "00000000-0000-0000-0000-000000000002",
                        "percentage_allocation": 100,
                        "multivariate_feature_option": {
                            "value": "variant_value",
                            "key": "variant_a",
                        },
                    }
                ],
            }
        ],
    }


def test_map_environment_document_to_context__keyed_variant__carries_key() -> None:
    # Given
    environment = _environment_with_keyed_variant()

    # When
    context = map_environment_document_to_context(environment)

    # Then
    variants = context["features"]["mv_feature"]["variants"]
    assert variants[0]["key"] == "variant_a"


def test_map_environment_document_to_context__null_variant_key__drops_key() -> None:
    # Given - an unkeyed variant is serialised with a null key
    environment = _environment_with_keyed_variant()
    environment["feature_states"][0]["multivariate_feature_state_values"][0][
        "multivariate_feature_option"
    ]["key"] = None

    # When
    context = map_environment_document_to_context(environment)

    # Then - the null key is dropped, treated as no key
    variants = context["features"]["mv_feature"]["variants"]
    assert "key" not in variants[0]


EXPERIMENT: ExperimentModel = {
    "id": 42,
    "name": "New checkout CTA",
    "in_experiment": False,
}


def _feature_state(
    feature_name: str,
    metadata: typing.Optional[FeatureStateMetadataModel] = None,
) -> FeatureStateModel:
    feature_state: FeatureStateModel = {
        "enabled": True,
        "feature": {"id": 1, "name": feature_name},
        "feature_state_value": "control",
        "featurestate_uuid": "00000000-0000-0000-0000-000000000001",
        "multivariate_feature_state_values": [],
    }
    if metadata is not None:
        feature_state["metadata"] = metadata
    return feature_state


def _environment_with_experiment() -> EnvironmentModel:
    return {
        "api_key": "test-key",
        "name": "Test",
        "project": {
            "segments": [
                {
                    "id": 7,
                    "name": "rollout",
                    "rules": [],
                    "feature_states": [
                        _feature_state(
                            "banner",
                            {"experiment": {**EXPERIMENT, "in_experiment": True}},
                        )
                    ],
                }
            ]
        },
        "identity_overrides": [
            {
                "identifier": "user_123",
                "identity_features": [_feature_state("banner")],
            }
        ],
        "feature_states": [
            _feature_state("banner", {"experiment": EXPERIMENT}),
            _feature_state("plain", {}),
        ],
    }


def test_map_environment_document_to_context__experiment__carried_in_metadata() -> None:
    # Given
    environment = _environment_with_experiment()

    # When
    context = map_environment_document_to_context(environment)

    # Then
    assert context["features"]["banner"]["metadata"] == {
        "id": 1,
        "experiment": EXPERIMENT,
    }
    assert context["segments"]["7"]["overrides"][0]["metadata"] == {
        "id": 1,
        "experiment": {**EXPERIMENT, "in_experiment": True},
    }


def test_map_environment_document_to_context__no_experiment__metadata_has_id_only() -> (
    None
):
    # Given
    environment = _environment_with_experiment()

    # When
    context = map_environment_document_to_context(environment)

    # Then
    assert context["features"]["plain"]["metadata"] == {"id": 1}


def test_map_environment_document_to_identity_overrides_segments__no_experiment() -> (
    None
):
    # Given
    environment = _environment_with_experiment()

    # When
    segments = map_environment_document_to_identity_overrides_segments(environment)

    # Then
    assert segments["user_123"]["overrides"][0]["metadata"] == {"id": 1}
