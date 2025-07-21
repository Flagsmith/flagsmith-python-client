import json
import sys
import time
import typing
import uuid

import pytest
import requests
import responses
from flag_engine.environments.models import EnvironmentModel
from flag_engine.features.models import FeatureModel, FeatureStateModel
from pytest_mock import MockerFixture
from responses import matchers

from flagsmith import Flagsmith, __version__
from flagsmith.exceptions import (
    FlagsmithAPIError,
    FlagsmithFeatureDoesNotExistError,
)
from flagsmith.models import DefaultFlag, Flags
from flagsmith.offline_handlers import BaseOfflineHandler


def test_flagsmith_starts_polling_manager_on_init_if_enabled(
    mocker: MockerFixture, server_api_key: str, requests_session_response_ok: None
) -> None:
    # Given
    mock_polling_manager = mocker.MagicMock()
    mocker.patch(
        "flagsmith.flagsmith.EnvironmentDataPollingManager",
        return_value=mock_polling_manager,
    )

    # When
    Flagsmith(environment_key=server_api_key, enable_local_evaluation=True)

    # Then
    mock_polling_manager.start.assert_called_once()


@responses.activate()
def test_update_environment_sets_environment(
    flagsmith: Flagsmith, environment_json: str, environment_model: EnvironmentModel
) -> None:
    # Given
    responses.add(method="GET", url=flagsmith.environment_url, body=environment_json)
    assert flagsmith._environment is None

    # When
    flagsmith.update_environment()

    # Then
    assert flagsmith._environment is not None
    assert flagsmith._environment == environment_model


@responses.activate()
def test_get_environment_flags_calls_api_when_no_local_environment(
    api_key: str, flagsmith: Flagsmith, flags_json: str
) -> None:
    # Given
    responses.add(method="GET", url=flagsmith.environment_flags_url, body=flags_json)

    # When
    all_flags = flagsmith.get_environment_flags().all_flags()

    # Then
    assert len(responses.calls) == 1
    assert responses.calls[0].request.headers["X-Environment-Key"] == api_key

    # Taken from hard coded values in tests/data/flags.json
    assert all_flags[0].enabled is True
    assert all_flags[0].value == "some-value"
    assert all_flags[0].feature_name == "some_feature"


@responses.activate()
def test_get_environment_flags_uses_local_environment_when_available(
    flagsmith: Flagsmith, environment_model: EnvironmentModel
) -> None:
    # Given
    flagsmith._environment = environment_model
    flagsmith.enable_local_evaluation = True

    # When
    all_flags = flagsmith.get_environment_flags().all_flags()

    # Then
    assert len(responses.calls) == 0
    assert len(all_flags) == 1
    assert all_flags[0].feature_name == environment_model.feature_states[0].feature.name
    assert all_flags[0].enabled == environment_model.feature_states[0].enabled
    assert all_flags[0].value == environment_model.feature_states[0].get_value()


@responses.activate()
def test_get_identity_flags_calls_api_when_no_local_environment_no_traits(
    flagsmith: Flagsmith, identities_json: str
) -> None:
    # Given
    responses.add(method="POST", url=flagsmith.identities_url, body=identities_json)
    identifier = "identifier"

    # When
    identity_flags = flagsmith.get_identity_flags(identifier=identifier).all_flags()

    # Then
    body = responses.calls[0].request.body
    if isinstance(body, bytes):
        # Decode 'body' from bytes to string if it is in bytes format.
        body = body.decode()
    assert body == json.dumps({"identifier": identifier, "traits": []})

    # Taken from hard coded values in tests/data/identities.json
    assert identity_flags[0].enabled is True
    assert identity_flags[0].value == "some-value"
    assert identity_flags[0].feature_name == "some_feature"


