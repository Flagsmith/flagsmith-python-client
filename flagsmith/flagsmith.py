import logging
import typing
from datetime import datetime
from urllib.parse import urljoin

import requests
from flag_engine import engine
from requests.adapters import HTTPAdapter
from urllib3 import Retry

from flagsmith.analytics import AnalyticsProcessor
from flagsmith.exceptions import FlagsmithAPIError, FlagsmithClientError
from flagsmith.mappers import (
    map_context_and_identity_data_to_context,
    map_environment_document_to_context,
    map_environment_document_to_environment_updated_at,
)
from flagsmith.models import DefaultFlag, Flags, Segment
from flagsmith.offline_handlers import OfflineHandler
from flagsmith.polling_manager import EnvironmentDataPollingManager
from flagsmith.streaming_manager import EventStreamManager
from flagsmith.types import (
    ApplicationMetadata,
    JsonType,
    StreamEvent,
    TraitMapping,
)
from flagsmith.utils.identities import generate_identity_data
from flagsmith.version import __version__

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://edge.api.flagsmith.com/api/v1/"
DEFAULT_REALTIME_API_URL = "https://realtime.flagsmith.com/"
DEFAULT_USER_AGENT = f"flagsmith-python-sdk/{__version__}"


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
        environment_key: typing.Optional[str] = None,
        api_url: typing.Optional[str] = None,
        realtime_api_url: typing.Optional[str] = None,
        custom_headers: typing.Optional[typing.Dict[str, typing.Any]] = None,
        request_timeout_seconds: typing.Optional[int] = 10,
        enable_local_evaluation: bool = False,
        environment_refresh_interval_seconds: typing.Union[int, float] = 60,
        retries: typing.Optional[Retry] = None,
        enable_analytics: bool = False,
        default_flag_handler: typing.Optional[
            typing.Callable[[str], DefaultFlag]
        ] = None,
        proxies: typing.Optional[typing.Dict[str, str]] = None,
        offline_mode: bool = False,
        offline_handler: typing.Optional[OfflineHandler] = None,
        enable_realtime_updates: bool = False,
        application_metadata: typing.Optional[ApplicationMetadata] = None,
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
        :param enable_realtime_updates: Use real-time functionality via SSE as opposed to polling the API
        :param application_metadata: Optional metadata about the client application.
        """

        self.offline_mode = offline_mode
        self.enable_local_evaluation = enable_local_evaluation
        self.environment_refresh_interval_seconds = environment_refresh_interval_seconds
        self.offline_handler = offline_handler
        self.default_flag_handler = default_flag_handler
        self.enable_realtime_updates = enable_realtime_updates
        self._analytics_processor: typing.Optional[AnalyticsProcessor] = None
        self._evaluation_context: typing.Optional[engine.EvaluationContext] = None
        self._environment_updated_at: typing.Optional[datetime] = None

        # argument validation
        if offline_mode and not offline_handler:
            raise ValueError("offline_handler must be provided to use offline mode.")
        elif default_flag_handler and offline_handler:
            raise ValueError(
                "Cannot use both default_flag_handler and offline_handler."
            )

        if enable_realtime_updates and not enable_local_evaluation:
            raise ValueError(
                "Can only use realtime updates when running in local evaluation mode."
            )

        if self.offline_handler:
            self._evaluation_context = self.offline_handler.get_evaluation_context()

        if not self.offline_mode:
            if not environment_key:
                raise ValueError("environment_key is required.")

            self.session = requests.Session()
            self.session.headers.update(
                self._get_headers(
                    environment_key=environment_key,
                    application_metadata=application_metadata,
                    custom_headers=custom_headers,
                )
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

            self.environment_flags_url = urljoin(self.api_url, "flags/")
            self.identities_url = urljoin(self.api_url, "identities/")
            self.environment_url = urljoin(self.api_url, "environment-document/")

            if self.enable_local_evaluation:
                if not environment_key.startswith("ser."):
                    raise ValueError(
                        "In order to use local evaluation, please generate a server key "
                        "in the environment settings page."
                    )

                self._initialise_local_evaluation()

            if enable_analytics:
                self._analytics_processor = AnalyticsProcessor(
                    environment_key, self.api_url, timeout=self.request_timeout_seconds
                )

    def _initialise_local_evaluation(self) -> None:
        # To ensure that the environment is set before allowing subsequent
        # method calls, update the environment manually.
        self.update_environment()
        if self.enable_realtime_updates:
            if not self._evaluation_context:
                raise ValueError("Unable to get environment from API key")

            stream_url = urljoin(
                self.realtime_api_url,
                f"sse/environments/{self._evaluation_context['environment']['key']}/stream",
            )

            self.event_stream_thread = EventStreamManager(
                stream_url=stream_url,
                on_event=self.handle_stream_event,
                daemon=True,
            )

            self.event_stream_thread.start()

        else:
            self.environment_data_polling_manager_thread = (
                EnvironmentDataPollingManager(
                    main=self,
                    refresh_interval_seconds=self.environment_refresh_interval_seconds,
                    daemon=True,
                )
            )

            self.environment_data_polling_manager_thread.start()

    def handle_stream_event(self, event: StreamEvent) -> None:
        if not (environment_updated_at := self._environment_updated_at):
            raise ValueError(
                "Cannot handle stream events before retrieving initial environment"
            )
        if event["updated_at"] > environment_updated_at:
            self.update_environment()

    def get_environment_flags(self) -> Flags:
        """
        Get all the default for flags for the current environment.

        :return: Flags object holding all the flags for the current environment.
        """
        if (
            self.offline_mode or self.enable_local_evaluation
        ) and self._evaluation_context:
            return self._get_environment_flags_from_document()
        return self._get_environment_flags_from_api()

    def get_identity_flags(
        self,
        identifier: str,
        traits: typing.Optional[TraitMapping] = None,
        *,
        transient: bool = False,
    ) -> Flags:
        """
        Get all the flags for the current environment for a given identity. Will also
        upsert all traits to the Flagsmith API for future evaluations. Providing a
        trait with a value of None will remove the trait from the identity if it exists.

        :param identifier: a unique identifier for the identity in the current
            environment, e.g. email address, username, uuid
        :param traits: a dictionary of traits to add / update on the identity in
            Flagsmith, e.g. `{"num_orders": 10}`. Envelope traits you don't want persisted
            in a dictionary with `"transient"` and `"value"` keys, e.g.
            `{"num_orders": 10, "color": {"value": "pink", "transient": True}}`.
        :param transient: if `True`, the identity won't get persisted
        :return: Flags object holding all the flags for the given identity.
        """
        traits = traits or {}
        if (
            self.offline_mode or self.enable_local_evaluation
        ) and self._evaluation_context:
            return self._get_identity_flags_from_document(identifier, traits)
        return self._get_identity_flags_from_api(
            identifier,
            traits,
            transient=transient,
        )

    def get_identity_segments(
        self,
        identifier: str,
        traits: typing.Optional[typing.Mapping[str, engine.ContextValue]] = None,
    ) -> typing.List[Segment]:
        """
        Get a list of segments that the given identity is in.

        :param identifier: a unique identifier for the identity in the current
            environment, e.g. email address, username, uuid
        :param traits: a dictionary of traits to add / update on the identity in
            Flagsmith, e.g. {"num_orders": 10}
        :return: list of Segment objects that the identity is part of.
        """
        if not self._evaluation_context:
            raise FlagsmithClientError(
                "Local evaluation required to obtain identity segments."
            )

        context = map_context_and_identity_data_to_context(
            context=self._evaluation_context,
            identifier=identifier,
            traits=traits,
        )

        evaluation_result = engine.get_evaluation_result(
            context=context,
        )
        return [
            Segment(id=int(segment_result["key"]), name=segment_result["name"])
            for segment_result in evaluation_result["segments"]
        ]

    def update_environment(self) -> None:
        try:
            environment_data = self._get_json_response(
                self.environment_url, method="GET"
            )
        except FlagsmithAPIError:
            logger.exception("Error retrieving environment document from API")
        else:
            try:
                self._evaluation_context = map_environment_document_to_context(
                    environment_data,
                )
                self._environment_updated_at = (
                    map_environment_document_to_environment_updated_at(
                        environment_data,
                    )
                )
            except (KeyError, TypeError, ValueError):
                logger.exception("Error parsing environment document")

    def _get_headers(
        self,
        environment_key: str,
        application_metadata: typing.Optional[ApplicationMetadata],
        custom_headers: typing.Optional[typing.Dict[str, typing.Any]],
    ) -> typing.Dict[str, str]:
        headers = {
            "X-Environment-Key": environment_key,
            "User-Agent": DEFAULT_USER_AGENT,
        }
        if application_metadata:
            if name := application_metadata.get("name"):
                headers["Flagsmith-Application-Name"] = name
            if version := application_metadata.get("version"):
                headers["Flagsmith-Application-Version"] = version
        headers.update(custom_headers or {})
        return headers

    def _get_environment_flags_from_document(self) -> Flags:
        if self._evaluation_context is None:
            raise TypeError("No environment present")

        evaluation_result = engine.get_evaluation_result(self._evaluation_context)

        return Flags.from_evaluation_result(
            evaluation_result=evaluation_result,
            analytics_processor=self._analytics_processor,
            default_flag_handler=self.default_flag_handler,
        )

    def _get_identity_flags_from_document(
        self,
        identifier: str,
        traits: TraitMapping,
    ) -> Flags:
        if self._evaluation_context is None:
            raise TypeError("No environment present")

        context = map_context_and_identity_data_to_context(
            context=self._evaluation_context,
            identifier=identifier,
            traits=traits,
        )
        evaluation_result = engine.get_evaluation_result(
            context=context,
        )

        return Flags.from_evaluation_result(
            evaluation_result=evaluation_result,
            analytics_processor=self._analytics_processor,
            default_flag_handler=self.default_flag_handler,
        )

    def _get_environment_flags_from_api(self) -> Flags:
        try:
            json_response: typing.List[typing.Mapping[str, JsonType]] = (
                self._get_json_response(url=self.environment_flags_url, method="GET")
            )
            return Flags.from_api_flags(
                api_flags=json_response,
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
        self,
        identifier: str,
        traits: TraitMapping,
        *,
        transient: bool = False,
    ) -> Flags:
        request_body = generate_identity_data(
            identifier,
            traits,
            transient=transient,
        )
        try:
            json_response: typing.Dict[str, typing.List[typing.Dict[str, JsonType]]] = (
                self._get_json_response(
                    url=self.identities_url,
                    method="POST",
                    body=request_body,
                )
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

    def _get_json_response(
        self,
        url: str,
        method: str,
        body: typing.Optional[JsonType] = None,
    ) -> typing.Any:
        try:
            request_method = getattr(self.session, method.lower())
            response = request_method(
                url, json=body, timeout=self.request_timeout_seconds
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            raise FlagsmithAPIError(
                "Unable to get valid response from Flagsmith API."
            ) from e

    def __del__(self) -> None:
        if hasattr(self, "environment_data_polling_manager_thread"):
            self.environment_data_polling_manager_thread.stop()

        if hasattr(self, "event_stream_thread"):
            self.event_stream_thread.stop()
