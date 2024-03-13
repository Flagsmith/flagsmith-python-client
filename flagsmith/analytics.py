import json
import typing
from datetime import datetime

from requests_futures.sessions import FuturesSession  # type: ignore

ANALYTICS_ENDPOINT: typing.Final[str] = "analytics/flags/"

# Used to control how often we send data(in seconds)
ANALYTICS_TIMER: typing.Final[int] = 10

session = FuturesSession(max_workers=4)


class AnalyticsProcessor:
    """
    AnalyticsProcessor is used to track how often individual Flags are evaluated within
    the Flagsmith SDK. Docs: https://docs.flagsmith.com/advanced-use/flag-analytics.
    """

    def __init__(
        self, environment_key: str, base_api_url: str, timeout: typing.Optional[int] = 3
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
        self._last_flushed = datetime.now()
        self.analytics_data: typing.MutableMapping[str, typing.Any] = {}
        self.timeout = timeout or 3

    def flush(self) -> None:
        """
        Sends all the collected data to the api asynchronously and resets the timer
        """

        if not self.analytics_data:
            return
        session.post(
            self.analytics_endpoint,
            data=json.dumps(self.analytics_data),
            timeout=self.timeout,
            headers={
                "X-Environment-Key": self.environment_key,
                "Content-Type": "application/json",
            },
        )

        self.analytics_data.clear()
        self._last_flushed = datetime.now()

    def track_feature(self, feature_name: str) -> None:
        self.analytics_data[feature_name] = self.analytics_data.get(feature_name, 0) + 1
        if (datetime.now() - self._last_flushed).seconds > ANALYTICS_TIMER:
            self.flush()
