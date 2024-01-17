import json
import os
import random
import string

import pytest
import responses
from flag_engine.environments.models import EnvironmentModel

from flagsmith import Flagsmith
from flagsmith.analytics import AnalyticsProcessor

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@pytest.fixture()
def analytics_processor():
    return AnalyticsProcessor(
        environment_key="test_key", base_api_url="http://test_url"
    )


@pytest.fixture(scope="session")
def api_key():
    return "".join(random.sample(string.ascii_letters, 20))


@pytest.fixture(scope="session")
def server_api_key():
    return "ser.%s" % "".join(random.sample(string.ascii_letters, 20))


@pytest.fixture()
def flagsmith(api_key):
    return Flagsmith(environment_key=api_key)


@pytest.fixture()
def environment_json():
    with open(os.path.join(DATA_DIR, "environment.json"), "rt") as f:
        yield f.read()


@pytest.fixture()
def requests_session_response_ok(mocker, environment_json):
    mock_session = mocker.MagicMock()
    mocker.patch("flagsmith.flagsmith.requests.Session", return_value=mock_session)

    mock_environment_document_response = mocker.MagicMock(status_code=200)
    mock_environment_document_response.json.return_value = json.loads(environment_json)
    mock_session.get.return_value = mock_environment_document_response

    return mock_session


@pytest.fixture()
def local_eval_flagsmith(requests_session_response_ok, server_api_key):
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
        environment_refresh_interval_seconds=0.1,
    )

    yield flagsmith

    del flagsmith


@pytest.fixture()
def environment_model(environment_json: str) -> EnvironmentModel:
    return EnvironmentModel.model_validate_json(environment_json)


@pytest.fixture()
def flags_json():
    with open(os.path.join(DATA_DIR, "flags.json"), "rt") as f:
        yield f.read()


@pytest.fixture()
def identities_json():
    with open(os.path.join(DATA_DIR, "identities.json"), "rt") as f:
        yield f.read()


@pytest.fixture
def mocked_responses():
    with responses.RequestsMock() as rsps:
        yield rsps
