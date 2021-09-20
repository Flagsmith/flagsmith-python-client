import logging
from collections import UserDict
from datetime import datetime

from requests_futures.sessions import FuturesSession

logger = logging.getLogger(__name__)

ANALYTICS_ENDPOINT = "analytics/flags/"

# Used to control how often we send data(in seconds)
ANALYTICS_TIMER = 10

session = FuturesSession()


class AnalyticsProc(UserDict):
    """
    AnalyticsProc is used to track how often individual Flags are evaluated within the Flagsmith SDK
    docs: https://docs.flagsmith.com/advanced-use/flag-analytics
    """

    def __init__(self, environment_id, api):
        """
        Initialise Flagsmith environment.

        :param environment_id: environment key obtained from the Flagsmith UI
        :param api:  api url to override when using self hosted version
        """
        self.analytics_endpoint = api + ANALYTICS_ENDPOINT
        self.environment_id = environment_id
        self._last_flushed = datetime.now()
        super().__init__()

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if (datetime.now() - self._last_flushed).seconds > ANALYTICS_TIMER:
            self.flush()
            self._last_flushed = datetime.now()
            self.clear()

    def flush(self):
        try:
            session.post(
                self.analytics_endpoint,
                data=self.data,
                timeout=5,
                headers={"X-Environment-Key": self.environment_id},
            )

        except Exception as e:
            logger.error("Failed to send anaytics data. Error message was %s" % e)

    def track_feature(self, feature_id: int):
        self[feature_id] = self.get(feature_id, 0) + 1
