import json
import logging
import typing
from datetime import datetime

import pytz
import requests
from flag_engine import engine
from flag_engine.environments.models import EnvironmentModel
from flag_engine.identities.models import IdentityModel, TraitModel
from flag_engine.segments.evaluator import get_identity_segments
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from flagsmith.analytics import AnalyticsProcessor
from flagsmith.exceptions import FlagsmithAPIError, FlagsmithClientError
from flagsmith.models import DefaultFlag, Flags, Segment
from flagsmith.offline_handlers import BaseOfflineHandler
from flagsmith.polling_manager import EnvironmentDataPollingManager
from flagsmith.streaming_manager import EventStreamManager
from flagsmith.utils.identities import generate_identities_data

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://edge.api.flagsmith.com/api/v1/"
DEFAULT_REALTIME_API_URL = "https://realtime.flagsmith.com/"


class Flagsmith:
    """A Flagsmith client.

    Provides an interface for interacting with the Flagsmith http API.

    Basic Usage::

      >>> from flagsmith import Flagsmith
      >>> flagsmith = Flagsmith(environment_key="<your API key>")
      >>> environment_flags = flagsmith.get_environment_flags()
      >>> feature_enabled = environment_flags.is_feature_enabled("foo")
      >>> identity_flags = flagsmith.get_identity_flags("identifier", {"foo": "bar"})
      >>> feature_enabled_for_identity = identity_flags.is_feature_enabled("foo")
    """

    def __init__(
        self,
        environment_key: str = None,
        api_url: str = None,
        realtime_api_url: str = None,
        custom_headers: typing.Dict[str, typing.Any] = None,
        request_timeout_seconds: int = None,
        enable_local_evaluation: bool = False,
        environment_refresh_interval_seconds: typing.Union[int, float] = 60,
        retries: Retry = None,
        enable_analytics: bool = False,
        default_flag_handler: typing.Callable[[str], DefaultFlag] = None,
        proxies: typing.Dict[str, str] = None,
        offline_mode: bool = False,
        offline_handler: BaseOfflineHandler = None,
        use_stream: bool = False,
    ):
        """
        :param environment_key: The environment key obtained from Flagsmith interface.
            Required unless offline_mode is True.
        :param api_url: Override the URL of the Flagsmith API to communicate with
        :param realtime_api_url: Override the URL of the Flagsmith real-time API
        :param custom_headers: Additional headers to add to requests made to the
            Flagsmith API
        :param request_timeout_seconds: Number of seconds to wait for a request to
            complete before terminating the request
        :param enable_local_evaluation: Enables local evaluation of flags
        :param environment_refresh_interval_seconds: If using local evaluation,
            specify the interval period between refreshes of local environment data
        :param retries: a urllib3.Retry object to use on all http requests to the
            Flagsmith API
        :param enable_analytics: if enabled, sends additional requests to the Flagsmith
            API to power flag analytics charts
        :param default_flag_handler: callable which will be used in the case where
            flags cannot be retrieved from the API or a non-existent feature is
            requested
        :param proxies: as per https://requests.readthedocs.io/en/latest/api/#requests.Session.proxies
        :param offline_mode: sets the client into offline mode. Relies on offline_handler for
            evaluating flags.
        :param offline_handler: provide a handler for offline logic. Used to get environment
            document from another source when in offline_mode. Works in place of
            default_flag_handler if offline_mode is not set and using remote evaluation.
        :param use_stream: Use real-time functionality via SSE as opposed to polling the API
        """

        self.offline_mode = offline_mode
        self.enable_local_evaluation = enable_local_evaluation
        self.offline_handler = offline_handler
        self.default_flag_handler = default_flag_handler
        self.use_stream = use_stream
        self._analytics_processor = None
        self._environment = None

        # argument validation
        if offline_mode and not offline_handler:
            raise ValueError("offline_handler must be provided to use offline mode.")
        elif default_flag_handler and offline_handler:
            raise ValueError(
                "Cannot use both default_flag_handler and offline_handler."
            )

        if self.offline_handler:
            self._environment = self.offline_handler.get_environment()

        if not self.offline_mode:
            if not environment_key:
                raise ValueError("environment_key is required.")

            self.session = requests.Session()
            self.session.headers.update(
                **{"X-Environment-Key": environment_key}, **(custom_headers or {})
            )
            self.session.proxies.update(proxies or {})
            retries = retries or Retry(total=3, backoff_factor=0.1)

            api_url = api_url or DEFAULT_API_URL
            self.api_url = api_url if api_url.endswith("/") else f"{api_url}/"

            realtime_api_url = realtime_api_url or DEFAULT_REALTIME_API_URL
            self.realtime_api_url = (
                realtime_api_url
                if realtime_api_url.endswith("/")
                else f"{realtime_api_url}/"
            )

            self.request_timeout_seconds = request_timeout_seconds
            self.session.mount(self.api_url, HTTPAdapter(max_retries=retries))

            self.environment_flags_url = f"{self.api_url}flags/"
            self.identities_url = f"{self.api_url}identities/"
            self.environment_url = f"{self.api_url}environment-document/"

            if self.enable_local_evaluation:
                if not environment_key.startswith("ser."):
                    raise ValueError(
                        "In order to use local evaluation, please generate a server key "
                        "in the environment settings page."
                    )

                if self.use_stream:
                    self.update_environment()
                    stream_url = f"{self.realtime_api_url}sse/environments/{self._environment.api_key}/stream"

                    self.event_stream_thread = EventStreamManager(
                        stream_url=stream_url,
                        on_event=self.handle_stream_event,
                        daemon=True,  # noqa
                    )

                    self.event_stream_thread.start()

                else:
                    self.environment_data_polling_manager_thread = EnvironmentDataPollingManager(
                        main=self,
                        refresh_interval_seconds=environment_refresh_interval_seconds,
                        daemon=True,  # noqa
                    )
                    self.environment_data_polling_manager_thread.start()

            if enable_analytics:
                self._analytics_processor = AnalyticsProcessor(
                    environment_key, self.api_url, timeout=self.request_timeout_seconds
                )

    def handle_stream_event(self, event):
        event_data = json.loads(event.data)
        stream_updated_at = datetime.fromtimestamp(event_data.get("updated_at"))

        if stream_updated_at.tzinfo is None:
            stream_updated_at = pytz.utc.localize(stream_updated_at)

        environment_updated_at = self._environment.updated_at
        if environment_updated_at.tzinfo is None:
            environment_updated_at = pytz.utc.localize(environment_updated_at)

        if stream_updated_at > environment_updated_at:
            self.update_environment()

    def get_environment_flags(self) -> Flags:
        """
        Get all the default for flags for the current environment.

        :return: Flags object holding all the flags for the current environment.
        """
        if (self.offline_mode or self.enable_local_evaluation) and self._environment:
            return self._get_environment_flags_from_document()
        return self._get_environment_flags_from_api()

    def get_identity_flags(
        self, identifier: str, traits: typing.Dict[str, typing.Any] = None
    ) -> Flags:
        """
        Get all the flags for the current environment for a given identity. Will also
        upsert all traits to the Flagsmith API for future evaluations. Providing a
        trait with a value of None will remove the trait from the identity if it exists.

        :param identifier: a unique identifier for the identity in the current
            environment, e.g. email address, username, uuid
        :param traits: a dictionary of traits to add / update on the identity in
            Flagsmith, e.g. {"num_orders": 10}
        :return: Flags object holding all the flags for the given identity.
        """
        traits = traits or {}
        if (self.offline_mode or self.enable_local_evaluation) and self._environment:
            return self._get_identity_flags_from_document(identifier, traits)
        return self._get_identity_flags_from_api(identifier, traits)

    def get_identity_segments(
        self, identifier: str, traits: typing.Dict[str, typing.Any] = None
    ) -> typing.List[Segment]:
        """
        Get a list of segments that the given identity is in.

        :param identifier: a unique identifier for the identity in the current
            environment, e.g. email address, username, uuid
        :param traits: a dictionary of traits to add / update on the identity in
            Flagsmith, e.g. {"num_orders": 10}
        :return: list of Segment objects that the identity is part of.
        """

        if not self._environment:
            raise FlagsmithClientError(
                "Local evaluation required to obtain identity segments."
            )

        traits = traits or {}
        identity_model = self._build_identity_model(identifier, **traits)
        segment_models = get_identity_segments(self._environment, identity_model)
        return [Segment(id=sm.id, name=sm.name) for sm in segment_models]

    def update_environment(self):
        self._environment = self._get_environment_from_api()

    def _get_environment_from_api(self) -> EnvironmentModel:
        environment_data = self._get_json_response(self.environment_url, method="GET")
        return EnvironmentModel.model_validate(environment_data)

    def _get_environment_flags_from_document(self) -> Flags:
        return Flags.from_feature_state_models(
            feature_states=engine.get_environment_feature_states(self._environment),
            analytics_processor=self._analytics_processor,
            default_flag_handler=self.default_flag_handler,
        )

    def _get_identity_flags_from_document(
        self, identifier: str, traits: typing.Dict[str, typing.Any]
    ) -> Flags:
        identity_model = self._build_identity_model(identifier, **traits)
        feature_states = engine.get_identity_feature_states(
            self._environment, identity_model
        )
        return Flags.from_feature_state_models(
            feature_states=feature_states,
            analytics_processor=self._analytics_processor,
            identity_id=identity_model.composite_key,
            default_flag_handler=self.default_flag_handler,
        )

    def _get_environment_flags_from_api(self) -> Flags:
        try:
            api_flags = self._get_json_response(
                url=self.environment_flags_url, method="GET"
            )
            return Flags.from_api_flags(
                api_flags=api_flags,
                analytics_processor=self._analytics_processor,
                default_flag_handler=self.default_flag_handler,
            )
        except FlagsmithAPIError:
            if self.offline_handler:
                return self._get_environment_flags_from_document()
            elif self.default_flag_handler:
                return Flags(default_flag_handler=self.default_flag_handler)
            raise

    def _get_identity_flags_from_api(
        self, identifier: str, traits: typing.Dict[str, typing.Any]
    ) -> Flags:
        try:
            data = generate_identities_data(identifier, traits)
            json_response = self._get_json_response(
                url=self.identities_url, method="POST", body=data
            )
            return Flags.from_api_flags(
                api_flags=json_response["flags"],
                analytics_processor=self._analytics_processor,
                default_flag_handler=self.default_flag_handler,
            )
        except FlagsmithAPIError:
            if self.offline_handler:
                return self._get_identity_flags_from_document(identifier, traits)
            elif self.default_flag_handler:
                return Flags(default_flag_handler=self.default_flag_handler)
            raise

    def _get_json_response(self, url: str, method: str, body: dict = None):
        try:
            request_method = getattr(self.session, method.lower())
            response = request_method(
                url, json=body, timeout=self.request_timeout_seconds
            )
            if response.status_code != 200:
                raise FlagsmithAPIError(
                    "Invalid request made to Flagsmith API. Response status code: %d",
                    response.status_code,
                )
            return response.json()
        except (requests.ConnectionError, json.JSONDecodeError) as e:
            raise FlagsmithAPIError(
                "Unable to get valid response from Flagsmith API."
            ) from e

    def _build_identity_model(self, identifier: str, **traits):
        if not self._environment:
            raise FlagsmithClientError(
                "Unable to build identity model when no local environment present."
            )

        trait_models = [
            TraitModel(trait_key=key, trait_value=value)
            for key, value in traits.items()
        ]
        return IdentityModel(
            identifier=identifier,
            environment_api_key=self._environment.api_key,
            identity_traits=trait_models,
        )

    def __del__(self):
        if hasattr(self, "environment_data_polling_manager_thread"):
            self.environment_data_polling_manager_thread.stop()

        if hasattr(self, "event_stream_thread"):
            self.event_stream_thread.stop()
