import json
import logging
import os
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


def test_flush__tracked_event__sent_to_events_api(
    mocker: MockerFixture,
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    post = mocker.spy(event_processor._session, "post")
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    before = int(datetime.now().timestamp() * 1000)
    event_processor.track_event(
        event="purchase",
        identifier="user1",
        value=99.5,
        traits={"plan": "premium"},
        metadata={"sku": "abc"},
    )
    after = int(datetime.now().timestamp() * 1000)

    # When
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 1
    assert post.call_args.kwargs["timeout"] == 3
    request = mocked_responses.calls[0].request
    assert request.headers["X-Environment-Key"] == "test_key"
    assert request.headers["Content-Type"] == "application/json; charset=utf-8"
    assert "flagsmith-python-sdk/" in request.headers["Flagsmith-SDK-User-Agent"]
    request_body = request.body
    assert request_body
    body = json.loads(request_body)
    assert "environment_key" not in body
    [event] = body["events"]
    assert event["event"] == "purchase"
    assert event["feature_name"] is None
    assert event["identifier"] == "user1"
    assert event["value"] == "99.5"
    assert event["traits"] == {"plan": "premium"}
    assert event["metadata"]["sku"] == "abc"
    assert "sdk_version" in event["metadata"]
    assert before <= event["timestamp"] <= after


def test_flush__event_values__sent_as_strings(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_event(event="purchase", value=99.5)
    event_processor.track_event(event="opt_in", value=True)
    event_processor.track_event(event="count", value=3)
    event_processor.track_event(event="variant", value="control")
    event_processor.track_event(event="empty")

    # When
    event_processor.flush()

    # Then
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    body = json.loads(request_body)
    assert [e["value"] for e in body["events"]] == [
        "99.5",
        "True",
        "3",
        "control",
        None,
    ]


def test_flush__exposure_event__sent_as_flag_exposure(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_exposure_event(
        feature_name="checkout_v2",
        identifier="user1",
        value="variant_b",
        traits={"plan": "premium"},
        metadata={"source": "homepage"},
    )

    # When
    event_processor.flush()

    # Then
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    [event] = json.loads(request_body)["events"]
    assert event["event"] == FLAG_EXPOSURE_EVENT == "$flag_exposure"
    assert event["feature_name"] == "checkout_v2"
    assert event["identifier"] == "user1"
    assert event["value"] == "variant_b"
    assert event["traits"] == {"plan": "premium"}
    assert event["metadata"]["source"] == "homepage"
    assert "sdk_version" in event["metadata"]


def test_flush__equal_exposures_in_flush_interval__sent_once(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    for _ in range(3):
        event_processor.track_exposure_event(
            feature_name="checkout_v2", identifier="user1", value="variant_b"
        )

    # When
    event_processor.flush()

    # Then
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    assert len(json.loads(request_body)["events"]) == 1


def test_flush__differing_exposures__each_sent(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
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

    # When
    event_processor.flush()

    # Then
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    assert len(json.loads(request_body)["events"]) == 4


def test_flush__equal_exposure_after_flush__sent_again(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_exposure_event(
        feature_name="checkout_v2", identifier="user1", value="variant_b"
    )
    event_processor.flush()
    event_processor.track_exposure_event(
        feature_name="checkout_v2", identifier="user1", value="variant_b"
    )

    # When
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 2


def test_flush__equal_custom_events__each_sent(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_event(event="purchase", identifier="user1", value="99.5")
    event_processor.track_event(event="purchase", identifier="user1", value="99.5")

    # When
    event_processor.flush()

    # Then
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    assert len(json.loads(request_body)["events"]) == 2


def test_track_event__metadata_not_json_serialisable__event_not_tracked(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)

    # When
    event_processor.track_event(event="purchase", metadata={"at": datetime.now()})
    event_processor.track_event(event="checkout")
    event_processor.flush()

    # Then
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    assert [e["event"] for e in json.loads(request_body)["events"]] == ["checkout"]
    assert caplog.messages == [
        "Not tracking purchase event: not JSON serialisable:"
        " Object of type datetime is not JSON serializable"
    ]


def test_track_event__full_buffer__sent_without_flush(
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

    # When
    for i in range(5):
        processor.track_event(event=f"event_{i}")
    deadline = time.monotonic() + 5
    while not mocked_responses.calls and time.monotonic() < deadline:
        time.sleep(0.01)
    processor.flush()
    processor.close(timeout_seconds=0)
    processor._worker.join(5)

    # Then
    assert len(mocked_responses.calls) == 1
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    body = json.loads(request_body)
    assert [e["event"] for e in body["events"]] == [f"event_{i}" for i in range(5)]


def test_track_event__buffer_full_of_kept_events__waits_for_flush_interval(
    mocker: MockerFixture,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocker.patch("flagsmith.analytics.random.uniform", return_value=0)
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/", max_buffer_items=2
        ),
        environment_key="test_key",
    )
    mocked_responses.post("http://test_analytics/v1/events", status=503)
    processor.track_event(event="event_1")
    processor.track_event(event="event_2")
    processor.flush()

    # When
    processor.track_event(event="event_3")
    time.sleep(0.3)

    # Then
    assert len(mocked_responses.calls) == 3
    processor.close(timeout_seconds=0)
    processor._worker.join(5)


@pytest.mark.parametrize("max_buffer_items", [0, -1])
def test_track_event__max_buffer_items_below_one__event_sent_without_flush(
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
    max_buffer_items: int,
) -> None:
    # Given
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/",
            max_buffer_items=max_buffer_items,
        ),
        environment_key="test_key",
    )
    mocked_responses.post("http://test_analytics/v1/events", status=202)

    # When
    processor.track_event(event="purchase")
    deadline = time.monotonic() + 5
    while not mocked_responses.calls and time.monotonic() < deadline:
        time.sleep(0.01)
    processor.close(timeout_seconds=0)
    processor._worker.join(5)

    # Then
    assert len(mocked_responses.calls) == 1
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    assert [e["event"] for e in json.loads(request_body)["events"]] == ["purchase"]
    assert caplog.messages[0] == (
        f"max_buffer_items must be at least 1, not {max_buffer_items}: using 1"
    )


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
    processor.close(timeout_seconds=0)
    processor._worker.join(5)

    # Then
    assert len(mocked_responses.calls) == 4
    request_body = mocked_responses.calls[3].request.body
    assert request_body
    body = json.loads(request_body)
    assert [e["event"] for e in body["events"]] == ["event_2", "event_3", "event_4"]
    assert "Event buffer was full: dropped the 1 oldest events" in caplog.messages


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
    assert caplog.messages == [
        "Failed to send 1 events, attempt 1 of 3: status 503",
        "Failed to send 1 events, attempt 2 of 3: reset",
    ]


@pytest.mark.parametrize(
    "failures",
    [
        pytest.param([503, 503, 503], id="unavailable"),
        pytest.param([500, 500, 503], id="unavailable-after-server-errors"),
        pytest.param([429, 408, 504], id="throttled-and-timed-out"),
        pytest.param(
            [502, requests.ConnectionError("reset"), requests.Timeout("timed out")],
            id="unreachable",
        ),
    ],
)
def test_flush__last_attempt_fails_transiently__kept_ahead_of_newer_events(
    mocker: MockerFixture,
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
    failures: typing.List[typing.Union[int, Exception]],
) -> None:
    # Given
    mocker.patch("flagsmith.analytics.random.uniform", return_value=0)
    for failure in failures:
        if isinstance(failure, Exception):
            mocked_responses.post("http://test_analytics/v1/events", body=failure)
        else:
            mocked_responses.post("http://test_analytics/v1/events", status=failure)
    mocked_responses.post("http://test_analytics/v1/events", status=202)
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
    assert "Keeping 1 events for the next send" in caplog.messages


def test_flush__kept_batch_and_no_new_events__kept_batch_sent(
    mocker: MockerFixture,
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocker.patch("flagsmith.analytics.random.uniform", return_value=0)
    for status in (503, 503, 503, 202):
        mocked_responses.post("http://test_analytics/v1/events", status=status)
    event_processor.track_event(event="add_to_cart")
    event_processor.flush()

    # When
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 4
    request_body = mocked_responses.calls[3].request.body
    assert request_body
    assert [e["event"] for e in json.loads(request_body)["events"]] == ["add_to_cart"]


def test_flush__send_in_flight_covers_tracked_events__waits_without_resending(
    mocker: MockerFixture,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocker.patch("flagsmith.analytics.random.uniform", return_value=0)
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/", max_buffer_items=2
        ),
        environment_key="test_key",
    )
    requested = threading.Event()
    answer = threading.Event()

    def answer_when_released(
        request: requests.PreparedRequest,
    ) -> typing.Tuple[int, typing.Dict[str, str], str]:
        requested.set()
        answer.wait(5)
        return 503, {}, ""

    mocked_responses.add_callback(
        responses.POST,
        "http://test_analytics/v1/events",
        callback=answer_when_released,
    )
    processor.track_event(event="event_1")
    processor.track_event(event="event_2")
    requested.wait(5)
    threading.Timer(0.1, answer.set).start()

    # When
    processor.flush()

    # Then
    assert len(mocked_responses.calls) == 3
    processor.close(timeout_seconds=0)
    processor._worker.join(5)


def test_track_exposure_event__equal_exposure_dropped_from_full_buffer__sent(
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/", max_buffer_items=2
        ),
        environment_key="test_key",
    )
    requested = threading.Event()
    answer = threading.Event()

    def answer_when_released(
        request: requests.PreparedRequest,
    ) -> typing.Tuple[int, typing.Dict[str, str], str]:
        requested.set()
        answer.wait(5)
        return 202, {}, ""

    mocked_responses.add_callback(
        responses.POST,
        "http://test_analytics/v1/events",
        callback=answer_when_released,
    )
    processor.track_event(event="event_1")
    processor.track_event(event="event_2")
    requested.wait(5)
    processor.track_exposure_event(
        feature_name="checkout", identifier="user1", value="variant_b"
    )
    processor.track_event(event="event_3")
    processor.track_event(event="event_4")

    # When
    processor.track_exposure_event(
        feature_name="checkout", identifier="user1", value="variant_b"
    )
    answer.set()
    processor.flush()
    processor.close(timeout_seconds=0)
    processor._worker.join(5)

    # Then
    sent_events = []
    for call in mocked_responses.calls:
        request_body = call.request.body
        assert request_body
        sent_events += [e["event"] for e in json.loads(request_body)["events"]]
    assert sent_events == ["event_1", "event_2", "event_4", FLAG_EXPOSURE_EVENT]


@pytest.mark.parametrize(
    "statuses, expected_log",
    [
        pytest.param(
            [400],
            "Events API rejected 1 events with 400, dropping them",
            id="rejected",
        ),
        pytest.param(
            [501],
            "Events API rejected 1 events with 501, dropping them",
            id="not-implemented",
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


def test_flush__request_cannot_be_made__dropped_without_retrying(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    mocked_responses.post(
        "http://test_analytics/v1/events",
        body=requests.exceptions.InvalidHeader("invalid header"),
    )
    event_processor.track_event(event="purchase")

    # When
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 1
    assert caplog.messages == ["Dropping 1 events: invalid header"]


def test_flush__unexpected_error__returns_and_keeps_tracking(
    mocker: MockerFixture,
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    mocker.patch.object(
        event_processor._session,
        "post",
        side_effect=[RuntimeError("unexpected"), mocker.DEFAULT],
        wraps=event_processor._session.post,
    )
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_event(event="purchase")
    event_processor.flush()

    # When
    event_processor.track_event(event="checkout")
    event_processor.flush()

    # Then
    assert len(mocked_responses.calls) == 1
    assert caplog.messages == ["Dropping 1 events: failed to send"]


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
    assert caplog.messages == [
        f"Events API refused the environment key with {status},"
        " stopping event tracking",
        "Not tracking checkout event: event tracking has stopped.",
    ]


def test_events__flush_interval_elapsed__sent_without_flush(
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

    # When
    processor.track_event(event="purchase")
    deadline = time.monotonic() + 5
    while not mocked_responses.calls and time.monotonic() < deadline:
        time.sleep(0.01)
    processor.close(timeout_seconds=0)
    processor._worker.join(5)

    # Then
    assert len(mocked_responses.calls) == 1


def test_close__sends_buffered_events_and_stops_event_tracking(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_event(event="purchase")

    # When
    event_processor.close()
    with caplog.at_level(logging.DEBUG, logger="flagsmith.analytics"):
        event_processor.track_event(event="checkout")
    event_processor.flush()
    event_processor.close()

    # Then
    assert len(mocked_responses.calls) == 1
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    assert [e["event"] for e in json.loads(request_body)["events"]] == ["purchase"]
    assert not event_processor._worker.is_alive()
    assert caplog.messages == [
        "Not tracking checkout event: event tracking has stopped."
    ]


def test_close__events_api_not_answering__returns_within_timeout(
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
    event_processor.close(timeout_seconds=0.1)
    elapsed = time.monotonic() - started
    answer.set()
    event_processor._worker.join(5)

    # Then
    assert elapsed < 1
    assert len(mocked_responses.calls) == 1
    assert caplog.messages == [
        "Gave up sending events after 0.1 seconds while closing",
        "Failed to send 1 events, attempt 1 of 3: status 503",
        "Not sending 1 events: the client is closed",
    ]


def test_stop__events_api_not_answering__returns_without_waiting(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    answer = threading.Event()
    mocked_responses.add_callback(
        responses.POST,
        "http://test_analytics/v1/events",
        callback=lambda request: (answer.wait(5), (202, {}, ""))[1],
    )
    event_processor.track_event(event="purchase")

    # When
    started = time.monotonic()
    event_processor.stop()
    elapsed = time.monotonic() - started
    answer.set()
    event_processor._worker.join(5)

    # Then
    assert elapsed < 1
    assert len(mocked_responses.calls) == 1
    assert not event_processor._worker.is_alive()


def test_close__after_stop__waits_for_buffered_events(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    answer = threading.Event()
    mocked_responses.add_callback(
        responses.POST,
        "http://test_analytics/v1/events",
        callback=lambda request: (answer.wait(5), (202, {}, ""))[1],
    )
    event_processor.track_event(event="purchase")
    event_processor.stop()
    threading.Timer(0.2, answer.set).start()

    # When
    event_processor.close(timeout_seconds=5)

    # Then
    assert len(mocked_responses.calls) == 1
    assert not event_processor._worker.is_alive()


def test_track_event__full_buffer_while_sending__drops_logged_once(
    mocked_responses: responses.RequestsMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    processor = EventProcessor(
        config=EventProcessorConfig(
            events_api_url="http://test_analytics/", max_buffer_items=2
        ),
        environment_key="test_key",
    )
    requested = threading.Event()
    answer = threading.Event()

    def answer_when_released(
        request: requests.PreparedRequest,
    ) -> typing.Tuple[int, typing.Dict[str, str], str]:
        requested.set()
        answer.wait(5)
        return 202, {}, ""

    mocked_responses.add_callback(
        responses.POST,
        "http://test_analytics/v1/events",
        callback=answer_when_released,
    )
    processor.track_event(event="event_1")
    processor.track_event(event="event_2")
    requested.wait(5)

    # When
    for i in range(3, 8):
        processor.track_event(event=f"event_{i}")
    answer.set()
    processor.flush()
    processor.close(timeout_seconds=0)
    processor._worker.join(5)

    # Then
    assert [m for m in caplog.messages if m.startswith("Event buffer")] == [
        "Event buffer was full: dropped the 3 oldest events"
    ]


@pytest.mark.skipif(not hasattr(os, "fork"), reason="needs os.fork")
@pytest.mark.filterwarnings(
    "ignore:This process .* is multi-threaded:DeprecationWarning"
)
def test_track_event__forked_child__each_process_sends_its_own_events(
    event_processor: EventProcessor,
    mocked_responses: responses.RequestsMock,
) -> None:
    # Given
    mocked_responses.post("http://test_analytics/v1/events", status=202)
    event_processor.track_event(event="tracked_before_fork")

    # When
    pid = os.fork()
    if pid == 0:
        exit_code = 1
        try:
            event_processor.track_event(event="tracked_in_child")
            event_processor.flush()
            child_sent_events = []
            for call in mocked_responses.calls:
                request_body = call.request.body
                assert request_body
                child_sent_events += [
                    e["event"] for e in json.loads(request_body)["events"]
                ]
            exit_code = 0 if child_sent_events == ["tracked_in_child"] else 2
        finally:
            os._exit(exit_code)
    _, wait_status = os.waitpid(pid, 0)
    event_processor.flush()

    # Then
    assert os.waitstatus_to_exitcode(wait_status) == 0
    assert len(mocked_responses.calls) == 1
    request_body = mocked_responses.calls[0].request.body
    assert request_body
    assert [e["event"] for e in json.loads(request_body)["events"]] == [
        "tracked_before_fork"
    ]
