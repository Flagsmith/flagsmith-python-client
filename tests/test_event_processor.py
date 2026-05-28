import json
from concurrent.futures import Future
from unittest import mock

from flagsmith.analytics import (
    EventProcessor,
    EventProcessorConfig,
)


def test_track_event_buffers_event(event_processor: EventProcessor) -> None:
    event_processor.track_event(
        event_name="purchase",
        identity_identifier="user1",
        traits={"plan": "premium"},
        metadata={"amount": 99},
    )
    # Events are never deduplicated
    event_processor.track_event(
        event_name="purchase",
        identity_identifier="user1",
    )

    assert len(event_processor._buffer) == 2
    event = event_processor._buffer[0]
    assert event["event_id"] == "purchase"
    assert event["event_type"] == "custom_event"
    assert event["identity_identifier"] == "user1"
    assert event["enabled"] is None
    assert event["value"] is None
    assert event["traits"] == {"plan": "premium"}
    assert event["metadata"]["amount"] == 99
    assert "sdk_version" in event["metadata"]
    assert isinstance(event["evaluated_at"], int)


def test_auto_flush_on_buffer_full() -> None:
    config = EventProcessorConfig(
        analytics_server_url="http://test/", max_buffer_items=5
    )
    processor = EventProcessor(config=config, environment_key="key")

    with mock.patch("flagsmith.analytics.session"):
        for i in range(5):
            processor.track_event(event_name=f"event_{i}")

    assert len(processor._buffer) == 0


def test_flush_sends_correct_http_request(event_processor: EventProcessor) -> None:
    with mock.patch("flagsmith.analytics.session") as mock_session:
        event_processor.track_event(event_name="purchase", identity_identifier="user1")
        event_processor.flush()

    mock_session.post.assert_called_once()
    call_kwargs = mock_session.post.call_args
    assert call_kwargs[0][0] == "http://test_analytics/v1/analytics/batch"

    headers = call_kwargs[1]["headers"]
    assert headers["X-Environment-Key"] == "test_key"
    assert headers["Content-Type"] == "application/json; charset=utf-8"
    assert "flagsmith-python-client/" in headers["Flagsmith-SDK-User-Agent"]

    body = json.loads(call_kwargs[1]["data"])
    assert body["environment_key"] == "test_key"
    assert len(body["events"]) == 1
    assert body["events"][0]["event_id"] == "purchase"


def test_flush_noop_when_empty(event_processor: EventProcessor) -> None:
    with mock.patch("flagsmith.analytics.session") as mock_session:
        event_processor.flush()

    mock_session.post.assert_not_called()


def test_failed_flush_requeues_events(event_processor: EventProcessor) -> None:
    future: Future[None] = Future()
    future.set_exception(Exception("connection error"))

    with mock.patch("flagsmith.analytics.session") as mock_session:
        mock_session.post.return_value = future
        event_processor.track_event(event_name="purchase")
        event_processor.flush()

    assert len(event_processor._buffer) == 1
    assert event_processor._buffer[0]["event_id"] == "purchase"


def test_start_stop_lifecycle() -> None:
    config = EventProcessorConfig(
        analytics_server_url="http://test/", flush_interval_seconds=100
    )
    processor = EventProcessor(config=config, environment_key="key")

    processor.start()
    assert processor._timer is not None
    assert processor._timer.is_alive()

    with mock.patch("flagsmith.analytics.session"):
        processor.track_event(event_name="purchase")
        processor.stop()

    assert len(processor._buffer) == 0
