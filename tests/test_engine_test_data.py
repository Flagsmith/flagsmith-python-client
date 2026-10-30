import json
import re
import typing
from pathlib import Path

import pytest

from flagsmith.models import (
    Flag,
    Flags,
    build_segment_overrides_index,
    find_flag_dependent_features,
)
from flagsmith.types import SDKEvaluationContext

TEST_CASES_PATH = Path(__file__).parent / "engine_tests/engine-test-data/test_cases"
JSONC_LINE_COMMENT_RE = re.compile(r"^\s*//.*$", re.MULTILINE)


def _load_test_case(path: Path) -> typing.Dict[str, typing.Any]:
    test_case: typing.Dict[str, typing.Any] = json.loads(
        JSONC_LINE_COMMENT_RE.sub("", path.read_text())
    )
    return test_case


def _with_feature_ids(context: typing.Dict[str, typing.Any]) -> SDKEvaluationContext:
    # Contexts built by the SDK always carry feature IDs in metadata, and
    # `Flag.from_evaluation_result` requires them. Engine test data may omit
    # them, so fill in a placeholder.
    for feature in (context.get("features") or {}).values():
        feature["metadata"] = {"id": 1, **(feature.get("metadata") or {})}
    for segment in (context.get("segments") or {}).values():
        for override in segment.get("overrides") or []:
            override["metadata"] = {"id": 1, **(override.get("metadata") or {})}
    return typing.cast(SDKEvaluationContext, context)


@pytest.mark.parametrize(
    "test_case_path",
    sorted(TEST_CASES_PATH.glob("*.json*")),
    ids=lambda path: path.stem,
)
def test_engine_test_data__lazy_flags__match_expected_result(
    test_case_path: Path,
) -> None:
    # Given
    test_case = _load_test_case(test_case_path)
    context = _with_feature_ids(test_case["context"])
    overrides_index = build_segment_overrides_index(context)
    flags = Flags.from_evaluation_context(
        context,
        overrides_index,
        flag_dependent_features=find_flag_dependent_features(overrides_index),
        analytics_processor=None,
        default_flag_handler=None,
    )

    # When
    actual_flags = {
        feature_name: flags.get_flag(feature_name)
        for feature_name in test_case["result"]["flags"]
    }

    # Then
    assert all(isinstance(flag, Flag) for flag in actual_flags.values())
    actual = {
        feature_name: (flag.enabled, flag.value, flag.reason)
        for feature_name, flag in actual_flags.items()
        if isinstance(flag, Flag)
    }
    assert actual == {
        feature_name: (expected["enabled"], expected["value"], expected["reason"])
        for feature_name, expected in test_case["result"]["flags"].items()
    }


def test_engine_test_data__submodule__is_checked_out() -> None:
    # Given / When
    test_case_paths = list(TEST_CASES_PATH.glob("*.json*"))

    # Then
    assert test_case_paths, "Run `git submodule update --init` to fetch test data"
