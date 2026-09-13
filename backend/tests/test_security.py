import time

import pytest

from app.core.security import (
    InvalidTokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_is_not_plaintext_and_verifies_correctly():
    hashed = hash_password("correct-horse-battery-staple")
    assert hashed != "correct-horse-battery-staple"
    assert verify_password("correct-horse-battery-staple", hashed)


def test_password_verify_rejects_wrong_password():
    hashed = hash_password("correct-horse-battery-staple")
    assert not verify_password("wrong-password", hashed)


def test_access_token_round_trips_subject():
    user_id = "12345678-1234-1234-1234-123456789012"
    token = create_access_token(user_id)
    assert decode_token(token, expected_type="access") == user_id


def test_refresh_token_round_trips_subject():
    user_id = "abcdefab-abcd-abcd-abcd-abcdefabcdef"
    token = create_refresh_token(user_id)
    assert decode_token(token, expected_type="refresh") == user_id


def test_access_token_rejected_when_decoded_as_refresh():
    token = create_access_token("some-user-id")
    with pytest.raises(InvalidTokenError):
        decode_token(token, expected_type="refresh")


def test_garbage_token_raises_invalid_token_error():
    with pytest.raises(InvalidTokenError):
        decode_token("this.is.not.a.valid.jwt", expected_type="access")


def test_tampered_token_is_rejected():
    token = create_access_token("some-user-id")
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(InvalidTokenError):
        decode_token(tampered, expected_type="access")
