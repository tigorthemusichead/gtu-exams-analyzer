"""Unit tests for auth_service: hashing and JWT."""

import pytest
from datetime import timedelta

import jwt

from app.services.auth_service import hash_password, verify_password, create_token, decode_token


def test_hash_password_returns_string():
    h = hash_password("secret")
    assert isinstance(h, str)
    assert len(h) > 20


def test_verify_password_correct():
    h = hash_password("mypassword")
    assert verify_password("mypassword", h) is True


def test_verify_password_wrong():
    h = hash_password("mypassword")
    assert verify_password("wrong", h) is False


def test_create_and_decode_token():
    payload = {"sub": "42", "role": "teacher"}
    token = create_token(payload, timedelta(hours=1))
    decoded = decode_token(token)
    assert decoded["sub"] == "42"
    assert decoded["role"] == "teacher"
    assert "exp" in decoded


def test_decode_expired_token():
    token = create_token({"sub": "1"}, timedelta(seconds=-1))
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(token)


def test_decode_invalid_token():
    with pytest.raises(jwt.InvalidTokenError):
        decode_token("not.a.token")
