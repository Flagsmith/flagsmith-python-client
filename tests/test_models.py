import typing

import pytest
from flagsmith.models import Flag, Flags
from flag_engine.segments.evaluator import EvaluationResult, FlagResult


def test_flag_from_evaluation_result() -> None:
    # Given
    flag_result: FlagResult = {
        "name": "test_feature",
        "enabled": True,
        "value": "test-value",
        "feature_key": "123",
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
        ([], 0, []),
        (
            [
                {
                    "name": "feature1",
                    "enabled": True,
                    "value": "value1",
                    "feature_key": "1",
                }
            ],
            1,
            ["feature1"],
        ),
        (
            [
                {
                    "name": "feature1",
                    "enabled": True,
                    "value": "value1",
                    "feature_key": "1",
                },
                {
                    "name": "feature2",
                    "enabled": False,
                    "value": None,
                    "feature_key": "2",
                },
                {"name": "feature3", "enabled": True, "value": 42, "feature_key": "3"},
            ],
            3,
            ["feature1", "feature2", "feature3"],
        ),
    ],
)
def test_flags_from_evaluation_result(
    flags_result: typing.List[FlagResult],
    expected_count: int,
    expected_names: typing.List[str],
) -> None:
    # Given
    evaluation_result: EvaluationResult = {
        "flags": flags_result,
        "segments": [],
        "context": {
            "environment": {
                "name": "test_environment",
                "key": "test_environment_key",
            }
        },
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
        "name": "test_feature",
        "enabled": True,
        "value": value,
        "feature_key": "123",
    }

    # When
    flag: Flag = Flag.from_evaluation_result(flag_result)

    # Then
    assert flag.value == expected
