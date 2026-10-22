"""Password hashing and signed access tokens, using only the Python standard library.

Why standard library: it installs nothing extra on a locked-down PC.
- Passwords: scrypt with a random salt (memory-hard), compared in constant time.
- Tokens: JWT, algorithm HS256, with an expiry claim.
"""
import base64
import hashlib
import hmac
import json
import os
import time

from app.core.config import get_settings


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode()


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


# ---------------- passwords ----------------
def hash_password(password: str) -> str:
    n = get_settings().password_scrypt_n
    salt = os.urandom(16)
    digest = hashlib.scrypt(password.encode(), salt=salt, n=n, r=8, p=1, dklen=32)
    return f"scrypt${n}${_b64e(salt)}${_b64e(digest)}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, salt, digest = stored.split("$")
        if scheme != "scrypt":
            return False
        expected = _b64d(digest)
        got = hashlib.scrypt(password.encode(), salt=_b64d(salt), n=int(n), r=8, p=1, dklen=len(expected))
        return hmac.compare_digest(got, expected)
    except Exception:
        return False


# A fixed hash used when the e-mail is unknown, so timing does not reveal which e-mails exist.
_DUMMY_HASH: str | None = None


def burn_password_check(password: str) -> None:
    global _DUMMY_HASH
    if _DUMMY_HASH is None:
        _DUMMY_HASH = hash_password("dummy-password-for-timing")
    verify_password(password, _DUMMY_HASH)


# ---------------- tokens ----------------
class TokenError(Exception):
    pass


def create_access_token(user_id: str, role: str, expires_in: int | None = None) -> str:
    s = get_settings()
    now = int(time.time())
    header = {"alg": "HS256", "typ": "JWT"}
    payload = {"sub": user_id, "role": role, "iat": now, "exp": now + (expires_in or s.jwt_expire_seconds)}
    signing = f"{_b64e(json.dumps(header, separators=(',', ':')).encode())}.{_b64e(json.dumps(payload, separators=(',', ':')).encode())}"
    sig = hmac.new(s.jwt_secret.encode(), signing.encode(), hashlib.sha256).digest()
    return f"{signing}.{_b64e(sig)}"


def decode_access_token(token: str) -> dict:
    s = get_settings()
    try:
        head_b64, payload_b64, sig_b64 = token.split(".")
        header = json.loads(_b64d(head_b64))
        if header.get("alg") != "HS256":          # refuse "none" and any other algorithm
            raise TokenError("bad algorithm")
        signing = f"{head_b64}.{payload_b64}"
        expected = hmac.new(s.jwt_secret.encode(), signing.encode(), hashlib.sha256).digest()
        if not hmac.compare_digest(expected, _b64d(sig_b64)):
            raise TokenError("bad signature")
        payload = json.loads(_b64d(payload_b64))
    except TokenError:
        raise
    except Exception as exc:
        raise TokenError("malformed token") from exc
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("expired")
    if not payload.get("sub"):
        raise TokenError("no subject")
    return payload
