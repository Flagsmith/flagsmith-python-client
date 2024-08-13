from dataclasses import fields
from typing import Dict, Tuple, cast
from unittest import mock

import pytest

from flagsmith import Flagsmith
from flagsmith.models import Flag, Flags


@pytest.fixture
def api_key(request: pytest.FixtureRequest) -> str:
    return cast(str, request.config.option.api_key)


@pytest.fixture
def api_url(request: pytest.FixtureRequest) -> str:
    return cast(str, request.config.option.api_url)


@pytest.fixture
def is_migrated(request: pytest.FixtureRequest) -> bool:
    return cast(bool, request.config.option.migrated)


@pytest.fixture
def identifiers() -> Tuple[str, ...]:
    return ("1", "2", "3", "4", "5")


def get_matching_str(*values: str) -> str:
    class _matching_str(str):
        _values = values

        def __eq__(self, other: object) -> bool:
            return other in self._values

    return _matching_str(" / ".join(values))


def _get_flag_mock(**kwargs: object) -> mock.Mock:
    mock_kwargs = {field.name: mock.ANY for field in fields(Flag)}
    mock_kwargs.update(kwargs)
    return mock.MagicMock(
        spec=Flag(mock.ANY, mock.ANY, mock.ANY, mock.ANY), **mock_kwargs
    )


@pytest.fixture
def environment_default_or_percentage_split_value_flag_mock() -> mock.Mock:
    return _get_flag_mock(
        value=get_matching_str(
            "environment default",
            'overridden by "split_segment"',
        ),
    )


@pytest.fixture
def mv_value_flag_mock() -> mock.Mock:
    return _get_flag_mock(
        value=get_matching_str(
            "a",
            "b",
        ),
    )


@pytest.fixture
def mv_segment_override_value_flag_mock() -> mock.Mock:
    return _get_flag_mock(
        value=get_matching_str(
            'overridden by segment "power_users"',
            "a",
        ),
    )


@pytest.fixture
def expected_flags_without_identity_overrides(
    environment_default_or_percentage_split_value_flag_mock: mock.Mock,
    mv_segment_override_value_flag_mock: mock.Mock,
    mv_value_flag_mock: mock.Mock,
) -> Dict[str, Flags]:
    return {
        # - [ ]  Identity 1:
        #   - [ ]  multivariate feature: % split
        #   - [ ]  normal feature: environment default / % split override
        "1": Flags(
            {
                "multivariate_feature": mv_value_flag_mock,
                "normal_feature": environment_default_or_percentage_split_value_flag_mock,
            },
        ),
        # - [ ]  Identity 2:
        #   - [ ]  multivariate feature: % split
        #   - [ ]  normal feature: environment default / % split override
        "2": Flags(
            {
                "multivariate_feature": mv_value_flag_mock,
                "normal_feature": environment_default_or_percentage_split_value_flag_mock,
            },
        ),
        # - [ ]  Identity 3:
        #   - [ ]  multivariate feature: segment override
        #   - [ ]  normal feature: environment default / % split override
        "3": Flags(
            {
                "multivariate_feature": mv_segment_override_value_flag_mock,
                "normal_feature": environment_default_or_percentage_split_value_flag_mock,
            },
        ),
        # - [ ]  Identity 4:
        #   - [ ]  multivariate feature: % split
        #   - [ ]  normal feature: environment default / % split override
        "4": Flags(
            {
                "multivariate_feature": mv_value_flag_mock,
                "normal_feature": environment_default_or_percentage_split_value_flag_mock,
            },
        ),
        # - [ ]  Identity 5:
        #   - [ ]  multivariate feature: % split
        #   - [ ]  normal feature: environment default / % split override
        "5": Flags(
            {
                "multivariate_feature": mv_value_flag_mock,
                "normal_feature": environment_default_or_percentage_split_value_flag_mock,
            },
        ),
    }


