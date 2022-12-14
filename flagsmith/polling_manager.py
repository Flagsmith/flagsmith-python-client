import threading
import time
import typing


class PollingManager(threading.Thread):
    def __init__(
        self,
        to_execute: typing.Callable,
        refresh_interval_seconds: typing.Union[int, float] = 10,
    ):
        super(PollingManager, self).__init__()
        self._stop_event = threading.Event()
        self._callable = to_execute
        self.refresh_interval_seconds = refresh_interval_seconds

    def run(self) -> None:
        while not self._stop_event.is_set():
            self._callable()
            time.sleep(self.refresh_interval_seconds)

    def stop(self) -> None:
        self._stop_event.set()

    def __del__(self):
        self._stop_event.set()
