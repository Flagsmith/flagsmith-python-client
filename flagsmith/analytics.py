import json
import logging
from datetime import datetime, timedelta

import requests
from requests_futures.sessions import FuturesSession

ANALYTICS_ENDPOINT = "analytics/flags/"

# Used to control how often we send data(in seconds)
DEFAULT_FLUSH_INTERVAL_SECONDS = 10

logger = logging.getLogger(__name__)


class AnalyticsProcessor:
    """
    AnalyticsProcessor is used to track how often individual Flags are evaluated within
    the Flagsmith SDK. Docs: https://docs.flagsmith.com/advanced-use/flag-analytics.
    """

    def __init__(
        self,
        environment_key: str,
        base_api_url: str,
        timeout: int = 3,
        session: FuturesSession = None,
        flush_interval_seconds: int = DEFAULT_FLUSH_INTERVAL_SECONDS,
    ):
        """
        Initialise the AnalyticsProcessor to handle sending analytics on flag usage to
        the Flagsmith API.

        :param environment_key: environment key obtained from the Flagsmith UI
        :param base_api_url: base api url to override when using self hosted version
        :param timeout: used to tell requests to stop waiting for a response after a
            given number of seconds
        """
        self.analytics_endpoint = base_api_url + ANALYTICS_ENDPOINT
        self.environment_key = environment_key
        self.analytics_data = {}
        self.timeout = timeout
        self.session = session or FuturesSession(max_workers=4)
        self.flush_interval_seconds = flush_interval_seconds
        self._next_flush = self._get_next_flush()

    def flush(self):
        """
        Sends all the collected data to the api asynchronously and resets the timer
        """

        if not self.analytics_data:
            return

        try:
            self.session.post(
                self.analytics_endpoint,
                data=json.dumps(self.analytics_data),
                timeout=self.timeout,
                headers={
                    "X-Environment-Key": self.environment_key,
                    "Content-Type": "application/json",
                },
            )
            self.analytics_data.clear()
        except requests.ConnectionError as e:
            logger.error("Unable to send flag evaluation analytics to API.", exc_info=e)

        self._next_flush = self._get_next_flush()

    def track_feature(self, feature_id: int):
        self.analytics_data[feature_id] = self.analytics_data.get(feature_id, 0) + 1
        if datetime.now() > self._next_flush:
            self.flush()

    def _get_next_flush(self):
        return datetime.now() + timedelta(seconds=self.flush_interval_seconds)
