import time
from datetime import datetime
from unittest.mock import MagicMock, Mock

import requests

from flagsmith import Flagsmith
from flagsmith.exceptions import FlagsmithAPIError
from flagsmith.streaming_manager import EventStreamManager


def test_stream_not_used_by_default(requests_session_response_ok, server_api_key):
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
    )

    assert hasattr(flagsmith, "event_stream_thread") is False


def test_stream_used_when_use_stream_is_true(
    requests_session_response_ok, server_api_key
):
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
        use_stream=True,
    )

    assert hasattr(flagsmith, "event_stream_thread") is True


def test_stream_manager_handles_timeout(mocked_responses):
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


def test_stream_manager_handles_request_exception(mocked_responses, caplog):
    stream_url = (
        "https://realtime.flagsmith.com/sse/environments/B62qaMZNwfiqT76p38ggrQ/stream"
    )

    mocked_responses.get(stream_url, body=requests.RequestException())
    mocked_responses.get(stream_url, body=FlagsmithAPIError())

    streaming_manager = EventStreamManager(
        stream_url=stream_url,
        on_event=MagicMock(),
        daemon=True,
    )

    streaming_manager.start()

    time.sleep(0.01)

    assert streaming_manager.is_alive()

    streaming_manager.stop()

    for record in caplog.records:
        assert record.levelname == "ERROR"
        assert record.message == "Error handling event stream"


def test_environment_updates_on_recent_event(server_api_key, mocker):
    stream_updated_at = datetime(2020, 1, 1, 1, 1, 2)
    environment_updated_at = datetime(2020, 1, 1, 1, 1, 1)

    mocker.patch("flagsmith.Flagsmith.update_environment")

    flagsmith = Flagsmith(environment_key=server_api_key)
    flagsmith._environment = MagicMock()
    flagsmith._environment.updated_at = environment_updated_at

    flagsmith.handle_stream_event(
        event=Mock(
            data=f'{{"updated_at": {stream_updated_at.timestamp()}}}\n\n',
        )
    )

    flagsmith.update_environment.assert_called_once()


def test_environment_does_not_update_on_past_event(server_api_key, mocker):
    stream_updated_at = datetime(2020, 1, 1, 1, 1, 1)
    environment_updated_at = datetime(2020, 1, 1, 1, 1, 2)

    mocker.patch("flagsmith.Flagsmith.update_environment")

    flagsmith = Flagsmith(environment_key=server_api_key)
    flagsmith._environment = MagicMock()
    flagsmith._environment.updated_at = environment_updated_at

    flagsmith.handle_stream_event(
        event=Mock(
            data=f'{{"updated_at": {stream_updated_at.timestamp()}}}\n\n',
        )
    )

    flagsmith.update_environment.assert_not_called()


def test_environment_does_not_update_on_same_event(server_api_key, mocker):
    stream_updated_at = datetime(2020, 1, 1, 1, 1, 1)
    environment_updated_at = datetime(2020, 1, 1, 1, 1, 1)

    mocker.patch("flagsmith.Flagsmith.update_environment")

    flagsmith = Flagsmith(environment_key=server_api_key)
    flagsmith._environment = MagicMock()
    flagsmith._environment.updated_at = environment_updated_at

    flagsmith.handle_stream_event(
        event=Mock(
            data=f'{{"updated_at": {stream_updated_at.timestamp()}}}\n\n',
        )
    )

    flagsmith.update_environment.assert_not_called()
