import json
import os
import random
import string
import typing
from typing import Generator

import pytest
import responses
from pyfakefs.fake_filesystem import FakeFilesystem
from pytest_mock import MockerFixture

from flagsmith import Flagsmith
from flagsmith.analytics import (
    AnalyticsProcessor,
    EventProcessor,
    EventProcessorConfig,
)
from flagsmith.api.types import EnvironmentModel
from flagsmith.mappers import map_environment_document_to_context
from flagsmith.types import SDKEvaluationContext

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")


@pytest.fixture(autouse=True)
def stop_flagsmith_background_threads(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[None, None, None]:
    # Flagsmith starts polling, streaming and event-processor background
    # threads. Track every instance created during a test and stop its threads
    # on teardown so they don't leak across the suite (mirroring __del__, but
    # deterministically rather than at GC).
    instances: typing.List[Flagsmith] = []
    original_init = Flagsmith.__init__

    def tracking_init(self: Flagsmith, *args: typing.Any, **kwargs: typing.Any) -> None:
        instances.append(self)
        original_init(self, *args, **kwargs)

    monkeypatch.setattr(Flagsmith, "__init__", tracking_init)
    yield
    for flagsmith in instances:
        if polling := getattr(
            flagsmith, "environment_data_polling_manager_thread", None
        ):
            polling.stop()
            polling.join(timeout=5)
        if stream := getattr(flagsmith, "event_stream_thread", None):
            stream.stop()
            stream.join(timeout=5)
        if flagsmith._event_processor:
            flagsmith._event_processor.stop()


@pytest.fixture()
def analytics_processor() -> AnalyticsProcessor:
    return AnalyticsProcessor(
        environment_key="test_key", base_api_url="http://test_url"
    )


@pytest.fixture()
def event_processor_config() -> EventProcessorConfig:
    return EventProcessorConfig(events_api_url="http://test_analytics/")


@pytest.fixture()
def event_processor(
    event_processor_config: EventProcessorConfig,
) -> EventProcessor:
    return EventProcessor(
        config=event_processor_config,
        environment_key="test_key",
    )


@pytest.fixture(scope="session")
def api_key() -> str:
    return "".join(random.sample(string.ascii_letters, 20))


@pytest.fixture(scope="session")
def server_api_key() -> str:
    return "ser.%s" % "".join(random.sample(string.ascii_letters, 20))


@pytest.fixture()
def flagsmith(api_key: str) -> Flagsmith:
    return Flagsmith(environment_key=api_key)


@pytest.fixture()
def environment_json(fs: FakeFilesystem) -> typing.Generator[str, None, None]:
    environment_json_path = os.path.join(DATA_DIR, "environment.json")
    fs.add_real_file(environment_json_path)
    with open(environment_json_path, "rt") as f:
        yield f.read()


@pytest.fixture()
def requests_session_response_ok(mocker: MockerFixture, environment_json: str) -> None:
    mock_session = mocker.MagicMock()
    mocker.patch("flagsmith.flagsmith.requests.Session", return_value=mock_session)

    mock_environment_document_response = mocker.MagicMock(status_code=200)
    mock_environment_document_response.json.return_value = json.loads(environment_json)
    mock_session.get.return_value = mock_environment_document_response


@pytest.fixture()
def local_eval_flagsmith(
    requests_session_response_ok: None, server_api_key: str
) -> Generator[Flagsmith, None, None]:
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
        environment_refresh_interval_seconds=0.1,
    )

    yield flagsmith

    del flagsmith


@pytest.fixture()
def environment(environment_json: str) -> EnvironmentModel:
    ret: EnvironmentModel = json.loads(environment_json)
    return ret


@pytest.fixture()
def evaluation_context(environment: EnvironmentModel) -> SDKEvaluationContext:
    return map_environment_document_to_context(environment)


@pytest.fixture()
def flags_json() -> typing.Generator[str, None, None]:
    with open(os.path.join(DATA_DIR, "flags.json"), "rt") as f:
        yield f.read()


@pytest.fixture()
def identities_json() -> typing.Generator[str, None, None]:
    with open(os.path.join(DATA_DIR, "identities.json"), "rt") as f:
        yield f.read()


@pytest.fixture
def mocked_responses() -> Generator["responses.RequestsMock", None, None]:
    with responses.RequestsMock() as rsps:
        yield rsps
