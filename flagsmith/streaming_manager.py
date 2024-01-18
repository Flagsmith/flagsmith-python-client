import logging
import threading

import requests
import sseclient

from flagsmith.exceptions import FlagsmithAPIError

logger = logging.getLogger(__name__)


class EventStreamManager(threading.Thread):
    def __init__(
        self, *args, stream_url, on_event, request_timeout_seconds=None, **kwargs
    ):
        super().__init__(*args, **kwargs)
        self._stop_event = threading.Event()
        self.stream_url = stream_url
        self.on_event = on_event
        self.request_timeout_seconds = request_timeout_seconds

    def run(self) -> None:
        while not self._stop_event.is_set():
            try:
                with requests.get(
                    self.stream_url,
                    stream=True,
                    headers={"Accept": "application/json, text/event-stream"},
                    timeout=self.request_timeout_seconds,
                ) as response:
                    sse_client = sseclient.SSEClient(response)
                    for event in sse_client.events():
                        self.on_event(event)

            except requests.exceptions.ReadTimeout:
                pass

            except (FlagsmithAPIError, requests.RequestException):
                logger.exception("Error handling event stream")

    def stop(self) -> None:
        self._stop_event.set()

    def __del__(self):
        self._stop_event.set()