@responses.activate()
def test_get_identity_flags_calls_api_when_no_local_environment_with_traits(
    flagsmith: Flagsmith, identities_json: str
) -> None:
    # Given
    responses.add(method="POST", url=flagsmith.identities_url, body=identities_json)
    identifier = "identifier"
    traits = {"some_trait": "some_value"}

    # When
    identity_flags = flagsmith.get_identity_flags(identifier=identifier, traits=traits)

    # Then
    body = responses.calls[0].request.body
    if isinstance(body, bytes):
        # Decode 'body' from bytes to string if it is in bytes format.
        body = body.decode()
    assert body == json.dumps(
        {
            "identifier": identifier,
            "traits": [{"trait_key": k, "trait_value": v} for k, v in traits.items()],
        }
    )

    # Taken from hard coded values in tests/data/identities.json
    assert identity_flags.all_flags()[0].enabled is True
    assert identity_flags.all_flags()[0].value == "some-value"
    assert identity_flags.all_flags()[0].feature_name == "some_feature"


@responses.activate()
def test_get_identity_flags_uses_local_environment_when_available(
    flagsmith: Flagsmith, environment_model: EnvironmentModel, mocker: MockerFixture
) -> None:
    # Given
    flagsmith._environment = environment_model
    flagsmith.enable_local_evaluation = True
    mock_engine = mocker.patch("flagsmith.flagsmith.engine")

    feature_state = FeatureStateModel(
        feature=FeatureModel(id=1, name="some_feature", type="STANDARD"),
        enabled=True,
        featurestate_uuid=str(uuid.uuid4()),
    )
    mock_engine.get_identity_feature_states.return_value = [feature_state]

    # When
    identity_flags = flagsmith.get_identity_flags(
        "identifier", traits={"some_trait": "some_value"}
    ).all_flags()

    # Then
    mock_engine.get_identity_feature_states.assert_called_once()
    assert identity_flags[0].enabled is feature_state.enabled
    assert identity_flags[0].value == feature_state.get_value()


@responses.activate()
def test_get_identity_flags__transient_identity__calls_expected(
    flagsmith: Flagsmith,
    identities_json: str,
) -> None:
    # Given
    responses.add(
        method="POST",
        url=flagsmith.identities_url,
        body=identities_json,
        match=[
            matchers.json_params_matcher(
                {
                    "identifier": "identifier",
                    "traits": [
                        {"trait_key": "some_trait", "trait_value": "some_value"}
                    ],
                    "transient": True,
                }
            )
        ],
    )

    # When & Then
    flagsmith.get_identity_flags(
        "identifier",
        traits={"some_trait": "some_value"},
        transient=True,
    )


@responses.activate()
def test_get_identity_flags__transient_trait_keys__calls_expected(
    flagsmith: Flagsmith,
    identities_json: str,
    environment_model: EnvironmentModel,
    mocker: MockerFixture,
) -> None:
    # Given
    responses.add(
        method="POST",
        url=flagsmith.identities_url,
        body=identities_json,
        match=[
            matchers.json_params_matcher(
                {
                    "identifier": "identifier",
                    "traits": [
                        {
                            "trait_key": "some_trait",
                            "trait_value": "some_value",
                            "transient": True,
                        }
                    ],
                },
            )
        ],
    )

    # When & Then
    flagsmith.get_identity_flags(
        "identifier",
        traits={"some_trait": {"value": "some_value", "transient": True}},
    )


def test_request_connection_error_raises_flagsmith_api_error(
    mocker: MockerFixture, api_key: str
) -> None:
    """
    Test the behaviour when session.<method> raises a ConnectionError. Note that this
    does not account for the fact that we are using retries. Since this is a standard
    library, we leave this untested. It is assumed that, once the retries are exhausted,
    the requests library raises requests.ConnectionError.
    """

    # Given
    mock_session = mocker.MagicMock()
    mocker.patch("flagsmith.flagsmith.requests.Session", return_value=mock_session)

    flagsmith = Flagsmith(environment_key=api_key)

    mock_session.get.side_effect = requests.ConnectionError

    # When
    with pytest.raises(FlagsmithAPIError):
        flagsmith.get_environment_flags()

    # Then
    # expected exception raised


