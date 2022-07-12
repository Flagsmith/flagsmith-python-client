import json
from datetime import datetime, timedelta
from unittest import mock

from flagsmith.analytics import ANALYTICS_TIMER


def test_analytics_processor_track_feature_updates_analytics_data(analytics_processor):
    # When
    analytics_processor.track_feature("my_feature")
    assert analytics_processor.analytics_data["my_feature"] == 1

    analytics_processor.track_feature("my_feature")
    assert analytics_processor.analytics_data["my_feature"] == 2


def test_analytics_processor_flush_clears_analytics_data(analytics_processor):
    analytics_processor.track_feature("my_feature")
    analytics_processor.flush()
    assert analytics_processor.analytics_data == {}


def test_analytics_processor_flush_post_request_data_match_ananlytics_data(
    analytics_processor,
):
    # Given
    with mock.patch("flagsmith.analytics.session") as session:
        # When
        analytics_processor.track_feature("my_feature_1")
        analytics_processor.track_feature("my_feature_2")
        analytics_processor.flush()
    # Then
    session.post.assert_called()
    post_call = session.mock_calls[0]
    assert {"my_feature_1": 1, "my_feature_2": 1} == json.loads(post_call[2]["data"])


def test_analytics_processor_flush_early_exit_if_analytics_data_is_empty(
    analytics_processor,
):
    with mock.patch("flagsmith.analytics.session") as session:
        analytics_processor.flush()

    # Then
    session.post.assert_not_called()


def test_analytics_processor_calling_track_feature_calls_flush_when_timer_runs_out(
    analytics_processor,
):
    # Given
    with mock.patch("flagsmith.analytics.datetime") as mocked_datetime, mock.patch(
        "flagsmith.analytics.session"
    ) as session:
        # Let's move the time
        mocked_datetime.now.return_value = datetime.now() + timedelta(
            seconds=ANALYTICS_TIMER + 1
        )
        # When
        analytics_processor.track_feature("my_feature")

    # Then
    session.post.assert_called()
