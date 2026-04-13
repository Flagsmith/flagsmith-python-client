import typing
from unittest import mock

import pytest

from flagsmith.analytics import PipelineAnalyticsProcessor
from flagsmith.models import Flag, Flags
from flagsmith.types import SDKEvaluationResult, SDKFlagResult


def test_flag_from_evaluation_result() -> None:
    # Given
    flag_result: SDKFlagResult = {
        "enabled": True,
        "name": "test_feature",
        "reason": "DEFAULT",
        "value": "test-value",
        "metadata": {"id": 123},
    }

    # When
    flag = Flag.from_evaluation_result(flag_result)

    # Then
    assert flag.enabled is True
    assert flag.value == "test-value"
    assert flag.feature_name == "test_feature"
    assert flag.feature_id == 123
    assert flag.is_default is False


@pytest.mark.parametrize(
    "flags_result,expected_names",
    [
        ({}, []),
        (
            {
                "feature1": {
                    "enabled": True,
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                    "metadata": {"id": 1},
                }
            },
            ["feature1"],
        ),
        (
            {
                "feature1": {
                    "enabled": True,
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                    "metadata": {"id": 1},
                }
            },
            ["feature1"],
        ),
        (
            {
                "feature1": {
                    "enabled": True,
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                    "metadata": {"id": 1},
                },
                "feature2": {
                    "enabled": True,
                    "name": "feature2",
                    "reason": "DEFAULT",
                    "value": "value2",
                    "metadata": {"id": 2},
                },
                "feature3": {
                    "enabled": True,
                    "name": "feature3",
                    "reason": "DEFAULT",
                    "value": 42,
                    "metadata": {"id": 3},
                },
            },
            ["feature1", "feature2", "feature3"],
        ),
    ],
)
def test_flags_from_evaluation_result(
    flags_result: typing.Dict[str, SDKFlagResult],
    expected_names: typing.List[str],
) -> None:
    # Given
    evaluation_result: SDKEvaluationResult = {
        "flags": flags_result,
        "segments": [],
    }

    # When
    flags: Flags = Flags.from_evaluation_result(
        evaluation_result=evaluation_result,
        analytics_processor=None,
        default_flag_handler=None,
    )

    # Then
    assert set(flags.flags.keys()) == set(expected_names)
    assert set(flag.feature_name for flag in flags.flags.values()) == set(
        expected_names
    )


@pytest.mark.parametrize(
    "value,expected",
    [
        ("string", "string"),
        (42, 42),
        (3.14, 3.14),
        (True, True),
        (False, False),
        (None, None),
    ],
)
def test_flag_from_evaluation_result_value_types(
    value: typing.Any, expected: typing.Any
) -> None:
    # Given
    flag_result: SDKFlagResult = {
        "enabled": True,
        "name": "test_feature",
        "reason": "DEFAULT",
        "value": value,
        "metadata": {"id": 123},
    }

    # When
    flag = Flag.from_evaluation_result(flag_result)

    # Then
    assert flag.value == expected


def test_flag_from_evaluation_result_missing_metadata__raises_expected() -> None:
    # Given
    flag_result: SDKFlagResult = {
        "enabled": True,
        "name": "test_feature",
        "reason": "DEFAULT",
        "value": "test-value",
    }

    # When & Then
    with pytest.raises(ValueError):
        Flag.from_evaluation_result(flag_result)


def test_get_flag_records_pipeline_evaluation_event(
    pipeline_analytics_processor: PipelineAnalyticsProcessor,
) -> None:
    flags = Flags(
        flags={
            "my_feature": Flag(
                enabled=True, value="v1", feature_name="my_feature", feature_id=1
            )
        },
        _pipeline_analytics_processor=pipeline_analytics_processor,
        _identity_identifier="user123",
        _traits={"plan": "premium"},
    )

    with mock.patch.object(
        pipeline_analytics_processor, "record_evaluation_event"
    ) as mock_record:
        flags.get_flag("my_feature")

    mock_record.assert_called_once_with(
        flag_key="my_feature",
        enabled=True,
        value="v1",
        identity_identifier="user123",
        traits={"plan": "premium"},
    )


def test_get_flag_without_pipeline_processor() -> None:
    flags = Flags(
        flags={
            "my_feature": Flag(
                enabled=True, value="v1", feature_name="my_feature", feature_id=1
            )
        },
    )
    flag = flags.get_flag("my_feature")
    assert flag.enabled is True
