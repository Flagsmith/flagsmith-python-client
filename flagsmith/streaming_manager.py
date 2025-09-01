import logging
import threading
import typing
from typing import Callable, Optional

import requests
import sseclient

from flagsmith.mappers import map_sse_event_to_stream_event
from flagsmith.types import StreamEvent

logger = logging.getLogger(__name__)


class EventStreamManager(threading.Thread):
    def __init__(
        self,
        *args: typing.Any,
        stream_url: str,
        on_event: Callable[[StreamEvent], None],
        request_timeout_seconds: Optional[int] = None,
        **kwargs: typing.Any,
    ) -> None:
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
                    sse_client = sseclient.SSEClient(chunk for chunk in response)
                    for event in sse_client.events():
                        self.on_event(map_sse_event_to_stream_event(event))

            except (requests.RequestException, ValueError, TypeError):
                logger.exception("Error opening or reading from the event stream")

    def stop(self) -> None:
        self._stop_event.set()

    def __del__(self) -> None:
        self._stop_event.set()
