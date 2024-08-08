import time
from datetime import datetime
from unittest.mock import MagicMock, Mock

import pytest
import requests
import responses
from pytest_mock import MockerFixture

from flagsmith import Flagsmith
from flagsmith.exceptions import FlagsmithAPIError
from flagsmith.streaming_manager import EventStreamManager


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
    assert isinstance(flagsmith.update_environment, Mock)
    flagsmith.update_environment.assert_called_once()


def test_environment_does_not_update_on_past_event(
    server_api_key: str, mocker: MockerFixture
) -> None:
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
    assert isinstance(flagsmith.update_environment, Mock)
    flagsmith.update_environment.assert_not_called()


def test_environment_does_not_update_on_same_event(
    server_api_key: str, mocker: MockerFixture
) -> None:
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
    assert isinstance(flagsmith.update_environment, Mock)
    flagsmith.update_environment.assert_not_called()


def test_invalid_json_payload(server_api_key: str, mocker: MockerFixture) -> None:
    mocker.patch("flagsmith.Flagsmith.update_environment")
    flagsmith = Flagsmith(environment_key=server_api_key)

    with pytest.raises(FlagsmithAPIError):
        flagsmith.handle_stream_event(
            event=Mock(
                data='{"updated_at": test}\n\n',
            )
        )

    with pytest.raises(FlagsmithAPIError):
        flagsmith.handle_stream_event(
            event=Mock(
                data="{{test}}\n\n",
            )
        )

    with pytest.raises(FlagsmithAPIError):
        flagsmith.handle_stream_event(
            event=Mock(
                data="test",
            )
        )


def test_invalid_timestamp_in_payload(
    server_api_key: str, mocker: MockerFixture
) -> None:
    mocker.patch("flagsmith.Flagsmith.update_environment")
    flagsmith = Flagsmith(environment_key=server_api_key)

    with pytest.raises(FlagsmithAPIError):
        flagsmith.handle_stream_event(
            event=Mock(
                data='{"updated_at": "test"}\n\n',
            )
        )

    with pytest.raises(FlagsmithAPIError):
        flagsmith.handle_stream_event(
            event=Mock(
                data='{"test": "test"}\n\n',
            )
        )
