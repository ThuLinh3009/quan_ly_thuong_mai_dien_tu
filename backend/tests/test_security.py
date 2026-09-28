import jwt
import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    hash_token,
    verify_password,
)


def test_hash_password_roundtrip():
    hashed = hash_password("Str0ngPass!")
    assert hashed != "Str0ngPass!"
    assert verify_password("Str0ngPass!", hashed)
    assert not verify_password("wrong-password", hashed)


def test_verify_password_rejects_garbage_hash():
    assert not verify_password("anything", "not-a-bcrypt-hash")


def test_access_token_roundtrip():
    token = create_access_token(user_id=42, role="customer")
    payload = decode_token(token)
    assert payload["sub"] == "42"
    assert payload["role"] == "customer"
    assert payload["type"] == "access"


def test_refresh_token_roundtrip():
    token, jti, expires_at = create_refresh_token(user_id=7, role="admin")
    payload = decode_token(token)
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti
    assert expires_at.tzinfo is not None


def test_decode_token_rejects_tampered_signature():
    token = create_access_token(user_id=1, role="staff")
    with pytest.raises(jwt.PyJWTError):
        decode_token(token + "tampered")


def test_hash_token_is_deterministic():
    assert hash_token("same-value") == hash_token("same-value")
    assert hash_token("value-a") != hash_token("value-b")
