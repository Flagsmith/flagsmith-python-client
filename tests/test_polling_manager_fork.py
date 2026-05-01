import json
import multiprocessing
import time
import typing
from pathlib import Path

import pytest

# pytest-httpserver requires python>=3.10 — skip the whole module on
# older interpreters where the dep isn't installed.
pytest.importorskip("pytest_httpserver")

from flagsmith import Flagsmith  # noqa: E402

if typing.TYPE_CHECKING:
    from pytest_httpserver import HTTPServer


@pytest.fixture
def api_url(httpserver: "HTTPServer", request: pytest.FixtureRequest) -> str:
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
