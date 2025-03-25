import hashlib
import hmac
from typing import Union


def generate_signature(
    request_body: Union[str, bytes],
    shared_secret: str,
) -> str:
    """Generates a signature for a webhook request body using HMAC-SHA256.

    :param request_body: The raw request body, as string or bytes.
    :param shared_secret: The shared secret configured for this specific webhook.
    :return: The hex-encoded signature.
    """
    if isinstance(request_body, str):
        request_body = request_body.encode()

    shared_secret_bytes = shared_secret.encode()

    return hmac.new(
        key=shared_secret_bytes,
        msg=request_body,
        digestmod=hashlib.sha256,
    ).hexdigest()


def verify_signature(
    request_body: Union[str, bytes],
    received_signature: str,
    shared_secret: str,
) -> bool:
    """Verifies a webhook's signature to determine if the request was sent by Flagsmith.

    :param request_body: The raw request body, as string or bytes.
    :param received_signature: The signature as received in the X-Flagsmith-Signature request header.
    :param shared_secret: The shared secret configured for this specific webhook.
    :return: True if the signature is valid, False otherwise.
    """
    expected_signature = generate_signature(request_body, shared_secret)
    return hmac.compare_digest(expected_signature, received_signature)
