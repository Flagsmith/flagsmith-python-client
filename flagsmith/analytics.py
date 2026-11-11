import atexit
import enum
import json
import logging
import random
import threading
import typing
from dataclasses import dataclass
from datetime import datetime

import requests
from requests_futures.sessions import FuturesSession  # type: ignore

from flagsmith.version import DEFAULT_USER_AGENT, __version__

logger = logging.getLogger(__name__)

ANALYTICS_ENDPOINT: typing.Final[str] = "analytics/flags/"

# Used to control how often we send data(in seconds)
ANALYTICS_TIMER: typing.Final[int] = 10

FLAG_EXPOSURE_EVENT: typing.Final[str] = "$flag_exposure"

DEFAULT_EVENT_API_URL: typing.Final[str] = "https://events.api.flagsmith.com/"

EVENTS_REQUEST_TIMEOUT_SECONDS: typing.Final[float] = 3
EVENTS_MAX_ATTEMPTS: typing.Final[int] = 3
EVENTS_RETRY_BASE_SECONDS: typing.Final[float] = 1
DEFAULT_EVENTS_CLOSE_TIMEOUT_SECONDS: typing.Final[float] = 5
RETRIED_STATUS_CODES: typing.Final[typing.FrozenSet[int]] = frozenset({408, 429})

session = FuturesSession(max_workers=4)


class AnalyticsProcessor:
    """
    AnalyticsProcessor is used to track how often individual Flags are evaluated within
    the Flagsmith SDK. Docs: https://docs.flagsmith.com/advanced-use/flag-analytics.
    """

    def __init__(
        self,
        environment_key: str,
        base_api_url: str,
        timeout: typing.Optional[int] = 3,
        analytics_url: typing.Optional[str] = None,
    ):
        """
        Initialise the AnalyticsProcessor to handle sending analytics on flag usage to
        the Flagsmith API.

        :param environment_key: environment key obtained from the Flagsmith UI
        :param base_api_url: base api url to override when using self hosted version
        :param timeout: used to tell requests to stop waiting for a response after a
            given number of seconds
        :param analytics_url: full URL of the flag analytics endpoint, used to override
            the default ``<base_api_url>/analytics/flags/``. Intended for deployments
            where flag evaluation traffic and analytics traffic must go to different
            hosts (for example, evaluating through the Edge Proxy while sending
            analytics to the core API).
        """
        self.analytics_endpoint = analytics_url or (base_api_url + ANALYTICS_ENDPOINT)
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


class ExposureKey(typing.NamedTuple):
    feature_name: typing.Optional[str]
    identifier: typing.Optional[str]
    value: typing.Optional[str]


@dataclass
class EventProcessorConfig:
    events_api_url: str = DEFAULT_EVENT_API_URL
    max_buffer_items: int = 1000
    flush_interval_seconds: float = 10.0


class _DeliveryOutcome(enum.Enum):
    DELIVERED = "delivered"
    DROPPED = "dropped"
    KEPT = "kept"
    REFUSED = "refused"


