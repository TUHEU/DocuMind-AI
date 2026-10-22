import time

import pytest

from app.core.security import TokenError, create_access_token, decode_access_token, hash_password, verify_password


def test_password_hash_is_salted_and_verifies():
    h1, h2 = hash_password("Secret123"), hash_password("Secret123")
    assert h1 != h2                                   # random salt
    assert "Secret123" not in h1
    assert verify_password("Secret123", h1)
    assert not verify_password("secret123", h1)


def test_verify_password_rejects_garbage_hash():
    assert not verify_password("x", "not-a-hash")
    assert not verify_password("x", "bcrypt$1$2$3")


def test_token_round_trip():
    payload = decode_access_token(create_access_token("user-1", "ADMIN"))
    assert payload["sub"] == "user-1" and payload["role"] == "ADMIN"


def test_expired_token_is_refused():
    token = create_access_token("u", "ADMIN", expires_in=-5)
    with pytest.raises(TokenError):
        decode_access_token(token)


def test_tampered_token_is_refused():
    head, payload, sig = create_access_token("u", "OPERATOR").split(".")
    forged = create_access_token("u", "ADMIN").split(".")[1]
    with pytest.raises(TokenError):
        decode_access_token(f"{head}.{forged}.{sig}")


def test_alg_none_token_is_refused():
    import base64, json
    b = lambda d: base64.urlsafe_b64encode(json.dumps(d).encode()).rstrip(b"=").decode()
    token = f"{b({'alg': 'none', 'typ': 'JWT'})}.{b({'sub': 'u', 'role': 'ADMIN', 'exp': int(time.time()) + 999})}."
    with pytest.raises(TokenError):
        decode_access_token(token)


def test_garbage_token_is_refused():
    with pytest.raises(TokenError):
        decode_access_token("abc")