@responses.activate()
def test_non_200_response_raises_flagsmith_api_error(flagsmith: Flagsmith) -> None:
    # Given
    responses.add(url=flagsmith.environment_flags_url, method="GET", status=400)

    # When
    with pytest.raises(FlagsmithAPIError):
        flagsmith.get_environment_flags()

    # Then
    # expected exception raised


@pytest.mark.parametrize(
    "settings, expected_timeout",
    [
        ({"request_timeout_seconds": 5}, 5),  # Arbitrary timeout
        ({"request_timeout_seconds": None}, None),  # No timeout is forced
        ({}, 10),  # Default timeout
    ],
)
def test_request_times_out_according_to_setting(
    mocker: MockerFixture,
    api_key: str,
    settings: typing.Dict[str, typing.Any],
    expected_timeout: typing.Optional[int],
) -> None:
    # Given
    session = mocker.patch("flagsmith.flagsmith.requests.Session").return_value
    flagsmith = Flagsmith(
        environment_key=api_key,
        enable_local_evaluation=False,
        **settings,
    )

    # When
    flagsmith.get_environment_flags()

    # Then
    session.get.assert_called_once_with(
        "https://edge.api.flagsmith.com/api/v1/flags/",
        json=None,
        timeout=expected_timeout,
    )


@responses.activate()
def test_default_flag_is_used_when_no_environment_flags_returned(api_key: str) -> None:
    # Given
    feature_name = "some_feature"

    # a default flag and associated handler
    default_flag = DefaultFlag(True, "some-default-value")

    def default_flag_handler(feature_name: str) -> DefaultFlag:
        return default_flag

    flagsmith = Flagsmith(
        environment_key=api_key, default_flag_handler=default_flag_handler
    )

    # and we mock the API to return an empty list of flags
    responses.add(
        url=flagsmith.environment_flags_url, method="GET", body=json.dumps([])
    )

    # When
    flags = flagsmith.get_environment_flags()

    # Then
    # the data from the default flag is used
    flag = flags.get_flag(feature_name)
    assert flag.is_default
    assert flag.enabled == default_flag.enabled
    assert flag.value == default_flag.value


@responses.activate()
def test_default_flag_is_not_used_when_environment_flags_returned(
    api_key: str, flags_json: str
) -> None:
    # Given
    feature_name = "some_feature"

    # a default flag and associated handler
    default_flag = DefaultFlag(True, "some-default-value")

    def default_flag_handler(feature_name: str) -> DefaultFlag:
        return default_flag

    flagsmith = Flagsmith(
        environment_key=api_key, default_flag_handler=default_flag_handler
    )

    # but we mock the API to return an actual value for the same feature
    responses.add(url=flagsmith.environment_flags_url, method="GET", body=flags_json)

    # When
    flags = flagsmith.get_environment_flags()

    # Then
    # the data from the API response is used, not the default flag
    flag = flags.get_flag(feature_name)
    assert not flag.is_default
    assert flag.value != default_flag.value
    assert flag.value == "some-value"  # hard coded value in tests/data/flags.json


@responses.activate()
def test_default_flag_is_used_when_no_identity_flags_returned(api_key: str) -> None:
    # Given
    feature_name = "some_feature"

    # a default flag and associated handler
    default_flag = DefaultFlag(True, "some-default-value")

    def default_flag_handler(feature_name: str) -> DefaultFlag:
        return default_flag

    flagsmith = Flagsmith(
        environment_key=api_key, default_flag_handler=default_flag_handler
    )

    # and we mock the API to return an empty list of flags
    response_data: typing.Mapping[str, typing.Sequence[typing.Any]] = {
        "flags": [],
        "traits": [],
    }
    responses.add(
        url=flagsmith.identities_url, method="POST", body=json.dumps(response_data)
    )

    # When
    flags = flagsmith.get_identity_flags(identifier="identifier")

    # Then
    # the data from the default flag is used
    flag = flags.get_flag(feature_name)
    assert flag.is_default
    assert flag.enabled == default_flag.enabled
    assert flag.value == default_flag.value


