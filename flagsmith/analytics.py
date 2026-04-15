import atexit
import json
import logging
import threading
import time
import typing
from dataclasses import dataclass
from datetime import datetime

from requests_futures.sessions import FuturesSession  # type: ignore

from flagsmith.version import __version__

logger = logging.getLogger(__name__)

ANALYTICS_ENDPOINT: typing.Final[str] = "analytics/flags/"

# Used to control how often we send data(in seconds)
ANALYTICS_TIMER: typing.Final[int] = 10

session = FuturesSession(max_workers=4)


class AnalyticsProcessor:
    """
    AnalyticsProcessor is used to track how often individual Flags are evaluated within
    the Flagsmith SDK. Docs: https://docs.flagsmith.com/advanced-use/flag-analytics.
    """

    def __init__(
        self, environment_key: str, base_api_url: str, timeout: typing.Optional[int] = 3
    ):
        """
        Initialise the AnalyticsProcessor to handle sending analytics on flag usage to
        the Flagsmith API.

        :param environment_key: environment key obtained from the Flagsmith UI
        :param base_api_url: base api url to override when using self hosted version
        :param timeout: used to tell requests to stop waiting for a response after a
            given number of seconds
        """
        self.analytics_endpoint = base_api_url + ANALYTICS_ENDPOINT
        self.environment_key = environment_key
        self._last_flushed = datetime.now()
        self.analytics_data: typing.MutableMapping[str, typing.Any] = {}
        self.timeout = timeout or 3

    def flush(self) -> None:
        """
        Sends all the collected data to the api asynchronously and resets the timer
        """

        if not self.analytics_data:
            return
        session.post(
            self.analytics_endpoint,
            data=json.dumps(self.analytics_data),
            timeout=self.timeout,
            headers={
                "X-Environment-Key": self.environment_key,
                "Content-Type": "application/json",
            },
        )

        self.analytics_data.clear()
        self._last_flushed = datetime.now()

    def track_feature(self, feature_name: str) -> None:
        self.analytics_data[feature_name] = self.analytics_data.get(feature_name, 0) + 1
        if (datetime.now() - self._last_flushed).seconds > ANALYTICS_TIMER:
            self.flush()


@dataclass
class PipelineAnalyticsConfig:
    analytics_server_url: str
    max_buffer_items: int = 1000
    flush_interval_seconds: float = 10.0


class PipelineAnalyticsProcessor:
    """
    Buffered analytics processor that sends per-evaluation and custom events
    to the Flagsmith pipeline analytics endpoint in batches.

    Evaluation events are deduplicated within each flush window. Events are
    flushed periodically via a background timer or when the buffer is full.
    """

    def __init__(
        self,
        config: PipelineAnalyticsConfig,
        environment_key: str,
    ) -> None:
        url = config.analytics_server_url
        if not url.endswith("/"):
            url = f"{url}/"
        self._batch_endpoint = f"{url}v1/analytics/batch"
        self._environment_key = environment_key
        self._max_buffer = config.max_buffer_items
        self._flush_interval_seconds = config.flush_interval_seconds

        self._buffer: typing.List[typing.Dict[str, typing.Any]] = []
        self._dedup_keys: typing.Dict[str, str] = {}
        self._lock = threading.Lock()
        self._timer: typing.Optional[threading.Timer] = None

    def record_evaluation_event(
        self,
        flag_key: str,
        enabled: bool,
        value: typing.Any,
        identity_identifier: typing.Optional[str] = None,
        traits: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> None:
        fingerprint = f"{identity_identifier or 'none'}|{enabled}|{value}"
        should_flush = False

        with self._lock:
            if self._dedup_keys.get(flag_key) == fingerprint:
                return
            self._dedup_keys[flag_key] = fingerprint
            self._buffer.append(
                {
                    "event_id": flag_key,
                    "event_type": "flag_evaluation",
                    "evaluated_at": int(time.time() * 1000),
                    "identity_identifier": identity_identifier,
                    "enabled": enabled,
                    "value": value,
                    "traits": dict(traits) if traits else None,
                    "metadata": {"sdk_version": __version__},
                }
            )
            if len(self._buffer) >= self._max_buffer:
                should_flush = True

        if should_flush:
            self.flush()

    def record_custom_event(
        self,
        event_name: str,
        identity_identifier: typing.Optional[str] = None,
        traits: typing.Optional[typing.Dict[str, typing.Any]] = None,
        metadata: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> None:
        should_flush = False

        with self._lock:
            self._buffer.append(
                {
                    "event_id": event_name,
                    "event_type": "custom_event",
                    "evaluated_at": int(time.time() * 1000),
                    "identity_identifier": identity_identifier,
                    "enabled": None,
                    "value": None,
                    "traits": dict(traits) if traits else None,
                    "metadata": {**(metadata or {}), "sdk_version": __version__},
                }
            )
            if len(self._buffer) >= self._max_buffer:
                should_flush = True

        if should_flush:
            self.flush()

    def flush(self) -> None:
        with self._lock:
            if not self._buffer:
                return
            events = self._buffer
            self._buffer = []
            self._dedup_keys.clear()

        payload = json.dumps(
            {"events": events, "environment_key": self._environment_key}
        )
        try:
            future = session.post(
                self._batch_endpoint,
                data=payload,
                timeout=3,
                headers={
                    "Content-Type": "application/json; charset=utf-8",
                    "X-Environment-Key": self._environment_key,
                    "Flagsmith-SDK-User-Agent": f"flagsmith-python-client/{__version__}",
                },
            )
        except RuntimeError:
            logger.debug("Skipping flush: thread pool already shut down")
            return
        future.add_done_callback(lambda f: self._handle_flush_result(f, events))

    def _handle_flush_result(
        self,
        future: typing.Any,
        events: typing.List[typing.Dict[str, typing.Any]],
    ) -> None:
        try:
            response = future.result()
            response.raise_for_status()
        except Exception:
            logger.warning(
                "Failed to flush pipeline analytics, re-queuing events", exc_info=True
            )
            with self._lock:
                self._buffer = events + self._buffer
                self._buffer = self._buffer[: self._max_buffer]

    def start(self) -> None:
        self._schedule_flush()
        atexit.register(self.stop)

    def stop(self) -> None:
        atexit.unregister(self.stop)
        if self._timer is not None:
            self._timer.cancel()
        self.flush()

    def _schedule_flush(self) -> None:
        self._timer = threading.Timer(self._flush_interval_seconds, self._timer_flush)
        self._timer.daemon = True
        self._timer.start()

    def _timer_flush(self) -> None:
        self.flush()
        self._schedule_flush()
