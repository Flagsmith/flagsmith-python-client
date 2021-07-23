import json
import logging
import os
from unittest import TestCase, mock

from flagsmith import Flagsmith

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

TEST_API_URL = "https://test.bullet-train.io/api"
TEST_IDENTIFIER = "test-identity"
TEST_FEATURE = "test-feature"


class MockResponse:
    def __init__(self, data, status_code):
        self.json_data = json.loads(data)
        self.status_code = status_code

    def json(self):
        return self.json_data


def mock_response(filename, *args, status=200, **kwargs):
    print("Hit URL %s with params" % args[0], kwargs.get("params"))
    dir_path = os.path.dirname(os.path.realpath(__file__))
    with open(os.path.join(dir_path, filename), "rt") as f:
        return MockResponse(f.read(), status)


def mocked_get_specific_feature_flag_enabled(*args, **kwargs):
    return mock_response(
        "data/get-flag-for-specific-feature-enabled.json", *args, **kwargs
    )


def mocked_get_specific_feature_flag_disabled(*args, **kwargs):
    return mock_response(
        "data/get-flag-for-specific-feature-disabled.json", *args, **kwargs
    )


def mocked_get_specific_feature_flag_not_found(*args, **kwargs):
    return mock_response("data/not-found.json", *args, status=404, **kwargs)


def mocked_get_value(*args, **kwargs):
    return mock_response("data/get-value-for-specific-feature.json", *args, **kwargs)


def mocked_get_identity_flags_with_trait(*args, **kwargs):
    return mock_response("data/get-identity-flags-with-trait.json", *args, **kwargs)


def mocked_get_identity_flags_without_trait(*args, **kwargs):
    return mock_response("data/get-identity-flags-without-trait.json", *args, **kwargs)


class FlagsmithTestCase(TestCase):
    test_environment_key = "test-env-key"

    def setUp(self) -> None:
        self.bt = Flagsmith(environment_id=self.test_environment_key, api=TEST_API_URL)

    @mock.patch(
        "flagsmith.flagsmith.requests.get",
        side_effect=mocked_get_specific_feature_flag_enabled,
    )
    def test_has_feature_returns_true_if_feature_returned(self, mock_get):
        # When
        result = self.bt.has_feature(TEST_FEATURE)

        # Then
        assert result

    @mock.patch(
        "flagsmith.flagsmith.requests.get",
        side_effect=mocked_get_specific_feature_flag_not_found,
    )
    def test_has_feature_returns_false_if_feature_not_returned(self, mock_get):
        # When
        result = self.bt.has_feature(TEST_FEATURE)

        # Then
        assert not result

    @mock.patch(
        "flagsmith.flagsmith.requests.get",
        side_effect=mocked_get_specific_feature_flag_enabled,
    )
    def test_feature_enabled_returns_true_if_feature_enabled(self, mock_get):
        # When
        result = self.bt.feature_enabled(TEST_FEATURE)

        # Then
        assert result

    @mock.patch(
        "flagsmith.flagsmith.requests.get",
        side_effect=mocked_get_specific_feature_flag_disabled,
    )
    def test_feature_enabled_returns_true_if_feature_disabled(self, mock_get):
        # When
        result = self.bt.feature_enabled(TEST_FEATURE)

        # Then
        assert not result

    @mock.patch("flagsmith.flagsmith.requests.get", side_effect=mocked_get_value)
    def test_get_value_returns_value_for_environment_if_feature_exists(self, mock_get):
        # When
        result = self.bt.get_value(TEST_FEATURE)

        # Then
        assert result == "Test value"

    @mock.patch(
        "flagsmith.flagsmith.requests.get",
        side_effect=mocked_get_specific_feature_flag_not_found,
    )
    def test_get_value_returns_None_for_environment_if_feature_does_not_exist(
        self, mock_get
    ):
        # When
        result = self.bt.get_value(TEST_FEATURE)

        # Then
        assert result is None

    @mock.patch(
        "flagsmith.flagsmith.requests.get",
        side_effect=mocked_get_identity_flags_with_trait,
    )
    def test_get_trait_returns_trait_value_if_trait_key_exists(self, mock_get):
        # When
        result = self.bt.get_trait("trait_key", TEST_IDENTIFIER)

        # Then
        assert result == "trait_value"

    @mock.patch(
        "flagsmith.flagsmith.requests.get",
        side_effect=mocked_get_identity_flags_without_trait,
    )
    def test_get_trait_returns_None_if_trait_key_does_not_exist(self, mock_get):
        # When
        result = self.bt.get_trait("trait_key", TEST_IDENTIFIER)

        # Then
        assert result is None
