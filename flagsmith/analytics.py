import copy
import logging
from collections import UserDict
from datetime import datetime

import requests
from requests_futures.sessions import FuturesSession

logger = logging.getLogger(__name__)

ANALYTICS_ENDPOINT = "analytics/flags/"

# Used to control how often we send data(in seconds)
ANALYTICS_TIMER = 10

session = FuturesSession(max_workers=4)


class AnalyticsProcessor:
    """
    AnalyticsProcessor is used to track how often individual Flags are evaluated within the Flagsmith SDK
    docs: https://docs.flagsmith.com/advanced-use/flag-analytics
    """

    def __init__(self, environment_key: str, base_api_url: str, timeout: int = 3):
        """
        Initialise Flagsmith environment.

        :param environment_key: environment key obtained from the Flagsmith UI
        :param  base_api_url:  base api url to override when using self hosted version
        :param timeout: used to tell requests to stop waiting for a response after a given number of seconds
        """
        self.analytics_endpoint = base_api_url + ANALYTICS_ENDPOINT
        self.environment_key = environment_key
        self._last_flushed = datetime.now()
        self.analytics_data = {}
        self.timeout = timeout
        super().__init__()

    def flush(self):
        """
        Sends all the collected data to the api asynchronously and resets the timer
        """

        if not self.analytics_data:
            return
        try:
            # create a copy of the `analytics_data` because we call `clear` on the dictionary later
            # and for the obvious reason when mocking we get the empty dict.
            data = copy.copy(self.analytics_data)
            session.post(
                self.analytics_endpoint,
                data=data,
                timeout=self.timeout,
                headers={"X-Environment-Key": self.environment_key},
            )

            self.analytics_data.clear()
            self._last_flushed = datetime.now()

        except requests.RequestException as e:
            logger.error("Failed to send anaytics data. Error message was %s" % e)

    def track_feature(self, feature_id: int):
        self.analytics_data[feature_id] = self.analytics_data.get(feature_id, 0) + 1
        if (datetime.now() - self._last_flushed).seconds > ANALYTICS_TIMER:
            self.flush()
