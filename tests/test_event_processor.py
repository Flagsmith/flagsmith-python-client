import json
import logging
import threading
import time
import typing
from datetime import datetime

import pytest
import requests
import responses
from pytest_mock import MockerFixture

from flagsmith.analytics import (
    FLAG_EXPOSURE_EVENT,
    EventProcessor,
    EventProcessorConfig,
)


def test_track_event_buffers_event(event_processor: EventProcessor) -> None:
    event_processor.track_event(
        event="purchase",
        identifier="user1",
        value=99.5,
        traits={"plan": "premium"},
        metadata={"sku": "abc"},
    )
    event_processor.track_event(event="purchase", identifier="user1")

    assert len(event_processor._buffer) == 2
    event = event_processor._buffer[0]
    assert event["event"] == "purchase"
    assert event["feature_name"] is None
    assert event["identifier"] == "user1"
    assert event["value"] == "99.5"
    assert event["traits"] == {"plan": "premium"}
    assert event["metadata"]["sku"] == "abc"
    assert "sdk_version" in event["metadata"]
    assert isinstance(event["timestamp"], int)


def test_buffer_stringifies_non_string_values(
    event_processor: EventProcessor,
) -> None:
    event_processor.track_event(event="purchase", value=99.5)
    event_processor.track_event(event="opt_in", value=True)
    event_processor.track_event(event="count", value=3)
    event_processor.track_event(event="variant", value="control")
    event_processor.track_event(event="empty")

    assert [e["value"] for e in event_processor._buffer] == [
        "99.5",
        "True",
        "3",
        "control",
        None,
    ]


def test_track_event_defaults_timestamp_to_now(
    event_processor: EventProcessor,
) -> None:
    before = int(datetime.now().timestamp() * 1000)
    event_processor.track_event(event="ping")
    after = int(datetime.now().timestamp() * 1000)

    assert before <= event_processor._buffer[0]["timestamp"] <= after


def test_track_exposure_event_buffers_with_flag_exposure_event_name(
    event_processor: EventProcessor,
) -> None:
    event_processor.track_exposure_event(
        feature_name="checkout_v2",
        identifier="user1",
        value="variant_b",
        traits={"plan": "premium"},
        metadata={"source": "homepage"},
    )

    assert len(event_processor._buffer) == 1
    event = event_processor._buffer[0]
    assert event["event"] == FLAG_EXPOSURE_EVENT == "$flag_exposure"
    assert event["feature_name"] == "checkout_v2"
    assert event["identifier"] == "user1"
    assert event["value"] == "variant_b"
    assert event["traits"] == {"plan": "premium"}
    assert event["metadata"]["source"] == "homepage"
    assert "sdk_version" in event["metadata"]


def test_track_exposure_event__equal_events_in_flush_interval__deduplicated(
    event_processor: EventProcessor,
) -> None:
    # Given / When
    for _ in range(3):
        event_processor.track_exposure_event(
            feature_name="checkout_v2",
            identifier="user1",
            value="variant_b",
        )

    # Then
    assert len(event_processor._buffer) == 1


def test_track_exposure_event__differing_events__not_deduplicated(
    event_processor: EventProcessor,
) -> None:
    # Given / When
    event_processor.track_exposure_event(
        feature_name="checkout_v2", identifier="user1", value="variant_b"
    )
    event_processor.track_exposure_event(
        feature_name="checkout_v2", identifier="user2", value="variant_b"
    )
    event_processor.track_exposure_event(
        feature_name="checkout_v2", identifier="user1", value="variant_a"
    )
    event_processor.track_exposure_event(
        feature_name="banner_test", identifier="user1", value="variant_b"
    )

    # Then
    assert len(event_processor._buffer) == 4


