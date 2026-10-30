"""
Benchmarks a locally evaluating SDK client against environment documents tiered by size.
"""

import os
import typing
from pathlib import Path

import pytest
import responses
from flag_engine.engine import ContextValue

from flagsmith import Flagsmith

API_URL = "http://flagsmith.benchmark/api/v1/"
ENVIRONMENTS_DIR = Path(os.environ["SDK_BENCHMARKS_ENVIRONMENTS_DIR"])
IDENTITY_OVERRIDES_IDENTIFIER = "identity-override-1"
IDENTIFIER = "user-1"
TRAITS: typing.Mapping[str, ContextValue] = {
    "plan": "plan-7",
    "age": 30,
    "country": "GB",
    "version": "2.5.1",
    "email": "jane@example.com",
    "user_id": 12,
    "beta": True,
    "score": 95,
    "tier": "pro",
    "device": "iPhone 15",
}


@pytest.fixture(scope="module", params=["small", "medium", "large"])
def client(request: pytest.FixtureRequest) -> Flagsmith:
    """
    Build a locally evaluating client serving the environment document from memory.
    """
    environment_document = (ENVIRONMENTS_DIR / f"{request.param}.json").read_bytes()

    with responses.RequestsMock() as mocked_responses:
        mocked_responses.get(
            f"{API_URL}environment-document/",
            body=environment_document,
            content_type="application/json",
        )
        client = Flagsmith(
            environment_key="ser.benchmark",
            api_url=API_URL,
            enable_local_evaluation=True,
        )
        client.environment_data_polling_manager_thread.stop()  # Refreshed once, at startup only
        client.environment_data_polling_manager_thread.join()

    return client


@pytest.mark.benchmark
def test_get_environment_flags(client: Flagsmith) -> None:
    """
    Get a feature value from the environment flags.
    """
    client.get_environment_flags().get_feature_value("feature_1")


@pytest.mark.benchmark
def test_get_identity_flags_with_identity_overrides(client: Flagsmith) -> None:
    """
    Check a feature for an identity with identity overrides.
    """
    client.get_identity_flags(IDENTITY_OVERRIDES_IDENTIFIER).is_feature_enabled(
        "feature_8"
    )


@pytest.mark.benchmark
def test_get_identity_flags_no_traits(client: Flagsmith) -> None:
    """
    Get a feature value for an identity without traits.
    """
    client.get_identity_flags(IDENTIFIER).get_feature_value("feature_1")


@pytest.mark.benchmark
def test_get_identity_flags_with_traits(client: Flagsmith) -> None:
    """
    Get a feature value for an identity with traits.
    """
    client.get_identity_flags(IDENTIFIER, TRAITS).get_feature_value("feature_1")


@pytest.mark.benchmark
def test_get_identity_segments_with_traits(client: Flagsmith) -> None:
    """
    List the segments of an identity with traits.
    """
    client.get_identity_segments(IDENTIFIER, TRAITS)
