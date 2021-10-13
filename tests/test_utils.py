from flagsmith.utils import generate_header_content


def test_generate_header_content_returns_dict_with_api_key():
    # Given
    environment_key = "api_key"

    # When
    headers = generate_header_content(environment_key)

    # Then
    assert headers == {"X-Environment-Key": environment_key}


def test_generate_header_content_appends_headers_to_header_arg_if_present():
    # Given
    environment_key = "api_key"
    given_headers = {"Host": "test"}
    # When
    headers = generate_header_content(environment_key, given_headers)

    # Then
    assert headers == {"X-Environment-Key": environment_key, **given_headers}
