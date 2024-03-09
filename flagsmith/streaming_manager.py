import logging
import threading
import typing
from typing import Callable, Generator, Optional, Protocol, cast

import requests
import sseclient

from flagsmith.exceptions import FlagsmithAPIError

logger = logging.getLogger(__name__)


class StreamEvent(Protocol):
    data: str


class EventStreamManager(threading.Thread):
    def __init__(
        self,
        *args: typing.Any,
        stream_url: str,
        on_event: Callable[[StreamEvent], None],
        request_timeout_seconds: Optional[int] = None,
        **kwargs: typing.Any
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
                    sse_client = sseclient.SSEClient(
                        cast(Generator[bytes, None, None], response)
                    )
                    for event in sse_client.events():
                        self.on_event(event)

            except requests.exceptions.ReadTimeout:
                pass

            except (FlagsmithAPIError, requests.RequestException):
                logger.exception("Error handling event stream")

    def stop(self) -> None:
        self._stop_event.set()

    def __del__(self) -> None:
        self._stop_event.set()
