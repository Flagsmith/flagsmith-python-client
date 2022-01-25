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
from flagsmith.models import Flags
from flagsmith.polling_manager import EnvironmentDataPollingManager

logger = logging.getLogger(__name__)

API_URL = "https://api.flagsmith.com/api/v1/"
FLAGS_ENDPOINT = "flags/"
IDENTITY_ENDPOINT = "identities/"
TRAITS_ENDPOINT = "traits/"


class Flagsmith:
    def __init__(
        self,
        environment_key: str,
        api_url: str = API_URL,
        custom_headers: typing.Dict[str, typing.Any] = None,
        request_timeout: int = None,
        enable_client_side_evaluation: bool = False,
        environment_refresh_interval_seconds: int = 10,
        retries: Retry = None,
    ):
        self.session = requests.Session()
        self.session.headers.update(
            **{"X-Environment-Key": environment_key}, **(custom_headers or {})
        )
        retries = retries or Retry(total=3, backoff_factor=0.1)

        self.api_url = api_url if api_url.endswith("/") else f"{api_url}/"
        self.request_timeout = request_timeout
        self.session.mount(self.api_url, HTTPAdapter(max_retries=retries))

        self.environment_flags_url = f"{self.api_url}flags/"
        self.identities_url = f"{self.api_url}identities/"
        self.environment_url = f"{self.api_url}environment/"

        self._environment = None
        if enable_client_side_evaluation:
            self.environment_data_polling_manager_thread = (
                EnvironmentDataPollingManager(
                    main=self,
                    refresh_interval_seconds=environment_refresh_interval_seconds,
                )
            )
            self.environment_data_polling_manager_thread.start()

        self._analytics_processor = AnalyticsProcessor(
            environment_key, self.api_url, timeout=self.request_timeout
        )

    def get_environment_flags(self) -> Flags:
        if self._environment:
            return self._get_environment_flags_from_document()
        return self._get_environment_flags_from_api()

    def get_identity_flags(
        self, identifier: str, traits: typing.Dict[str, typing.Any] = None
    ) -> Flags:
        traits = traits or {}
        if self._environment:
            return self._get_identity_flags_from_document(identifier, traits)
        return self._get_identity_flags_from_api(identifier, traits)

    def delete_identity_trait(self, identifier: str, trait_key: str) -> None:
        # TODO: set the trait value to None and send to the API
        pass

    def update_environment(self):
        self._environment = self._get_environment_from_api()

    def _get_environment_from_api(self) -> EnvironmentModel:
        environment_data = self._get_json_response(self.environment_url, method="GET")
        return build_environment_model(environment_data)

    def _get_environment_flags_from_document(self) -> Flags:
        return Flags.from_feature_state_models(
            feature_states=engine.get_environment_feature_states(self._environment),
            analytics_processor=self._analytics_processor,
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
        )

    def _get_environment_flags_from_api(self) -> Flags:
        return Flags.from_api_flags(
            flags=self._get_json_response(url=self.environment_flags_url, method="GET"),
            analytics_processor=self._analytics_processor,
        )

    def _get_identity_flags_from_api(
        self, identifier: str, traits: typing.Dict[str, typing.Any]
    ) -> Flags:
        data = {
            "identifier": identifier,
            "traits": [
                {"trait_key": key, "trait_value": value}
                for key, value in traits.items()
            ],
        }
        json_response = self._get_json_response(
            url=self.identities_url, method="POST", body=data
        )
        return Flags.from_api_flags(
            flags=json_response["flags"], analytics_processor=self._analytics_processor
        )

    def _get_json_response(self, url: str, method: str, body: dict = None):
        try:
            request_method = getattr(self.session, method.lower())
            response = request_method(url, json=body, timeout=self.request_timeout)
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
