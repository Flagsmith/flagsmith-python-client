import time
from unittest import mock

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
