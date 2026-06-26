from __future__ import annotations

import logging
import threading
import typing

if typing.TYPE_CHECKING:
    from flagsmith import Flagsmith

logger = logging.getLogger(__name__)


class EnvironmentDataPollingManager(threading.Thread):
    def __init__(
        self,
        *args: typing.Any,
        main: Flagsmith,
        refresh_interval_seconds: typing.Union[int, float] = 10,
        **kwargs: typing.Any,
    ):
        super(EnvironmentDataPollingManager, self).__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.main = main
        self.refresh_interval_seconds = refresh_interval_seconds

    def run(self) -> None:
        # Wait on the stop event rather than sleeping so stop() interrupts
        # the interval immediately and the thread can be joined promptly.
        while not self._stop_event.is_set():
            try:
                self.main.update_environment()
            except Exception:
                # Never let an unexpected error kill the polling thread; log
                # it and try again on the next interval.
                logger.exception("Error updating environment")
            self._stop_event.wait(self.refresh_interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()

    def __del__(self) -> None:
        self._stop_event.set()
