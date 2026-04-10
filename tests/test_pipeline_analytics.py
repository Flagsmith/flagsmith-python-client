import json
from concurrent.futures import Future
from unittest import mock

import pytest

from flagsmith.analytics import (
    PipelineAnalyticsConfig,
    PipelineAnalyticsProcessor,
)


def test_record_evaluation_event_buffers_event(
    pipeline_analytics_processor: PipelineAnalyticsProcessor,
) -> None:
    pipeline_analytics_processor.record_evaluation_event(
        flag_key="my_flag",
        enabled=True,
        value="variant_a",
        identity_identifier="user123",
        traits={"plan": "premium"},
    )

    assert len(pipeline_analytics_processor._buffer) == 1
    event = pipeline_analytics_processor._buffer[0]
    assert event["event_id"] == "my_flag"
    assert event["event_type"] == "flag_evaluation"
    assert event["identity_identifier"] == "user123"
    assert event["enabled"] is True
    assert event["value"] == "variant_a"
    assert event["traits"] == {"plan": "premium"}
    assert "sdk_version" in event["metadata"]
    assert isinstance(event["evaluated_at"], int)


@pytest.mark.parametrize(
    "second_enabled, expected_count",
    [
        (True, 1),   # same fingerprint -> deduplicated
        (False, 2),  # different fingerprint -> both kept
    ],
)
def test_evaluation_event_deduplication(
    pipeline_analytics_processor: PipelineAnalyticsProcessor,
    second_enabled: bool,
    expected_count: int,
) -> None:
    pipeline_analytics_processor.record_evaluation_event(
        flag_key="my_flag", enabled=True, value="v1", identity_identifier="user1"
    )
    pipeline_analytics_processor.record_evaluation_event(
        flag_key="my_flag", enabled=second_enabled, value="v1", identity_identifier="user1"
    )

    assert len(pipeline_analytics_processor._buffer) == expected_count


def test_dedup_keys_cleared_after_flush(
    pipeline_analytics_processor: PipelineAnalyticsProcessor,
) -> None:
    with mock.patch("flagsmith.analytics.session"):
        pipeline_analytics_processor.record_evaluation_event(
            flag_key="my_flag", enabled=True, value="v1", identity_identifier="user1"
        )
        pipeline_analytics_processor.flush()

        pipeline_analytics_processor.record_evaluation_event(
            flag_key="my_flag", enabled=True, value="v1", identity_identifier="user1"
        )

    assert len(pipeline_analytics_processor._buffer) == 1


def test_auto_flush_on_buffer_full() -> None:
    config = PipelineAnalyticsConfig(
        analytics_server_url="http://test/", max_buffer=5
    )
    processor = PipelineAnalyticsProcessor(config=config, environment_key="key")

    with mock.patch("flagsmith.analytics.session"):
        for i in range(5):
            processor.record_evaluation_event(
                flag_key=f"flag_{i}", enabled=True, value=str(i)
            )

    assert len(processor._buffer) == 0


def test_flush_sends_correct_http_request(
    pipeline_analytics_processor: PipelineAnalyticsProcessor,
) -> None:
    with mock.patch("flagsmith.analytics.session") as mock_session:
        pipeline_analytics_processor.record_evaluation_event(
            flag_key="my_flag", enabled=True, value="v1", identity_identifier="user1"
        )
        pipeline_analytics_processor.flush()

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
    assert body["events"][0]["event_id"] == "my_flag"


def test_flush_noop_when_empty(
    pipeline_analytics_processor: PipelineAnalyticsProcessor,
) -> None:
    with mock.patch("flagsmith.analytics.session") as mock_session:
        pipeline_analytics_processor.flush()

    mock_session.post.assert_not_called()


def test_failed_flush_requeues_events(
    pipeline_analytics_processor: PipelineAnalyticsProcessor,
) -> None:
    future: Future[None] = Future()
    future.set_exception(Exception("connection error"))

    with mock.patch("flagsmith.analytics.session") as mock_session:
        mock_session.post.return_value = future
        pipeline_analytics_processor.record_evaluation_event(
            flag_key="my_flag", enabled=True, value="v1"
        )
        pipeline_analytics_processor.flush()

    assert len(pipeline_analytics_processor._buffer) == 1
    assert pipeline_analytics_processor._buffer[0]["event_id"] == "my_flag"


@pytest.mark.parametrize(
    "url, expected_endpoint",
    [
        ("http://example.com", "http://example.com/v1/analytics/batch"),
        ("http://example.com/", "http://example.com/v1/analytics/batch"),
    ],
)
def test_url_trailing_slash_handling(url: str, expected_endpoint: str) -> None:
    config = PipelineAnalyticsConfig(analytics_server_url=url)
    processor = PipelineAnalyticsProcessor(config=config, environment_key="key")
    assert processor._batch_endpoint == expected_endpoint


def test_record_custom_event(
    pipeline_analytics_processor: PipelineAnalyticsProcessor,
) -> None:
    pipeline_analytics_processor.record_custom_event(
        event_name="purchase",
        identity_identifier="user1",
        traits={"plan": "premium"},
        metadata={"amount": 99},
    )
    # Custom events are never deduplicated
    pipeline_analytics_processor.record_custom_event(
        event_name="purchase",
        identity_identifier="user1",
    )

    assert len(pipeline_analytics_processor._buffer) == 2
    event = pipeline_analytics_processor._buffer[0]
    assert event["event_id"] == "purchase"
    assert event["event_type"] == "custom_event"
    assert event["enabled"] is None
    assert event["value"] is None
    assert event["traits"] == {"plan": "premium"}
    assert event["metadata"]["amount"] == 99
    assert "sdk_version" in event["metadata"]


def test_start_stop_lifecycle() -> None:
    config = PipelineAnalyticsConfig(
        analytics_server_url="http://test/", flush_interval_seconds=100
    )
    processor = PipelineAnalyticsProcessor(config=config, environment_key="key")

    processor.start()
    assert processor._timer is not None
    assert processor._timer.is_alive()

    with mock.patch("flagsmith.analytics.session"):
        processor.record_evaluation_event(
            flag_key="my_flag", enabled=True, value="v1"
        )
        processor.stop()

    assert len(processor._buffer) == 0