@pytest.fixture
def expected_flags_with_identity_overrides(
    environment_default_or_percentage_split_value_flag_mock: mock.Mock,
    mv_segment_override_value_flag_mock: mock.Mock,
    mv_value_flag_mock: mock.Mock,
) -> Dict[str, Flags]:
    return {
        # - [ ]  Identity 1:
        #   - [ ]  multivariate feature: identity override
        #   - [ ]  normal feature: identity override
        "1": Flags(
            {
                "multivariate_feature": _get_flag_mock(value="b"),
                "normal_feature": _get_flag_mock(value="overridden for 1"),
            },
        ),
        # - [ ]  Identity 2:
        #   - [ ]  multivariate feature: % split
        #   - [ ]  normal feature: identity override
        "2": Flags(
            {
                "multivariate_feature": mv_value_flag_mock,
                "normal_feature": _get_flag_mock(value="overridden for 2"),
            },
        ),
        # - [ ]  Identity 3:
        #   - [ ]  multivariate feature: segment override
        #   - [ ]  normal feature: identity override
        "3": Flags(
            {
                "multivariate_feature": mv_segment_override_value_flag_mock,
                "normal_feature": _get_flag_mock(value="overridden for 3"),
            },
        ),
        # - [ ]  Identity 4:
        #   - [ ]  multivariate feature: segment override
        #   - [ ]  normal feature: environment default / % split override
        "4": Flags(
            {
                "multivariate_feature": mv_segment_override_value_flag_mock,
                "normal_feature": environment_default_or_percentage_split_value_flag_mock,
            },
        ),
        # - [ ]  Identity 5:
        #   - [ ]  multivariate feature: % split
        #   - [ ]  normal feature: environment default / % split override
        "5": Flags(
            {
                "multivariate_feature": mv_value_flag_mock,
                "normal_feature": environment_default_or_percentage_split_value_flag_mock,
            },
        ),
    }


def get_local_and_remote_flags(
    api_key: str,
    api_url: str,
    identifiers: Tuple[str, ...],
) -> Tuple[Dict[str, Flags], Dict[str, Flags]]:
    local_eval_flagsmith = Flagsmith(
        environment_key=api_key,
        api_url=api_url,
        enable_local_evaluation=True,
    )
    remote_eval_flagsmith = Flagsmith(
        environment_key=api_key,
        api_url=api_url,
    )
    local_flags: Dict[str, Flags] = {}
    remote_flags: Dict[str, Flags] = {}

    for identifier in identifiers:
        local_flags[identifier] = local_eval_flagsmith.get_identity_flags(identifier)
        remote_flags[identifier] = remote_eval_flagsmith.get_identity_flags(identifier)

    return local_flags, remote_flags


def test_local_eval__before_migration__identity_flags_expected(
    is_migrated: bool,
    api_key: str,
    api_url: str,
    identifiers: Tuple[str, ...],
    expected_flags_without_identity_overrides: Dict[str, Flags],
    expected_flags_with_identity_overrides: Dict[str, Flags],
) -> None:
    if is_migrated:
        pytest.xfail("should fail for migrated environments")
    local_flags, remote_flags = get_local_and_remote_flags(
        api_key=api_key, api_url=api_url, identifiers=identifiers
    )
    assert local_flags == expected_flags_without_identity_overrides
    assert remote_flags == expected_flags_with_identity_overrides


def test_local_eval__after_migration__identity_flags_expected(
    is_migrated: bool,
    api_key: str,
    api_url: str,
    identifiers: Tuple[str, ...],
    expected_flags_with_identity_overrides: Dict[str, Flags],
) -> None:
    if not is_migrated:
        pytest.xfail("should fail for unmigrated environments")
    local_flags, remote_flags = get_local_and_remote_flags(
        api_key=api_key, api_url=api_url, identifiers=identifiers
    )
    assert local_flags == expected_flags_with_identity_overrides
    assert remote_flags == local_flags
