import json
import multiprocessing
import time
from pathlib import Path
from unittest import mock

import pytest
import requests
import responses
from pytest_httpserver import HTTPServer
from pytest_mock import MockerFixture

from flagsmith import Flagsmith
from flagsmith.polling_manager import EnvironmentDataPollingManager


def test_polling_manager_calls_update_environment_on_start() -> None:
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


def test_polling_manager_calls_update_environment_on_each_refresh() -> None:
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


@responses.activate()
def test_polling_manager_is_resilient_to_api_errors(
    flagsmith: Flagsmith,
    environment_json: str,
    mocker: MockerFixture,
    server_api_key: str,
) -> None:
    # Given
    responses.add(method="GET", url=flagsmith.environment_url, body=environment_json)
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
        environment_refresh_interval_seconds=0.1,
    )

    responses.add(method="GET", url=flagsmith.environment_url, status=500)
    polling_manager = flagsmith.environment_data_polling_manager_thread

    # Then
    assert polling_manager.is_alive()
    polling_manager.stop()


@responses.activate()
def test_polling_manager_is_resilient_to_request_exceptions(
    flagsmith: Flagsmith,
    environment_json: str,
    mocker: MockerFixture,
    server_api_key: str,
) -> None:
    # Given
    responses.add(method="GET", url=flagsmith.environment_url, body=environment_json)
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
        environment_refresh_interval_seconds=0.1,
    )

    responses.add(
        method="GET",
        url=flagsmith.environment_url,
        body=requests.RequestException("Some exception"),
        status=500,
    )
    polling_manager = flagsmith.environment_data_polling_manager_thread

    # Then
    assert polling_manager.is_alive()
    polling_manager.stop()


@pytest.fixture
def api_url(
    httpserver: HTTPServer,
    request: pytest.FixtureRequest,
) -> str:
    """A local HTTP server impersonating the Flagsmith environment-document API."""
    body = (request.path.parent / "data/environment.json").read_bytes()
    httpserver.expect_request("/api/v1/environment-document/").respond_with_data(
        body, content_type="application/json"
    )
    return httpserver.url_for("/api/v1/")


@pytest.mark.skipif(
    "fork" not in multiprocessing.get_all_start_methods(),
    reason="fork() is unavailable on this platform",
)
def test_polling_manager_keeps_polling_after_fork(api_url: str, tmp_path: Path) -> None:
    # Given a flagsmith client polling against a local HTTP server.
    flagsmith = Flagsmith(
        environment_key="ser.dummy",
        api_url=api_url,
        enable_local_evaluation=True,
        environment_refresh_interval_seconds=0.1,
    )
    parent_ident = flagsmith.environment_data_polling_manager_thread.ident

    def _record_polling_state_in_child(flagsmith: Flagsmith, result_path: Path) -> None:
        # Give the child a chance to poll.
        time.sleep(0.1)
        polling = flagsmith.environment_data_polling_manager_thread
        result_path.write_text(
            json.dumps({"is_alive": polling.is_alive(), "ident": polling.ident})
        )

    # Give the parent a chance to poll.
    time.sleep(0.1)
    result_path = tmp_path / "child_result.json"

    # When the process forks (mimicking a gunicorn pre-fork worker).
    proc = multiprocessing.get_context("fork").Process(
        target=_record_polling_state_in_child, args=(flagsmith, result_path)
    )
    proc.start()
    proc.join()

    # Then the polling thread is alive in the child, and it's a fresh
    # thread rather than the parent's (dead) one.
    result = json.loads(result_path.read_text())
    assert result["is_alive"], "polling thread did not survive fork()"
    assert result["ident"] != parent_ident
    flagsmith.environment_data_polling_manager_thread.stop()
