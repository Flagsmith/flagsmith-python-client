import json

from flagsmith.webhooks import generate_signature, verify_signature


def test_generate_signature():
    # Given
    request_body = json.dumps({"data": {"foo": 123}})
    shared_secret = "shh"

    # When
    signature = generate_signature(request_body, shared_secret)

    # Then
    assert isinstance(signature, str)
    assert len(signature) == 64  # SHA-256 hex digest is 64 characters


def test_verify_signature_valid():
    # Given
    request_body = json.dumps({"data": {"foo": 123}})
    shared_secret = "shh"

    # When
    signature = generate_signature(request_body, shared_secret)

    # Then
    assert verify_signature(
        request_body=request_body,
        received_signature=signature,
        shared_secret=shared_secret,
    )
    # Test with bytes instead of str
    assert verify_signature(
        request_body=request_body.encode(),
        received_signature=signature,
        shared_secret=shared_secret,
    )


def test_verify_signature_invalid():
    # Given
    request_body = json.dumps({"event": "flag_updated", "data": {"id": 123}})

    # Then
    assert not verify_signature(
        request_body=request_body,
        received_signature="bad",
        shared_secret="?",
    )
