import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from threading import Event
from unittest import mock

from flagsmith.analytics import (
    ANALYTICS_ENDPOINT,
    ANALYTICS_TIMER,
    AnalyticsProcessor,
)


def test_analytics_processor_track_feature_updates_analytics_data(
    analytics_processor: AnalyticsProcessor,
) -> None:
    # When
    analytics_processor.track_feature("my_feature")
    assert analytics_processor.analytics_data["my_feature"] == 1

    analytics_processor.track_feature("my_feature")
    assert analytics_processor.analytics_data["my_feature"] == 2


def test_analytics_processor_flush_clears_analytics_data(
    analytics_processor: AnalyticsProcessor,
) -> None:
    analytics_processor.track_feature("my_feature")
    analytics_processor.flush()
    assert analytics_processor.analytics_data == {}


def test_analytics_processor_flush_post_request_data_match_ananlytics_data(
    analytics_processor: AnalyticsProcessor,
) -> None:
    # Given
    with mock.patch("flagsmith.analytics.session") as session:
        # When
        analytics_processor.track_feature("my_feature_1")
        analytics_processor.track_feature("my_feature_2")
        analytics_processor.flush()
    # Then
    session.post.assert_called()
    post_call = session.mock_calls[0]
    # When analytics_url is unset, the POST falls back to base_api_url + ANALYTICS_ENDPOINT.
    # Locks the default in so a future refactor cannot silently break it.
    assert post_call[1][0] == "http://test_url" + ANALYTICS_ENDPOINT
    assert {"my_feature_1": 1, "my_feature_2": 1} == json.loads(post_call[2]["data"])


def test_analytics_processor_flush_early_exit_if_analytics_data_is_empty(
    analytics_processor: AnalyticsProcessor,
) -> None:
    with mock.patch("flagsmith.analytics.session") as session:
        analytics_processor.flush()

    # Then
    session.post.assert_not_called()


def test_analytics_processor_calling_track_feature_calls_flush_when_timer_runs_out(
    analytics_processor: AnalyticsProcessor,
) -> None:
    # Given
    with (
        mock.patch("flagsmith.analytics.datetime") as mocked_datetime,
        mock.patch("flagsmith.analytics.session") as session,
    ):
        # Let's move the time
        mocked_datetime.now.return_value = datetime.now() + timedelta(
            seconds=ANALYTICS_TIMER + 1
        )
        # When
        analytics_processor.track_feature("my_feature")

    # Then
    session.post.assert_called()


def test_analytics_processor_posts_to_analytics_url_when_set() -> None:
    # Given
    processor = AnalyticsProcessor(
        environment_key="test_key",
        base_api_url="http://edge-proxy/",
        analytics_url="http://core-api/analytics/flags/",
    )

    # When
    with mock.patch("flagsmith.analytics.session") as session:
        processor.track_feature("my_feature")
        processor.flush()

    # Then
    session.post.assert_called_once()
    assert session.post.call_args[0][0] == "http://core-api/analytics/flags/"
    assert "edge-proxy" not in session.post.call_args[0][0]


def test_analytics_processor_preserves_evaluations_during_flush(
    analytics_processor: AnalyticsProcessor,
) -> None:
    submitted = Event()
    release = Event()
    analytics_processor.track_feature("my_feature")

    def post(*args: object, **kwargs: object) -> None:
        submitted.set()
        assert release.wait(5)

    with mock.patch("flagsmith.analytics.session.post", side_effect=post) as post_mock:
        with ThreadPoolExecutor(max_workers=2) as executor:
            flushing = executor.submit(analytics_processor.flush)
            try:
                assert submitted.wait(5)
                # Tracking must finish while submission is still blocked.
                executor.submit(analytics_processor.track_feature, "my_feature").result(
                    timeout=5
                )
                executor.submit(
                    analytics_processor.track_feature, "another_feature"
                ).result(timeout=5)
            finally:
                release.set()
            flushing.result(timeout=5)

        assert json.loads(post_mock.call_args.kwargs["data"]) == {"my_feature": 1}
        assert analytics_processor.analytics_data == {
            "my_feature": 1,
            "another_feature": 1,
        }
        analytics_processor.flush()
        assert json.loads(post_mock.call_args.kwargs["data"]) == {
            "my_feature": 1,
            "another_feature": 1,
        }
        assert analytics_processor.analytics_data == {}
