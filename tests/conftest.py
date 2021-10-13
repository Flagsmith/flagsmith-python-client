import pytest

from flagsmith.analytics import AnalyticsProcessor
from flagsmith.utils import generate_header_content


@pytest.fixture
def analytics_processor():
    return AnalyticsProcessor(
        base_api_url="http://test_url", http_headers=generate_header_content("test_key")
    )
