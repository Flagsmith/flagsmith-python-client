import atexit
import enum
import json
import logging
import random
import threading
import time
import typing
from collections import deque
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
RETRIED_STATUS_CODES: typing.Final[typing.FrozenSet[int]] = frozenset(
    {408, 429, 500, 502, 503, 504}
)

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


class _BufferedEvent(typing.NamedTuple):
    payload: str
    exposure_key: typing.Optional[ExposureKey]


class _DeliveryOutcome(enum.Enum):
    DELIVERED = "delivered"
    DROPPED = "dropped"
    KEPT = "kept"
    REFUSED = "refused"


class EventProcessor:
    """
    Buffered event processor that batches custom events and POSTs them to the
    Flagsmith event endpoint, from one worker thread. The worker sends the
    buffered events on a timer, when the buffer fills, on `flush`, and once
    more on `close`.

    A batch is sent up to ``EVENTS_MAX_ATTEMPTS`` times, backing off with full
    jitter between attempts. A batch whose last attempt fails transiently is
    kept for the next send, unless that attempt got a 500. A batch the events
    API rejects is dropped, and an events API refusing the environment key
    stops event tracking. When the buffer is full, the oldest event is dropped.
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
        self._condition = threading.Condition()
        self._buffer: typing.Deque[_BufferedEvent] = deque()
        self._buffered_exposure_keys: typing.Set[ExposureKey] = set()
        self._tracked_count = 0
        self._sent_count = 0
        # Events tracked up to this count are being sent, if a send is running.
        self._sending_count: typing.Optional[int] = None
        self._flush_requested = False
        self._sends_started = 0
        self._sends_completed = 0
        self._refused = False
        self._closed = False
        # Set once `close` returns: the worker starts no more requests.
        self._abandoned = threading.Event()

        self._worker = threading.Thread(
            target=self._run, name="flagsmith-event-processor", daemon=True
        )
        self._worker.start()
        atexit.register(self.close)

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
        try:
            serialised_event = json.dumps(
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
        except (TypeError, ValueError) as e:
            logger.warning("Not tracking %s event: not JSON serialisable: %s", event, e)
            return
        with self._condition:
            if self._closed or self._refused:
                logger.debug(
                    "Not tracking %s event: event tracking has stopped.", event
                )
                return
            exposure_key = None
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
            self._buffer.append(_BufferedEvent(serialised_event, exposure_key))
            self._tracked_count += 1
            self._drop_oldest_events()
            if len(self._buffer) >= self._max_buffer:
                self._condition.notify_all()

    def flush(self) -> None:
        """
        Sends the buffered events, including any kept from a failed send, and
        returns once each of them has been delivered, dropped, or kept for the
        next send. If a send already running covers every event tracked so
        far, waits for it instead. Does nothing once closed.
        """
        with self._condition:
            if self._closed:
                return
            if (
                self._sending_count is not None
                and self._sending_count >= self._tracked_count
            ):
                send = self._sends_started
            else:
                self._flush_requested = True
                send = self._sends_started + 1
                self._condition.notify_all()
            self._condition.wait_for(
                lambda: self._sends_completed >= send or not self._worker.is_alive()
            )

    def close(
        self, timeout_seconds: float = DEFAULT_EVENTS_CLOSE_TIMEOUT_SECONDS
    ) -> None:
        """
        Stops event tracking, and sends the buffered events, waiting for at
        most `timeout_seconds`. No request starts once this returns. Calling
        it again does nothing.
        """
        if not self.stop():
            return
        self._worker.join(timeout_seconds)
        self._abandoned.set()
        if self._worker.is_alive():
            logger.warning(
                "Gave up sending events after %s seconds while closing",
                timeout_seconds,
            )

    def stop(self) -> bool:
        """
        Stops event tracking, and has the worker send the buffered events,
        without waiting for it. Returns whether this stopped event tracking.
        """
        with self._condition:
            if self._closed:
                return False
            self._closed = True
            self._condition.notify_all()
        atexit.unregister(self.close)
        return True

    def _run(self) -> None:
        next_send_at = time.monotonic() + self._flush_interval_seconds
        while True:
            with self._condition:
                while not (
                    self._closed
                    or self._flush_requested
                    or (
                        len(self._buffer) >= self._max_buffer
                        and self._tracked_count > self._sent_count
                    )
                    or time.monotonic() >= next_send_at
                ):
                    self._condition.wait(next_send_at - time.monotonic())
                closing = self._closed
                events = list(self._buffer)
                self._buffer.clear()
                self._buffered_exposure_keys.clear()
                self._flush_requested = False
                self._sends_started += 1
                sending_count = self._sending_count = self._tracked_count
            next_send_at = time.monotonic() + self._flush_interval_seconds

            try:
                outcome = (
                    self._deliver([event.payload for event in events])
                    if events
                    else _DeliveryOutcome.DELIVERED
                )
            except Exception:
                logger.exception("Dropping %d events: failed to send", len(events))
                outcome = _DeliveryOutcome.DROPPED

            with self._condition:
                self._sent_count = sending_count
                self._sending_count = None
                self._sends_completed += 1
                if outcome is _DeliveryOutcome.KEPT:
                    self._buffer.extendleft(reversed(events))
                    self._buffered_exposure_keys.update(
                        event.exposure_key for event in events if event.exposure_key
                    )
                    self._drop_oldest_events()
                elif outcome is _DeliveryOutcome.REFUSED:
                    self._refused = True
                    self._buffer.clear()
                    self._buffered_exposure_keys.clear()
                self._condition.notify_all()
            if closing:
                self._session.close()
                return

    def _drop_oldest_events(self) -> None:
        while len(self._buffer) > self._max_buffer:
            dropped = self._buffer.popleft()
            self._buffered_exposure_keys.discard(dropped.exposure_key)
            logger.warning("Event buffer is full, dropped the oldest event")

    def _deliver(self, events: typing.List[str]) -> _DeliveryOutcome:
        payload = f'{{"events": [{", ".join(events)}]}}'
        status: typing.Optional[int] = None
        for attempt in range(1, EVENTS_MAX_ATTEMPTS + 1):
            if attempt > 1:
                backoff = EVENTS_RETRY_BASE_SECONDS * 2 ** (attempt - 2)
                self._abandoned.wait(random.uniform(0, backoff))
            if self._abandoned.is_set():
                logger.warning(
                    "Not sending %d events: the client is closed", len(events)
                )
                return _DeliveryOutcome.DROPPED
            try:
                response = self._post(payload)
            except (requests.ConnectionError, requests.Timeout) as e:
                status = None
                failure = str(e)
            except requests.RequestException as e:
                logger.error("Dropping %d events: %s", len(events), e)
                return _DeliveryOutcome.DROPPED
            else:
                status = response.status_code
                if outcome := self._outcome_of(status, len(events)):
                    return outcome
                failure = f"status {status}"
            logger.warning(
                "Failed to send %d events, attempt %d of %d: %s",
                len(events),
                attempt,
                EVENTS_MAX_ATTEMPTS,
                failure,
            )
        if status == 500:
            logger.warning(
                "Dropping %d events the events API failed with 500", len(events)
            )
            return _DeliveryOutcome.DROPPED
        logger.warning("Keeping %d events for the next send", len(events))
        return _DeliveryOutcome.KEPT

    def _post(self, payload: str) -> requests.Response:
        return self._session.post(
            self._batch_endpoint,
            data=payload,
            timeout=EVENTS_REQUEST_TIMEOUT_SECONDS,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Environment-Key": self._environment_key,
                "Flagsmith-SDK-User-Agent": DEFAULT_USER_AGENT,
            },
        )

    @staticmethod
    def _outcome_of(status: int, event_count: int) -> typing.Optional[_DeliveryOutcome]:
        """The outcome of a request answered with `status`, or None to retry it."""
        if status < 400:
            return _DeliveryOutcome.DELIVERED
        if status in (401, 403):
            logger.error(
                "Events API refused the environment key with %d,"
                " stopping event tracking",
                status,
            )
            return _DeliveryOutcome.REFUSED
        if status in RETRIED_STATUS_CODES:
            return None
        logger.warning(
            "Events API rejected %d events with %d, dropping them",
            event_count,
            status,
        )
        return _DeliveryOutcome.DROPPED