def test_track_exposure_event__equal_event_after_flush__buffered_again(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_exposure_event(
        feature_name="checkout_v2", identifier="user1", value="variant_b"
    )
    event_processor.flush()

    # When
    event_processor.track_exposure_event(
        feature_name="checkout_v2", identifier="user1", value="variant_b"
    )

    # Then
    assert len(event_processor._buffer) == 1


def test_track_event__equal_events__not_deduplicated(
    event_processor: EventProcessor,
) -> None:
    # Given / When
    event_processor.track_event(event="purchase", identifier="user1", value="99.5")
    event_processor.track_event(event="purchase", identifier="user1", value="99.5")

    # Then
    assert len(event_processor._buffer) == 2


def test_flush__full_buffer__sends_events_once(
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/", max_buffer_items=5
        ),
        environment_key="test_key",
    )
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    for i in range(5):
        processor.track_event(event=f"event_{i}")

    # When
    processor.flush()

    # Then
    assert len(mocked_responses.calls) == 1
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    body = json.loads(request_body)
    assert [e["event"] for e in body["events"]] == [f"event_{i}" for i in range(5)]
    assert processor._buffer == []


def test_flush__full_buffer__drops_oldest_event(
    mocker: MockerFixture,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    mocker.patch("flagsmith.analytics.random.uniform", return_value=0)
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/", max_buffer_items=3
        ),
        environment_key="test_key",
    )
    for status in (503, 503, 503, 202):
        mocked_responses.post("http://test_analytics/v1/events", status=status)
    for i in range(1, 4):
        processor.track_event(event=f"event_{i}")
    processor.flush()

    # When
    processor.track_event(event="event_4")
    processor.flush()

    # Then
    assert len(mocked_responses.calls) == 4
    request_body = mocked_responses.calls[3].request.body
    assert request_body
    body = json.loads(request_body)
    assert [e["event"] for e in body["events"]] == ["event_2", "event_3", "event_4"]
    assert "Event buffer is full, dropping the oldest event_1 event" in (
        caplog.messages
    )


