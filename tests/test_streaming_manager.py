import time
from datetime import datetime, timezone
from unittest.mock import MagicMock

import requests
import responses
from pytest_mock import MockerFixture

from flagsmith import Flagsmith
from flagsmith.local_evaluation import LocalEvaluation
from flagsmith.streaming_manager import EventStreamManager
from flagsmith.types import StreamEvent


def test_stream_manager_handles_timeout(
    mocked_responses: responses.RequestsMock,
) -> None:
    stream_url = (
        "https://realtime.flagsmith.com/sse/environments/B62qaMZNwfiqT76p38ggrQ/stream"
    )

    mocked_responses.get(stream_url, body=requests.exceptions.ReadTimeout())

    streaming_manager = EventStreamManager(
        stream_url=stream_url,
        on_event=MagicMock(),
        daemon=True,
    )

    streaming_manager.start()

    time.sleep(0.01)

    assert streaming_manager.is_alive()

    streaming_manager.stop()


def test_environment_updates_on_recent_event(
    server_api_key: str, mocker: MockerFixture
) -> None:
    stream_updated_at = datetime(2020, 1, 1, 1, 1, 2, tzinfo=timezone.utc)
    environment_updated_at = datetime(2020, 1, 1, 1, 1, 1, tzinfo=timezone.utc)

    flagsmith = Flagsmith(environment_key=server_api_key)
    update_environment = mocker.patch.object(flagsmith, "update_environment")
    flagsmith._local_evaluation = MagicMock(spec=LocalEvaluation)
    flagsmith._environment_updated_at = environment_updated_at

    flagsmith.handle_stream_event(event=StreamEvent(updated_at=stream_updated_at))

    update_environment.assert_called_once_with()


def test_environment_does_not_update_on_past_event(
    server_api_key: str, mocker: MockerFixture
) -> None:
    stream_updated_at = datetime(2020, 1, 1, 1, 1, 1, tzinfo=timezone.utc)
    environment_updated_at = datetime(2020, 1, 1, 1, 1, 2, tzinfo=timezone.utc)

    flagsmith = Flagsmith(environment_key=server_api_key)
    update_environment = mocker.patch.object(flagsmith, "update_environment")
    flagsmith._local_evaluation = MagicMock(spec=LocalEvaluation)
    flagsmith._environment_updated_at = environment_updated_at

    flagsmith.handle_stream_event(event=StreamEvent(updated_at=stream_updated_at))

    update_environment.assert_not_called()


def test_environment_does_not_update_on_same_event(
    server_api_key: str, mocker: MockerFixture
) -> None:
    stream_updated_at = datetime(2020, 1, 1, 1, 1, 1, tzinfo=timezone.utc)
    environment_updated_at = datetime(2020, 1, 1, 1, 1, 1, tzinfo=timezone.utc)

    flagsmith = Flagsmith(environment_key=server_api_key)
    update_environment = mocker.patch.object(flagsmith, "update_environment")
    flagsmith._local_evaluation = MagicMock(spec=LocalEvaluation)
    flagsmith._environment_updated_at = environment_updated_at

    flagsmith.handle_stream_event(event=StreamEvent(updated_at=stream_updated_at))

    update_environment.assert_not_called()
