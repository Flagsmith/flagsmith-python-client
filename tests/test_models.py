import typing

import pytest
from flag_engine.result.types import FlagResult

from flagsmith.models import Flag, Flags
from flagsmith.types import SDKEvaluationResult


def test_flag_from_evaluation_result() -> None:
    # Given
    flag_result: FlagResult = {
        "enabled": True,
        "feature_key": "123",
        "name": "test_feature",
        "reason": "DEFAULT",
        "value": "test-value",
    }

    # When
    flag: Flag = Flag.from_evaluation_result(flag_result)

    # Then
    assert flag.enabled is True
    assert flag.value == "test-value"
    assert flag.feature_name == "test_feature"
    assert flag.feature_id == 123
    assert flag.is_default is False


@pytest.mark.parametrize(
    "flags_result,expected_count,expected_names",
    [
        ({}, 0, []),
        (
            {
                "feature1": {
                    "enabled": True,
                    "feature_key": "1",
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                }
            },
            1,
            ["feature1"],
        ),
        (
            {
                "feature1": {
                    "enabled": True,
                    "feature_key": "1",
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                }
            },
            1,
            ["feature1"],
        ),
        (
            {
                "feature1": {
                    "enabled": True,
                    "feature_key": "1",
                    "name": "feature1",
                    "reason": "DEFAULT",
                    "value": "value1",
                },
                "feature2": {
                    "enabled": True,
                    "feature_key": "2",
                    "name": "feature2",
                    "reason": "DEFAULT",
                    "value": "value2",
                },
                "feature3": {
                    "enabled": True,
                    "feature_key": "3",
                    "name": "feature3",
                    "reason": "DEFAULT",
                    "value": 42,
                },
            },
            3,
            ["feature1", "feature2", "feature3"],
        ),
    ],
)
def test_flags_from_evaluation_result(
    flags_result: typing.Dict[str, FlagResult],
    expected_count: int,
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
    assert len(flags.flags) == expected_count

    for name in expected_names:
        assert name in flags.flags
        flag: Flag = flags.flags[name]
        assert isinstance(flag, Flag)
        assert flag.feature_name == name


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
    flag_result: FlagResult = {
        "enabled": True,
        "feature_key": "123",
        "name": "test_feature",
        "reason": "DEFAULT",
        "value": value,
    }

    # When
    flag: Flag = Flag.from_evaluation_result(flag_result)

    # Then
    assert flag.value == expected