def test_flush__sends_events_to_events_api(
    mocker: MockerFixture,
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    post = mocker.spy(event_processor._session, "post")
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_event(event="purchase", identifier="user1")

    # When
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 1
    request = mocked_responses.calls[0].request
    assert post.call_args.kwargs["timeout"] == 3
    assert request.headers["X-Environment-Key"] == "test_key"
    assert request.headers["Content-Type"] == "application/json; charset=utf-8"
    assert "flagsmith-python-sdk/" in request.headers["Flagsmith-SDK-User-Agent"]
    request_body = request.body
    assert request_body
    body = json.loads(request_body)
    assert "environment_key" not in body
    assert len(body["events"]) == 1
    assert body["events"][0]["event"] == "purchase"
    assert event_processor._buffer == []


def test_flush__no_events__sends_nothing(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # When
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 0


def test_flush__transient_failures__retried_with_backoff(
    mocker: MockerFixture,
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    uniform = mocker.patch("flagsmith.analytics.random.uniform", return_value=0)
    mocked_responses.post("http://test_analytics/v1/events", status=503)
    mocked_responses.post(
        "http://test_analytics/v1/events", body=requests.ConnectionError("reset")
    )
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_event(event="purchase")

    # When
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 3
    assert uniform.call_args_list == [mocker.call(0, 1), mocker.call(0, 2)]
    assert event_processor._buffer == []
    assert caplog.messages == [
        "Failed to send 1 events, attempt 1 of 3: status 503",
        "Failed to send 1 events, attempt 2 of 3: reset",
    ]


@pytest.mark.parametrize(
    "statuses",
    [
        pytest.param([503, 503, 503], id="unavailable"),
        pytest.param([500, 500, 503], id="unavailable-after-server-errors"),
        pytest.param([429, 429, 429], id="throttled"),
    ],
)
def test_flush__last_attempt_fails_transiently__kept_ahead_of_newer_events(
    mocker: MockerFixture,
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
    statuses: typing.List[int],
) -> None:
    # Given
    mocker.patch("flagsmith.analytics.random.uniform", return_value=0)
    for status in (*statuses, 202):
        mocked_responses.post("http://test_analytics/v1/events", status=status)
    event_processor.track_event(event="add_to_cart")
    event_processor.flush()

    # When
    event_processor.track_event(event="checkout")
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 4
    request_body = mocked_responses.calls[3].request.body
    assert request_body
    body = json.loads(request_body)
    assert [e["event"] for e in body["events"]] == ["add_to_cart", "checkout"]
    assert "Keeping 1 events for the next flush" in caplog.messages


@pytest.mark.parametrize(
    "statuses, expected_log",
    [
        pytest.param(
            [400],
            "Events API rejected 1 events with 400, dropping them",
            id="rejected",
        ),
        pytest.param(
            [503, 503, 500],
            "Dropping 1 events the events API failed with 500",
            id="server-error-last",
        ),
    ],
)
def test_flush__batch_rejected_or_last_failed_with_server_error__dropped(
    mocker: MockerFixture,
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
    statuses: typing.List[int],
    expected_log: str,
) -> None:
    # Given
    mocker.patch("flagsmith.analytics.random.uniform", return_value=0)
    for status in (*statuses, 202):
        mocked_responses.post("http://test_analytics/v1/events", status=status)
    event_processor.track_event(event="add_to_cart")
    event_processor.flush()

    # When
    event_processor.track_event(event="checkout")
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == len(statuses) + 1
    request_body = mocked_responses.calls[-1].request.body
    assert request_body
    body = json.loads(request_body)
    assert [e["event"] for e in body["events"]] == ["checkout"]
    assert expected_log in caplog.messages


@pytest.mark.parametrize("status", [401, 403])
def test_flush__environment_key_refused__stops_event_tracking(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
    status: int,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=status)
    event_processor.track_event(event="add_to_cart")
    event_processor.flush()

    # When
    with caplog.at_level(logging.DEBUG, logger="flagsmith.analytics"):
        event_processor.track_event(event="checkout")
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 1
    assert event_processor._buffer == []
    assert caplog.messages == [
        f"Events API refused the environment key with {status},"
        " stopping event tracking",
        "Not tracking checkout event: the events API refused the environment key.",
    ]


def test_start__flushes_on_timer(
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/", flush_interval_seconds=0.01
        ),
        environment_key="test_key",
    )
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    processor.track_event(event="purchase")

    # When
    processor.start()
    deadline = time.monotonic() + 5
    while not mocked_responses.calls and time.monotonic() < deadline:
        time.sleep(0.01)
    processor.stop()

    # Then
    assert len(mocked_responses.calls) == 1
    assert processor._buffer == []


def test_stop__sends_buffered_events(
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/", flush_interval_seconds=100
        ),
        environment_key="test_key",
    )
    processor.start()
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    processor.track_event(event="purchase")

    # When
    processor.stop()

    # Then
    assert processor._timer is not None
    assert not processor._timer.is_alive()
    assert len(mocked_responses.calls) == 1
    assert processor._buffer == []


def test_stop__events_api_not_answering__returns_within_timeout(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    answer = threading.Event()
    mocked_responses.add_callback(
        responses.POST,
        "http://test_analytics/v1/events",
        callback=lambda request: (answer.wait(5), (503, {}, ""))[1],
    )
    event_processor.track_event(event="purchase")

    # When
    started = time.monotonic()
    event_processor.stop(timeout_seconds=0.1)
    elapsed = time.monotonic() - started
    answer.set()
    with event_processor._send_lock:
        pass

    # Then
    assert elapsed < 1
    assert len(mocked_responses.calls) == 1
    assert caplog.messages == [
        "Gave up sending events after 0.1 seconds while closing",
        "Failed to send 1 events, attempt 1 of 3: status 503",
        "Not retrying 1 events: the client is closed",
    ]