@responses.activate()
def test_default_flag_is_not_used_when_identity_flags_returned(
    api_key: str, identities_json: str
) -> None:
    # Given
    feature_name = "some_feature"

    # a default flag and associated handler
    default_flag = DefaultFlag(True, "some-default-value")

    def default_flag_handler(feature_name: str) -> DefaultFlag:
        return default_flag

    flagsmith = Flagsmith(
        environment_key=api_key, default_flag_handler=default_flag_handler
    )

    # but we mock the API to return an actual value for the same feature
    responses.add(url=flagsmith.identities_url, method="POST", body=identities_json)

    # When
    flags = flagsmith.get_identity_flags(identifier="identifier")

    # Then
    # the data from the API response is used, not the default flag
    flag = flags.get_flag(feature_name)
    assert not flag.is_default
    assert flag.value != default_flag.value
    assert flag.value == "some-value"  # hard coded value in tests/data/identities.json


def test_default_flags_are_used_if_api_error_and_default_flag_handler_given(
    mocker: MockerFixture,
) -> None:
    # Given
    # a default flag and associated handler
    default_flag = DefaultFlag(True, "some-default-value")

    def default_flag_handler(feature_name: str) -> DefaultFlag:
        return default_flag

    # but we mock the request session to raise a ConnectionError
    mock_session = mocker.MagicMock()
    mocker.patch("flagsmith.flagsmith.requests.Session", return_value=mock_session)
    mock_session.get.side_effect = requests.ConnectionError

    flagsmith = Flagsmith(
        environment_key="some-key", default_flag_handler=default_flag_handler
    )

    # When
    flags = flagsmith.get_environment_flags()

    # Then
    assert flags.get_flag("some-feature") == default_flag


def test_get_identity_segments_no_traits(
    local_eval_flagsmith: Flagsmith, environment_model: EnvironmentModel
) -> None:
    # Given
    identifier = "identifier"

    # When
    segments = local_eval_flagsmith.get_identity_segments(identifier)

    # Then
    assert segments == []


def test_get_identity_segments_with_valid_trait(
    local_eval_flagsmith: Flagsmith, environment_model: EnvironmentModel
) -> None:
    # Given
    identifier = "identifier"
    traits = {"foo": "bar"}  # obtained from data/environment.json

    # When
    segments = local_eval_flagsmith.get_identity_segments(identifier, traits)

    # Then
    assert len(segments) == 1
    assert segments[0].name == "Test segment"  # obtained from data/environment.json


def test_local_evaluation_requires_server_key() -> None:
    with pytest.raises(ValueError):
        Flagsmith(environment_key="not-a-server-key", enable_local_evaluation=True)


def test_initialise_flagsmith_with_proxies() -> None:
    # Given
    proxies = {"https": "https://my.proxy.com/proxy-me"}

    # When
    flagsmith = Flagsmith(environment_key="test-key", proxies=proxies)

    # Then
    assert flagsmith.session.proxies == proxies


def test_offline_mode(environment_model: EnvironmentModel) -> None:
    # Given
    class DummyOfflineHandler(BaseOfflineHandler):
        def get_environment(self) -> EnvironmentModel:
            return environment_model

    # When
    flagsmith = Flagsmith(offline_mode=True, offline_handler=DummyOfflineHandler())

    # Then
    # we can request the flags from the client successfully
    environment_flags: Flags = flagsmith.get_environment_flags()
    assert environment_flags.is_feature_enabled("some_feature") is True

    identity_flags: Flags = flagsmith.get_identity_flags("identity")
    assert identity_flags.is_feature_enabled("some_feature") is True


