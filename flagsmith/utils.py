import typing


def generate_header_content(
    environment_key: str, headers: typing.Dict[str, str] = None
) -> typing.Dict[str, str]:
    """
    Generates required header content for accessing API

    :param headers: (optional) dictionary of other required header values
    :return: dictionary with required environment header appended to it
    """
    headers = headers or {}

    headers["X-Environment-Key"] = environment_key
    return headers
