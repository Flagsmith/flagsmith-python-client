from __future__ import annotations

import logging
import os
import threading
import time
import typing

if typing.TYPE_CHECKING:
    from flagsmith import Flagsmith

logger = logging.getLogger(__name__)


class EnvironmentDataPollingManager:
    """Owns the worker thread that periodically refreshes the local
    evaluation environment document.

    Composes (rather than extends) :class:`threading.Thread` so the
    worker can be replaced — most importantly after :func:`os.fork`,
    where threads do not survive into the child. We register an at-fork
    hook so a forked worker (gunicorn, uwsgi, multiprocessing) gets a
    freshly-started polling thread for its own PID. See issue #77.
    """

    def __init__(
        self,
        *,
        main: Flagsmith,
        refresh_interval_seconds: typing.Union[int, float] = 10,
    ) -> None:
        self._main = main
        self._refresh_interval_seconds = refresh_interval_seconds
        self._stop_event = threading.Event()
        self._thread = self._build_thread()
        self._at_fork_registered = False

    def _build_thread(self) -> threading.Thread:
        return threading.Thread(target=self._run, daemon=True)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self._main.update_environment()
            time.sleep(self._refresh_interval_seconds)

    def start(self) -> None:
        self._thread.start()
        if not self._at_fork_registered and hasattr(os, "register_at_fork"):
            os.register_at_fork(after_in_child=self._restart_after_fork)
            self._at_fork_registered = True

    def _restart_after_fork(self) -> None:
        if self._thread.is_alive():
            return
        # Sockets in the parent's connection pool are inherited as
        # shared FDs across fork; reusing them would interleave bytes
        # between processes. Drop them so the new thread opens fresh.
        if session := getattr(self._main, "session", None):
            session.close()
        self._stop_event = threading.Event()
        self._thread = self._build_thread()
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()

    def is_alive(self) -> bool:
        return self._thread.is_alive()

    @property
    def ident(self) -> typing.Optional[int]:
        return self._thread.ident

    def __del__(self) -> None:
        self._stop_event.set()
