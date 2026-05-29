import json
from concurrent.futures import Future
from datetime import datetime, timezone
from unittest import mock

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
    assert event["value"] == 99.5
    assert event["traits"] == {"plan": "premium"}
    assert event["metadata"]["sku"] == "abc"
    assert "sdk_version" in event["metadata"]
    assert isinstance(event["timestamp"], int)


def test_track_event_defaults_timestamp_to_now(
    event_processor: EventProcessor,
) -> None:
    before = int(datetime.now().timestamp() * 1000)
    event_processor.track_event(event="ping")
    after = int(datetime.now().timestamp() * 1000)

    assert before <= event_processor._buffer[0]["timestamp"] <= after


def test_track_event_uses_explicit_timestamp(
    event_processor: EventProcessor,
) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    event_processor.track_event(event="ping", timestamp=ts)

    assert event_processor._buffer[0]["timestamp"] == int(ts.timestamp() * 1000)


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


def test_track_exposure_event_uses_explicit_timestamp(
    event_processor: EventProcessor,
) -> None:
    ts = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    event_processor.track_exposure_event(feature_name="checkout_v2", timestamp=ts)

    assert event_processor._buffer[0]["timestamp"] == int(ts.timestamp() * 1000)


def test_auto_flush_on_buffer_full() -> None:
    config = EventProcessorConfig(events_api_url="http://test/", max_buffer_items=5)
    processor = EventProcessor(config=config, environment_key="key")

    with mock.patch("flagsmith.analytics.session"):
        for i in range(5):
            processor.track_event(event=f"event_{i}")

    assert len(processor._buffer) == 0


def test_flush_sends_correct_http_request(event_processor: EventProcessor) -> None:
    with mock.patch("flagsmith.analytics.session") as mock_session:
        event_processor.track_event(event="purchase", identifier="user1")
        event_processor.flush()

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert call_kwargs[0][0] == "http://test_analytics/v1/events"

    headers = call_kwargs[1]["headers"]
    assert headers["X-Environment-Key"] == "test_key"
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert "flagsmith-python-client/" in headers["Flagsmith-SDK-User-Agent"]

    body = json.loads(call_kwargs[1]["data"])
    assert "environment_key" not in body
    assert len(body["events"]) == 1
    assert body["events"][0]["event"] == "purchase"


def test_flush_noop_when_empty(event_processor: EventProcessor) -> None:
    with mock.patch("flagsmith.analytics.session") as mock_session:
        event_processor.flush()

    mock_session.post.assert_not_called()


def test_failed_flush_requeues_events(event_processor: EventProcessor) -> None:
    future: Future[None] = Future()
    future.set_exception(Exception("connection error"))

    with mock.patch("flagsmith.analytics.session") as mock_session:
        mock_session.post.return_value = future
        event_processor.track_event(event="purchase")
        event_processor.flush()

    assert len(event_processor._buffer) == 1
    assert event_processor._buffer[0]["event"] == "purchase"


def test_start_stop_lifecycle() -> None:
    config = EventProcessorConfig(
        events_api_url="http://test/", flush_interval_seconds=100
    )
    processor = EventProcessor(config=config, environment_key="key")

    processor.start()
    assert processor._timer is not None
    assert processor._timer.is_alive()

    with mock.patch("flagsmith.analytics.session"):
        processor.track_event(event="purchase")
        processor.stop()

    assert len(processor._buffer) == 0
