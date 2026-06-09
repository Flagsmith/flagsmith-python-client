from flagsmith.api.types import EnvironmentModel
from flagsmith.mappers import map_environment_document_to_context


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
