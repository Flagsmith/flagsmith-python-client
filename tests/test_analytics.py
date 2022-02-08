import json
import logging
from datetime import datetime, timedelta
from unittest import mock

import requests

from flagsmith.analytics import (
    DEFAULT_FLUSH_INTERVAL_SECONDS,
    AnalyticsProcessor,
)


def test_analytics_processor_track_feature_updates_analytics_data(analytics_processor):
    # When
    analytics_processor.track_feature(1)
    assert analytics_processor.analytics_data[1] == 1

    analytics_processor.track_feature(1)
    assert analytics_processor.analytics_data[1] == 2


def test_analytics_processor_flush_clears_analytics_data(analytics_processor):
    analytics_processor.track_feature(1)
    analytics_processor.flush()
    assert analytics_processor.analytics_data == {}


def test_analytics_processor_flush_post_request_data_match_analytics_data(mocker):
    # Given
    mock_session = mocker.MagicMock()
    analytics_processor = AnalyticsProcessor(
        environment_key="test-key",
        base_api_url="https://test.api.url/",
        session=mock_session,
    )

    # When
    analytics_processor.track_feature(1)
    analytics_processor.track_feature(2)
    analytics_processor.flush()

    # Then
    mock_session.post.assert_called_once()
    post_call = mock_session.post.mock_calls[0]
    assert {"1": 1, "2": 1} == json.loads(post_call[2]["data"])


def test_analytics_processor_flush_early_exit_if_analytics_data_is_empty(mocker):
    # Given
    mock_session = mocker.MagicMock()
    analytics_processor = AnalyticsProcessor(
        environment_key="test-key",
        base_api_url="https://test.api.url/",
        session=mock_session,
    )

    # When
    analytics_processor.flush()

    # Then
    mock_session.post.assert_not_called()


def test_analytics_processor_calling_track_feature_calls_flush_when_timer_runs_out(
    mocker,
):
    # Given
    mock_session = mocker.MagicMock()
    analytics_processor = AnalyticsProcessor(
        environment_key="test-key",
        base_api_url="https://test.api.url/",
        session=mock_session,
    )

    with mock.patch("flagsmith.analytics.datetime") as mocked_datetime:
        # Let's move the time
        mocked_datetime.now.return_value = datetime.now() + timedelta(
            seconds=DEFAULT_FLUSH_INTERVAL_SECONDS + 1
        )
        # When
        analytics_processor.track_feature(1)

    # Then
    mock_session.post.assert_called()


def test_flush_swallows_connection_error_and_does_not_clear_analytics_data(
    mocker, caplog
):
    # Given
    mock_session = mocker.MagicMock()
    mock_session.post.side_effect = requests.ConnectionError

    analytics_processor = AnalyticsProcessor(
        environment_key="test-key",
        base_api_url="https://test.api.url/",
        session=mock_session,
    )

    # When
    analytics_processor.track_feature(1)
    analytics_processor.flush()

    # Then
    # No exception raised and analytics processor still has data
    assert analytics_processor.analytics_data == {1: 1}
    assert len(caplog.records) == 1
    assert caplog.records[0].levelno == logging.ERROR
    assert caplog.records[0].msg == "Unable to send flag evaluation analytics to API."
