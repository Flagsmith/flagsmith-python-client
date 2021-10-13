import logging

import requests

from .analytics import AnalyticsProcessor

logger = logging.getLogger(__name__)

SERVER_URL = "https://api.flagsmith.com/api/v1/"
FLAGS_ENDPOINT = "flags/"
IDENTITY_ENDPOINT = "identities/"
TRAIT_ENDPOINT = "traits/"


class Flagsmith:
    def __init__(
        self, environment_key, api=SERVER_URL, custom_headers=None, request_timeout=None
    ):
        """
        Initialise Flagsmith environment.

        :param environment_key: environment key obtained from the Flagsmith UI
        :param api: (optional) api url to override when using self hosted version
        :param custom_headers: (optional) dict which will be passed in headers for each api call
        :param request_timeout: (optional) request timeout in seconds
        """

        self.environment_key = environment_key
        self.api = api
        self.flags_endpoint = api + FLAGS_ENDPOINT
        self.identities_endpoint = api + IDENTITY_ENDPOINT
        self.traits_endpoint = api + TRAIT_ENDPOINT
        self.custom_headers = custom_headers or {}
        self.request_timeout = request_timeout
        self._analytics_processor = AnalyticsProcessor(
            environment_key, api, self.request_timeout
        )

    def get_flags(self, identity=None):
        """
        Get all flags for the environment or optionally provide an identity within an environment
        to get their flags. Will return overridden identity flags where given and fill in the gaps
        with the default environment flags.

        :param identity: application's unique identifier for the user to check feature states
        :return: list of dictionaries representing feature states for environment / identity
        """
        if identity:
            data = self._get_flags_response(identity=identity)
        else:
            data = self._get_flags_response()

        if data:
            return data
        else:
            logger.error("Failed to get flags for environment.")

    def get_flags_for_user(self, identity):
        """
        Get all flags for a user

        :param identity: application's unique identifier for the user to check feature states
        :return: list of dictionaries representing identities feature states for environment
        """
        return self.get_flags(identity=identity)

    def has_feature(self, feature_name):
        """
        Determine if given feature exists for an environment.

        :param feature_name: name of feature to test existence of
        :return: True if exists, False if not.
        """
        data = self._get_flags_response(feature_name)
        if data:
            feature_id = data["feature"]["id"]
            self._analytics_processor.track_feature(feature_id)
            return True

        return False

    def feature_enabled(self, feature_name, identity=None):
        """
        Get enabled state of given feature for an environment.

        :param feature_name: name of feature to determine if enabled
        :param identity: (optional) application's unique identifier for the user to check feature state
        :return: True / False if feature exists. None otherwise.
        """
        if not feature_name:
            return None

        data = self._get_flags_response(feature_name, identity)

        if not data:
            return None

        feature_id = data["feature"]["id"]
        self._analytics_processor.track_feature(feature_id)

        return data["enabled"]

    def get_value(self, feature_name, identity=None):
        """
        Get value of given feature for an environment.

        :param feature_name: name of feature to determine value of
        :param identity: (optional) application's unique identifier for the user to check feature state
        :return: value of the feature state if feature exists, None otherwise
        """
        if not feature_name:
            return None

        data = self._get_flags_response(feature_name, identity)

        if not data:
            return None
        feature_id = data["feature"]["id"]
        self._analytics_processor.track_feature(feature_id)
        return data["feature_state_value"]

    def get_trait(self, trait_key, identity):
        """
        Get value of given trait for the identity of an environment.

        :param trait_key: key of trait to determine value of (must match 'ID' on flagsmith.com)
        :param identity: application's unique identifier for the user to check feature state
        :return: Trait value. None otherwise.
        """
        if not all([trait_key, identity]):
            return None

        data = self._get_flags_response(identity=identity, feature_name=None)

        traits = data["traits"]
        for trait in traits:
            if trait.get("trait_key") == trait_key:
                return trait.get("trait_value")

    def set_trait(self, trait_key, trait_value, identity):
        """
        Set value of given trait for the identity of an environment. Note that this will lazily create
        a new trait if the trait_key has not been seen before for this identity

        :param trait_key: key of trait
        :param trait_value: value of trait
        :param identity: application's unique identifier for the user to check feature state
        """
        values = [trait_key, trait_value, identity]
        if None in values or "" in values:
            return None

        payload = {
            "identity": {"identifier": identity},
            "trait_key": trait_key,
            "trait_value": trait_value,
        }

        requests.post(
            self.traits_endpoint,
            json=payload,
            headers=self._generate_header_content(self.custom_headers),
            timeout=self.request_timeout,
        )

    def _get_flags_response(self, feature_name=None, identity=None):
        """
        Private helper method to hit the flags endpoint

        :param feature_name: name of feature to determine value of (must match 'ID' on flagsmith.com)
        :param identity: (optional) application's unique identifier for the user to check feature state
        :return: data returned by API if successful, None if not.
        """
        params = {"feature": feature_name} if feature_name else {}

        try:
            if identity:
                params["identifier"] = identity
                response = requests.get(
                    self.identities_endpoint,
                    params=params,
                    headers=self._generate_header_content(self.custom_headers),
                    timeout=self.request_timeout,
                )
            else:
                response = requests.get(
                    self.flags_endpoint,
                    params=params,
                    headers=self._generate_header_content(self.custom_headers),
                    timeout=self.request_timeout,
                )

            if response.status_code == 200:
                data = response.json()
                if data:
                    return data
                else:
                    logger.error("API didn't return any data")
                    return None
            else:
                return None

        except Exception as e:
            logger.error(
                "Got error getting response from API. Error message was %s" % e
            )
            return None

    def _generate_header_content(self, headers=None):
        """
        Generates required header content for accessing API

        :param headers: (optional) dictionary of other required header values
        :return: dictionary with required environment header appended to it
        """
        headers = headers or {}

        headers["X-Environment-Key"] = self.environment_key
        return headers
