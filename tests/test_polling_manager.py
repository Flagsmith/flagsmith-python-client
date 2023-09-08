import time
from unittest import mock

import requests

from flagsmith import Flagsmith
from flagsmith.polling_manager import EnvironmentDataPollingManager


def test_polling_manager_calls_update_environment_on_start():
    # Given
    flagsmith = mock.MagicMock()
    polling_manager = EnvironmentDataPollingManager(
        main=flagsmith, refresh_interval_seconds=0.1
    )

    # When
    polling_manager.start()

    # Then
    flagsmith.update_environment.assert_called_once()
    polling_manager.stop()


def test_polling_manager_calls_update_environment_on_each_refresh():
    # Given
    flagsmith = mock.MagicMock()
    polling_manager = EnvironmentDataPollingManager(
        main=flagsmith, refresh_interval_seconds=0.1
    )

    # When
    polling_manager.start()
    time.sleep(0.25)

    # Then
    # 3 calls to update_environment should be made, one when the thread starts and 2
    # for each subsequent refresh
    assert flagsmith.update_environment.call_count == 3
    polling_manager.stop()


def test_polling_manager_is_resilient_to_api_errors(server_api_key):
    with mock.patch("requests.Session") as session_mock:
        # Given
        session_mock.get.return_value = mock.MagicMock(status_code=500)
        flagsmith = Flagsmith(
            environment_key=server_api_key,
            enable_local_evaluation=True,
            environment_refresh_interval_seconds=0.1,
        )
        polling_manager = flagsmith.environment_data_polling_manager_thread

        # Then
        assert polling_manager.is_alive()
        polling_manager.stop()


def test_polling_manager_is_resilient_to_request_exceptions(server_api_key):
    with mock.patch("requests.Session") as session_mock:
        # Given
        session_mock.get.return_value = mock.MagicMock(
            side_effect=requests.RequestException()
        )
        flagsmith = Flagsmith(
            environment_key=server_api_key,
            enable_local_evaluation=True,
            environment_refresh_interval_seconds=0.1,
        )
        polling_manager = flagsmith.environment_data_polling_manager_thread

        # Then
        assert polling_manager.is_alive()
        polling_manager.stop()
