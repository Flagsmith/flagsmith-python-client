import time
from unittest import mock

from flagsmith.polling_manager import PollingManager


def test_polling_manager_calls_callable_to_execute_on_start():
    # Given
    to_execute = mock.MagicMock()
    polling_manager = PollingManager(
        to_execute=to_execute, refresh_interval_seconds=0.1
    )

    # When
    polling_manager.start()

    # Then
    to_execute.assert_called_once()
    polling_manager.stop()


def test_polling_manager_calls_update_environment_on_each_refresh():
    # Given
    to_execute = mock.MagicMock()
    polling_manager = PollingManager(
        to_execute=to_execute, refresh_interval_seconds=0.1
    )

    # When
    polling_manager.start()
    time.sleep(0.25)

    # Then
    # 3 calls to update_environment should be made, one when the thread starts and 2
    # for each subsequent refresh
    assert to_execute.call_count == 3
    polling_manager.stop()
