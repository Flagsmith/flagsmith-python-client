import pytest

from flagsmith.analytics import AnalyticsProcessor


@pytest.fixture
def analytics_processor():
    return AnalyticsProcessor(
        environment_key="test_key", base_api_url="http://test_url"
    )