class EventProcessor:
    """
    Buffered event processor that batches custom events and POSTs them to the
    Flagsmith event endpoint. Flushes on a background timer or when the buffer
    fills.

    A batch is sent up to ``EVENTS_MAX_ATTEMPTS`` times, backing off with full
    jitter between attempts, one batch at a time. A batch whose last attempt
    fails transiently is kept for the next flush, unless that attempt got a
    500. A batch the events API rejects is dropped, and an events API refusing
    the environment key stops event tracking. When the buffer is full, the
    oldest event is dropped.
    """

    def __init__(
        self,
        config: EventProcessorConfig,
        environment_key: str,
    ) -> None:
        url = config.events_api_url
        if not url.endswith("/"):
            url = f"{url}/"
        self._batch_endpoint = f"{url}v1/events"
        self._environment_key = environment_key
        self._max_buffer = config.max_buffer_items
        self._flush_interval_seconds = config.flush_interval_seconds

        self._session = requests.Session()
        self._buffer: typing.List[typing.Dict[str, typing.Any]] = []
        self._buffered_exposure_keys: typing.Set[ExposureKey] = set()
        self._lock = threading.Lock()
        # Held while a batch is in flight, so that one batch is sent at a time.
        self._send_lock = threading.Lock()
        self._tracked_count = 0
        self._attempted_count = 0
        self._full_buffer_flush_pending = False
        self._refused = False
        self._stopped = threading.Event()
        self._closed = threading.Event()
        self._timer: typing.Optional[threading.Timer] = None

    def track_event(
        self,
        event: str,
        identifier: typing.Optional[str] = None,
        value: typing.Optional[typing.Union[str, int, float, bool]] = None,
        traits: typing.Optional[typing.Dict[str, typing.Any]] = None,
        metadata: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> None:
        self._buffer_event(
            event=event,
            feature_name=None,
            identifier=identifier,
            value=value,
            traits=traits,
            metadata=metadata,
        )

    def track_exposure_event(
        self,
        feature_name: str,
        identifier: typing.Optional[str] = None,
        value: typing.Optional[typing.Union[str, int, float, bool]] = None,
        traits: typing.Optional[typing.Dict[str, typing.Any]] = None,
        metadata: typing.Optional[typing.Dict[str, typing.Any]] = None,
    ) -> None:
        self._buffer_event(
            event=FLAG_EXPOSURE_EVENT,
            feature_name=feature_name,
            identifier=identifier,
            value=value,
            traits=traits,
            metadata=metadata,
        )

    def _buffer_event(
        self,
        event: str,
        feature_name: typing.Optional[str],
        identifier: typing.Optional[str],
        value: typing.Optional[typing.Union[str, int, float, bool]],
        traits: typing.Optional[typing.Dict[str, typing.Any]],
        metadata: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> None:
        with self._lock:
            if self._refused:
                logger.debug(
                    "Not tracking %s event: the events API refused the"
                    " environment key.",
                    event,
                )
                return
            if event == FLAG_EXPOSURE_EVENT:
                # An exposure is defined by who saw which variant of which
                # feature; equal exposures within one flush interval add no
                # information, so only the first is buffered.
                exposure_key = ExposureKey(
                    feature_name=feature_name,
                    identifier=identifier,
                    value=str(value) if value is not None else None,
                )
                if exposure_key in self._buffered_exposure_keys:
                    logger.debug(
                        "Skipping duplicate %s event for feature %s, identifier %s",
                        FLAG_EXPOSURE_EVENT,
                        feature_name,
                        identifier,
                    )
                    return
                self._buffered_exposure_keys.add(exposure_key)
            if len(self._buffer) >= self._max_buffer:
                dropped = self._buffer.pop(0)
                logger.warning(
                    "Event buffer is full, dropping the oldest %s event",
                    dropped["event"],
                )
            self._buffer.append(
                {
                    "event": event,
                    "feature_name": feature_name,
                    "identifier": identifier,
                    "value": str(value) if value is not None else None,
                    "traits": dict(traits) if traits else None,
                    "metadata": {**(metadata or {}), "sdk_version": __version__},
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
            )
            self._tracked_count += 1
            if len(self._buffer) < self._max_buffer or (
                self._full_buffer_flush_pending
            ):
                return
            self._full_buffer_flush_pending = True
            tracked_count = self._tracked_count

        threading.Thread(
            target=self._flush_full_buffer, args=(tracked_count,), daemon=True
        ).start()

    def flush(self) -> None:
        """
        Sends the events tracked so far, and returns once each of them has
        been delivered, dropped, or kept for the next flush. Events already
        sent while this was waiting for another batch in flight are not sent
        again.
        """
        with self._lock:
            tracked_count = self._tracked_count
        self._send(tracked_count)

    def _flush_full_buffer(self, tracked_count: int) -> None:
        with self._lock:
            self._full_buffer_flush_pending = False
        self._send(tracked_count)

    def _send(self, tracked_count: typing.Optional[int] = None) -> None:
        """
        Sends the buffered events as one batch. Given `tracked_count`, does
        nothing if every event tracked up to it has been sent already.
        """
        with self._send_lock:
            with self._lock:
                if not self._buffer or (
                    tracked_count is not None and self._attempted_count >= tracked_count
                ):
                    return
                events = self._buffer
                self._buffer = []
                self._buffered_exposure_keys.clear()
                attempted_count = self._tracked_count

            outcome = self._deliver(events)

            with self._lock:
                self._attempted_count = attempted_count
                if outcome is _DeliveryOutcome.KEPT:
                    max_buffer = self._max_buffer
                    self._buffer = (events + self._buffer)[-max_buffer:]
                elif outcome is _DeliveryOutcome.REFUSED:
                    self._refused = True
                    self._buffer = []
                    self._buffered_exposure_keys.clear()

    def _deliver(
        self, events: typing.List[typing.Dict[str, typing.Any]]
    ) -> _DeliveryOutcome:
        payload = json.dumps({"events": events})
        for attempt in range(1, EVENTS_MAX_ATTEMPTS + 1):
            if attempt > 1:
                backoff = EVENTS_RETRY_BASE_SECONDS * 2 ** (attempt - 2)
                if self._closed.wait(random.uniform(0, backoff)):
                    logger.warning(
                        "Not retrying %d events: the client is closed", len(events)
                    )
                    return _DeliveryOutcome.KEPT
            try:
                response = self._session.post(
                    self._batch_endpoint,
                    data=payload,
                    timeout=EVENTS_REQUEST_TIMEOUT_SECONDS,
                    headers={
                        "Content-Type": "application/json; charset=utf-8",
                        "X-Environment-Key": self._environment_key,
                        "Flagsmith-SDK-User-Agent": DEFAULT_USER_AGENT,
                    },
                )
            except requests.RequestException as e:
                logger.warning(
                    "Failed to send %d events, attempt %d of %d: %s",
                    len(events),
                    attempt,
                    EVENTS_MAX_ATTEMPTS,
                    e,
                )
                status = None
            else:
                status = response.status_code
                if response.ok:
                    return _DeliveryOutcome.DELIVERED
                if status in (401, 403):
                    logger.error(
                        "Events API refused the environment key with %d,"
                        " stopping event tracking",
                        status,
                    )
                    return _DeliveryOutcome.REFUSED
                if status not in RETRIED_STATUS_CODES and status < 500:
                    logger.warning(
                        "Events API rejected %d events with %d, dropping them",
                        len(events),
                        status,
                    )
                    return _DeliveryOutcome.DROPPED
                logger.warning(
                    "Failed to send %d events, attempt %d of %d: status %d",
                    len(events),
                    attempt,
                    EVENTS_MAX_ATTEMPTS,
                    status,
                )
        if status == 500:
            logger.warning(
                "Dropping %d events the events API failed with 500", len(events)
            )
            return _DeliveryOutcome.DROPPED
        logger.warning("Keeping %d events for the next flush", len(events))
        return _DeliveryOutcome.KEPT

    def start(self) -> None:
        self._schedule_flush()
        atexit.register(self.stop)

    def stop(
        self, timeout_seconds: float = DEFAULT_EVENTS_CLOSE_TIMEOUT_SECONDS
    ) -> None:
        """
        Stops flushing on a timer, and sends the buffered events, waiting for
        at most `timeout_seconds`. Events not sent by then are not retried.
        """
        atexit.unregister(self.stop)
        self._stopped.set()
        if self._timer is not None:
            self._timer.cancel()
        final_flush = threading.Thread(target=self._send, daemon=True)
        final_flush.start()
        final_flush.join(timeout_seconds)
        self._closed.set()
        if final_flush.is_alive():
            logger.warning(
                "Gave up sending events after %s seconds while closing",
                timeout_seconds,
            )

    def _schedule_flush(self) -> None:
        if self._stopped.is_set():
            return
        self._timer = threading.Timer(self._flush_interval_seconds, self._timer_flush)
        self._timer.daemon = True
        self._timer.start()

    def _timer_flush(self) -> None:
        self._send()
        self._schedule_flush()