@responses.activate()
def test_flagsmith_uses_offline_handler_if_set_and_no_api_response(
    mocker: MockerFixture, environment_model: EnvironmentModel
) -> None:
    # Given
    api_url = "http://some.flagsmith.com/api/v1/"
    mock_offline_handler = mocker.MagicMock(spec=BaseOfflineHandler)
    mock_offline_handler.get_environment.return_value = environment_model

    flagsmith = Flagsmith(
        environment_key="some-key",
        api_url=api_url,
        offline_handler=mock_offline_handler,
    )

    responses.get(flagsmith.environment_flags_url, status=500)
    responses.get(flagsmith.identities_url, status=500)

    # When
    environment_flags = flagsmith.get_environment_flags()
    identity_flags = flagsmith.get_identity_flags("identity", traits={})

    # Then
    mock_offline_handler.get_environment.assert_called_once_with()

    assert environment_flags.is_feature_enabled("some_feature") is True
    assert environment_flags.get_feature_value("some_feature") == "some-value"

    assert identity_flags.is_feature_enabled("some_feature") is True
    assert identity_flags.get_feature_value("some_feature") == "some-value"


@responses.activate()
def test_offline_mode__local_evaluation__correct_fallback(
    mocker: MockerFixture,
    environment_model: EnvironmentModel,
    caplog: pytest.LogCaptureFixture,
) -> None:
    # Given
    api_url = "http://some.flagsmith.com/api/v1/"
    mock_offline_handler = mocker.MagicMock(spec=BaseOfflineHandler)
    mock_offline_handler.get_environment.return_value = environment_model

    mocker.patch("flagsmith.flagsmith.EnvironmentDataPollingManager")

    responses.get(api_url + "environment-document/", status=500)

    flagsmith = Flagsmith(
        environment_key="ser.some-key",
        api_url=api_url,
        enable_local_evaluation=True,
        offline_handler=mock_offline_handler,
    )

    # When
    environment_flags = flagsmith.get_environment_flags()
    identity_flags = flagsmith.get_identity_flags("identity", traits={})

    # Then
    mock_offline_handler.get_environment.assert_called_once_with()

    assert environment_flags.is_feature_enabled("some_feature") is True
    assert environment_flags.get_feature_value("some_feature") == "some-value"

    assert identity_flags.is_feature_enabled("some_feature") is True
    assert identity_flags.get_feature_value("some_feature") == "some-value"

    [error_log_record] = caplog.records
    assert error_log_record.levelname == "ERROR"
    assert error_log_record.message == "Error updating environment"


def test_cannot_use_offline_mode_without_offline_handler() -> None:
    with pytest.raises(ValueError) as e:
        # When
        Flagsmith(offline_mode=True, offline_handler=None)

    # Then
    assert (
        e.exconly()
        == "ValueError: offline_handler must be provided to use offline mode."
    )


def test_cannot_use_default_handler_and_offline_handler(mocker: MockerFixture) -> None:
    # When
    with pytest.raises(ValueError) as e:
        Flagsmith(
            offline_handler=mocker.MagicMock(spec=BaseOfflineHandler),
            default_flag_handler=lambda flag_name: DefaultFlag(
                enabled=True, value="foo"
            ),
        )

    # Then
    assert (
        e.exconly()
        == "ValueError: Cannot use both default_flag_handler and offline_handler."
    )


def test_cannot_create_flagsmith_client_in_remote_evaluation_without_api_key() -> None:
    # When
    with pytest.raises(ValueError) as e:
        Flagsmith()

    # Then
    assert e.exconly() == "ValueError: environment_key is required."


def test_stream_not_used_by_default(
    requests_session_response_ok: None, server_api_key: str
) -> None:
    # When
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
    )

    # Then
    assert hasattr(flagsmith, "event_stream_thread") is False


def test_stream_used_when_enable_realtime_updates_is_true(
    requests_session_response_ok: None, server_api_key: str
) -> None:
    # When
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
        enable_realtime_updates=True,
    )

    # Then
    assert hasattr(flagsmith, "event_stream_thread") is True


