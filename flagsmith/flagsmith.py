import logging
import typing
from json import JSONDecodeError

import requests
from flag_engine import engine
from flag_engine.environments.builders import build_environment_model
from flag_engine.environments.models import EnvironmentModel
from flag_engine.identities.models import IdentityModel, TraitModel
from requests.adapters import HTTPAdapter, Retry

from flagsmith.analytics import AnalyticsProcessor
from flagsmith.exceptions import FlagsmithAPIError, FlagsmithClientError
from flagsmith.models import DefaultFlag, Flags
from flagsmith.polling_manager import EnvironmentDataPollingManager
from flagsmith.utils.identities import generate_identities_data

logger = logging.getLogger(__name__)

DEFAULT_API_URL = "https://api.flagsmith.com/api/v1/"


class Flagsmith:
    def __init__(
        self,
        environment_key: str,
        api_url: str = DEFAULT_API_URL,
        custom_headers: typing.Dict[str, typing.Any] = None,
        request_timeout_seconds: int = None,
        enable_local_evaluation: bool = False,
        environment_refresh_interval_seconds: int = 60,
        retries: Retry = None,
        enable_analytics: bool = False,
        defaults: typing.List[DefaultFlag] = None,
    ):
        self.session = requests.Session()
        self.session.headers.update(
            **{"X-Environment-Key": environment_key}, **(custom_headers or {})
        )
        retries = retries or Retry(total=3, backoff_factor=0.1)

        self.api_url = api_url if api_url.endswith("/") else f"{api_url}/"
        self.request_timeout_seconds = request_timeout_seconds
        self.session.mount(self.api_url, HTTPAdapter(max_retries=retries))

        self.environment_flags_url = f"{self.api_url}flags/"
        self.identities_url = f"{self.api_url}identities/"
        self.environment_url = f"{self.api_url}environment-document/"

        self._environment = None
        if enable_local_evaluation:
            self.environment_data_polling_manager_thread = (
                EnvironmentDataPollingManager(
                    main=self,
                    refresh_interval_seconds=environment_refresh_interval_seconds,
                )
            )
            self.environment_data_polling_manager_thread.start()

        self._analytics_processor = (
            AnalyticsProcessor(
                environment_key, self.api_url, timeout=self.request_timeout_seconds
            )
            if enable_analytics
            else None
        )

        self.defaults = defaults or []

    def get_environment_flags(self) -> Flags:
        """
        Get all the default for flags for the current environment.

        :return: Flags object holding all the flags for the current environment.
        """
        if self._environment:
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
        if self._environment:
            return self._get_identity_flags_from_document(identifier, traits)
        return self._get_identity_flags_from_api(identifier, traits)

    def update_environment(self):
        self._environment = self._get_environment_from_api()

    def _get_environment_from_api(self) -> EnvironmentModel:
        environment_data = self._get_json_response(self.environment_url, method="GET")
        return build_environment_model(environment_data)

    def _get_environment_flags_from_document(self) -> Flags:
        return Flags.from_feature_state_models(
            feature_states=engine.get_environment_feature_states(self._environment),
            analytics_processor=self._analytics_processor,
            defaults=self.defaults,
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
            defaults=self.defaults,
        )

    def _get_environment_flags_from_api(self) -> Flags:
        api_flags = self._get_json_response(
            url=self.environment_flags_url, method="GET"
        )

        return Flags.from_api_flags(
            api_flags=api_flags,
            analytics_processor=self._analytics_processor,
            defaults=self.defaults,
        )

    def _get_identity_flags_from_api(
        self, identifier: str, traits: typing.Dict[str, typing.Any]
    ) -> Flags:
        data = generate_identities_data(identifier, traits)
        json_response = self._get_json_response(
            url=self.identities_url, method="POST", body=data
        )
        return Flags.from_api_flags(
            api_flags=json_response["flags"],
            analytics_processor=self._analytics_processor,
            defaults=self.defaults,
        )

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
        except (requests.ConnectionError, JSONDecodeError) as e:
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
