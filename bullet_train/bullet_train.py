import requests

SERVER_URL = 'https://api.bullet-train.io/api'
FLAGS_ENDPOINT = '{}/v1/flags/'


class BulletTrain:
    def __init__(self, environment_id, api=SERVER_URL):
        """
        Initialise bullet train environment.

        :param environment_id: environment key obtained from bullet train UI
        :param api: (optional) api url to override when using self hosted version
        """
        self.environment_id = environment_id
        self.api = api
        self.flags_endpoint = FLAGS_ENDPOINT.format(api)

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
            print("Failed to get flags for environment.")

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
            return True

        return False

    def feature_enabled(self, feature_name, identity=None):
        """
        Get enabled state of given feature for an environment.

        :param feature_name: name of feature to determine if enabled (must match 'ID' on bullet-train.io)
        :param identity: (optional) application's unique identifier for the user to check feature state
        :return: True / False if feature exists. None otherwise.
        """
        if not feature_name:
            return None

        data = self._get_flags_response(feature_name, identity)

        if data:
            return data['enabled']
        else:
            return None

    def get_value(self, feature_name, identity=None):
        """
        Get value of given feature for an environment.

        :param feature_name: name of feature to determine value of (must match 'ID' on bullet-train.io)
        :param identity: (optional) application's unique identifier for the user to check feature state
        :return: True / False if feature exists. None otherwise.
        """
        if not feature_name:
            return None

        data = self._get_flags_response(feature_name, identity)

        if data:
            return data['feature_state_value']
        else:
            return None

    def _get_flags_response(self, feature_name=None, identity=None):
        """
        Private helper method to hit the flags endpoint

        :param feature_name: name of feature to determine value of (must match 'ID' on bullet-train.io)
        :param identity: (optional) application's unique identifier for the user to check feature state
        :return: data returned by API if successful, None if not.
        """
        params = {"feature": feature_name} if feature_name else {}

        try:
            if identity:
                response = requests.get(self.flags_endpoint + identity, params=params,
                                        headers=self._generate_header_content())
            else:
                response = requests.get(self.flags_endpoint, params=params,
                                        headers=self._generate_header_content())

            if response.status_code == 200:
                data = response.json()
                if data:
                    return data
                else:
                    print("API didn't return any data")
                    return None
            else:
                return None

        except Exception as e:
            print("Got error getting response from API. Error message was " + e.message)
            return None

    def _generate_header_content(self, headers={}):
        """
        Generates required header content for accessing API

        :param headers: (optional) dictionary of other required header values
        :return: dictionary with required environment header appended to it
        """
        headers['X-Environment-Key'] = self.environment_id
        return headers