def test_error_raised_when_realtime_updates_is_true_and_local_evaluation_false(
    requests_session_response_ok: None, server_api_key: str
) -> None:
    with pytest.raises(ValueError):
        Flagsmith(
            environment_key=server_api_key,
            enable_local_evaluation=False,
            enable_realtime_updates=True,
        )


@responses.activate()
def test_flagsmith_client_get_identity_flags__local_evaluation__returns_expected(
    environment_json: str,
    server_api_key: str,
) -> None:
    # Given
    identifier = "overridden-id"

    api_url = "https://mocked.flagsmith.com/api/v1/"
    environment_document_url = f"{api_url}environment-document/"
    responses.add(method="GET", url=environment_document_url, body=environment_json)

    flagsmith = Flagsmith(
        environment_key=server_api_key,
        api_url=api_url,
        enable_local_evaluation=True,
    )
    time.sleep(0.1)

    # When
    flag = flagsmith.get_identity_flags(identifier).get_flag("some_feature")

    # Then
    assert flag.enabled is False
    assert flag.value == "some-overridden-value"


def test_custom_feature_error_raised_when_invalid_feature(
    requests_session_response_ok: None, server_api_key: str
) -> None:
    # Given
    flagsmith = Flagsmith(
        environment_key=server_api_key,
        enable_local_evaluation=True,
    )

    flags = flagsmith.get_environment_flags()

    # Then
    with pytest.raises(FlagsmithFeatureDoesNotExistError):
        # When
        flags.is_feature_enabled("non-existing-feature")


@pytest.mark.parametrize(
    "kwargs,expected_headers",
    [
        (
            {
                "environment_key": "test-key",
                "application_metadata": {"name": "test-app", "version": "1.0.0"},
            },
            {
                "Flagsmith-Application-Name": "test-app",
                "Flagsmith-Application-Version": "1.0.0",
                "X-Environment-Key": "test-key",
            },
        ),
        (
            {
                "environment_key": "test-key",
                "application_metadata": {"name": "test-app"},
            },
            {
                "Flagsmith-Application-Name": "test-app",
                "X-Environment-Key": "test-key",
            },
        ),
        (
            {
                "environment_key": "test-key",
                "application_metadata": {"version": "1.0.0"},
            },
            {
                "Flagsmith-Application-Version": "1.0.0",
                "X-Environment-Key": "test-key",
            },
        ),
        (
            {
                "environment_key": "test-key",
                "application_metadata": {"version": "1.0.0"},
                "custom_headers": {"X-Custom-Header": "CustomValue"},
            },
            {
                "Flagsmith-Application-Version": "1.0.0",
                "X-Environment-Key": "test-key",
                "X-Custom-Header": "CustomValue",
            },
        ),
        (
            {
                "environment_key": "test-key",
                "application_metadata": None,
                "custom_headers": {"X-Custom-Header": "CustomValue"},
            },
            {
                "X-Environment-Key": "test-key",
                "X-Custom-Header": "CustomValue",
            },
        ),
        (
            {"environment_key": "test-key"},
            {
                "X-Environment-Key": "test-key",
            },
        ),
    ],
)
@responses.activate()
def test_flagsmith__init__expected_headers_sent(
    kwargs: typing.Dict[str, typing.Any],
    expected_headers: typing.Dict[str, str],
) -> None:
    # Given
    flagsmith = Flagsmith(**kwargs)
    responses.add(method="GET", url=flagsmith.environment_flags_url, body="{}")

    # When
    flagsmith.get_environment_flags()

    # Then
    headers = responses.calls[0].request.headers
    assert headers == {
        "User-Agent": (
            f"flagsmith-python-client/{__version__} python-requests/{requests.__version__} "
            f"python/{sys.version_info.major}.{sys.version_info.minor}"
        ),
        "Accept-Encoding": "gzip, deflate",
        "Accept": "*/*",
        "Connection": "keep-alive",
        **expected_headers,
    }
