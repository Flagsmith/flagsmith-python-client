import copy

import pytest
from flag_engine import engine
from pytest_mock import MockerFixture

from flagsmith.api.types import EnvironmentModel
from flagsmith.local_evaluation import LocalEvaluation


@pytest.fixture()
def local_evaluation(environment: EnvironmentModel) -> LocalEvaluation:
    return LocalEvaluation.from_environment_document(environment)


def test_local_evaluation__context__excludes_identity_overrides_segments(
    local_evaluation: LocalEvaluation,
) -> None:
    # When
    segments = local_evaluation.context["segments"]

    # Then
    assert segments is not None
    assert [segment["name"] for segment in segments.values()] == ["Test segment"]
    assert local_evaluation.overrides_index == {}


def test_local_evaluation__get_identity_context_no_identity_overrides__returns_context(
    local_evaluation: LocalEvaluation,
) -> None:
    # When
    context, overrides_index = local_evaluation.get_identity_context(
        "not-overridden-id", {"foo": "bar"}
    )

    # Then
    assert context["segments"] is local_evaluation.context["segments"]
    assert overrides_index is local_evaluation.overrides_index
    assert context["identity"] == {
        "identifier": "not-overridden-id",
        "traits": {"foo": "bar"},
    }


@pytest.mark.parametrize(
    "identifier, expected_value",
    [
        ("overridden-id", "some-overridden-value"),
        ("another-overridden-id", "another-overridden-value"),
    ],
)
def test_local_evaluation__get_identity_context_identity_overrides__returns_own_narrowed(
    local_evaluation: LocalEvaluation,
    identifier: str,
    expected_value: str,
) -> None:
    # When
    context, overrides_index = local_evaluation.get_identity_context(identifier)

    # Then
    # only the identity's own identity overrides segment is added,
    # matching its identifier alone
    assert context["segments"] is not None
    identity_segments = [
        segment
        for segment in context["segments"].values()
        if segment["name"] == "identity_overrides"
    ]
    assert identity_segments == [
        {
            "key": "identity_overrides",
            "name": "identity_overrides",
            "rules": [
                {
                    "type": "ALL",
                    "conditions": [
                        {
                            "property": "$.identity.identifier",
                            "operator": "IN",
                            "value": [identifier],
                        }
                    ],
                }
            ],
            "overrides": [
                {
                    "key": "",
                    "name": "some_feature",
                    "enabled": False,
                    "value": expected_value,
                    "priority": float("-inf"),
                    "metadata": {"id": 1},
                }
            ],
            "metadata": {"source": "identity_overrides"},
        }
    ]
    [segment] = identity_segments
    assert list(overrides_index) == ["some_feature"]
    assert list(overrides_index["some_feature"].values()) == [segment]

    # And the shared state is left untouched
    assert local_evaluation.overrides_index == {}
    assert local_evaluation.context["segments"] is not None
    assert len(local_evaluation.context["segments"]) == 1


@pytest.mark.parametrize(
    "identifier, expected_value",
    [
        ("overridden-id", "some-overridden-value"),
        ("another-overridden-id", "another-overridden-value"),
        ("not-overridden-id", "some-value"),
    ],
)
def test_local_evaluation__get_identity_context__evaluates_to_identity_overrides(
    local_evaluation: LocalEvaluation,
    identifier: str,
    expected_value: str,
) -> None:
    # Given
    context, _ = local_evaluation.get_identity_context(identifier)

    # When
    result = engine.get_evaluation_result(context)

    # Then
    assert result["flags"]["some_feature"]["value"] == expected_value


def test_local_evaluation__environment_flags__evaluated_once(
    local_evaluation: LocalEvaluation,
    mocker: MockerFixture,
) -> None:
    # Given
    spy = mocker.spy(engine, "get_evaluation_result")

    # When
    first = local_evaluation.environment_flags
    second = local_evaluation.environment_flags

    # Then
    assert first is second
    assert first["some_feature"].value == "some-value"
    spy.assert_called_once()


@pytest.mark.parametrize(
    "condition_property, expected_reads_flags",
    [
        ("$.flags.some_feature.enabled", True),
        ("$.flags['some feature'].value", True),
        ("$.flagship", False),
        ("flags", False),
    ],
)
def test_local_evaluation__reads__flags__returns_expected(
    environment: EnvironmentModel,
    condition_property: str,
    expected_reads_flags: bool,
) -> None:
    # Given
    # a condition in a nested rule of the only segment
    environment = copy.deepcopy(environment)
    condition = environment["project"]["segments"][0]["rules"][0]["rules"][0][
        "conditions"
    ][0]
    condition["property_"] = condition_property

    # When
    local_evaluation = LocalEvaluation.from_environment_document(environment)

    # Then
    assert local_evaluation.reads.flags is expected_reads_flags
