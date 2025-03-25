import threading
import time
import typing

import httpx

ANALYTICS_ENDPOINT: typing.Final[str] = "analytics/flags/"

# Used to control how often we send data(in seconds)
ANALYTICS_TIMER: typing.Final[int] = 10


class AnalyticsProcessor(threading.Thread):
    """
    AnalyticsProcessor is used to track how often individual Flags are evaluated within
    the Flagsmith SDK. Docs: https://docs.flagsmith.com/advanced-use/flag-analytics.
    """

    def __init__(
        self,
        *args: typing.Any,
        environment_key: str,
        base_api_url: str,
        client: httpx.Client | None = None,
        **kwargs: typing.Any,
    ):
        """
        Initialise the AnalyticsProcessor to handle sending analytics on flag usage to
        the Flagsmith API.

        :param environment_key: environment key obtained from the Flagsmith UI
        :param base_api_url: base api url to override when using self hosted version
        :param timeout: used to tell requests to stop waiting for a response after a
            given number of seconds
        """
        super().__init__(*args, **kwargs)

        self.analytics_endpoint = base_api_url + ANALYTICS_ENDPOINT
        self.environment_key = environment_key
        self.analytics_data: typing.MutableMapping[str, typing.Any] = {}

        self._client = client or httpx.Client()
        self._client.headers.update({"X-Environment-Key": self.environment_key})

        self._stop_event = threading.Event()

    def flush(self) -> None:
        """
        Sends all the collected data to the api asynchronously and resets the timer
        """

        if not self.analytics_data:
            return

        self._client.post(
            self.analytics_endpoint,
            data=self.analytics_data,
            headers={
                "X-Environment-Key": self.environment_key,
                "Content-Type": "application/json",
            },
        )

        self.analytics_data.clear()

    def track_feature(self, feature_name: str) -> None:
        self.analytics_data[feature_name] = self.analytics_data.get(feature_name, 0) + 1

    def run(self) -> None:
        while not self._stop_event.is_set():
            time.sleep(ANALYTICS_TIMER)
            self.flush()

    def stop(self) -> None:
        self._stop_event.set()

    def __del__(self) -> None:
        self._stop_event.set()
