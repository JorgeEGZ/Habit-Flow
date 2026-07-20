from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from base64 import urlsafe_b64encode
from datetime import datetime, timedelta, timezone
from typing import Any

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from jose import JWTError, jwt

from app.core.config import Settings, get_settings
from app.core.exceptions import AuthenticationRequired, InvalidCredentials

_password_hasher = PasswordHasher()


def hash_password(plain: str) -> str:
    return _password_hasher.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    try:
        _password_hasher.verify(hashed, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False
    return True


def _derive_key(settings: Settings, info: bytes) -> bytes:
    base = settings.secret_key.encode("utf-8")
    derived = hmac.new(base, info, hashlib.sha256).digest()
    return urlsafe_b64encode(derived)


def _access_key(settings: Settings) -> str:
    return _derive_key(settings, b"habitflow.access").decode("ascii")


def _refresh_key(settings: Settings) -> str:
    return _derive_key(settings, b"habitflow.refresh").decode("ascii")


def create_access_token(user_id: uuid.UUID, settings: Settings | None = None) -> tuple[str, int]:
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expires_in = settings.access_token_expire_minutes * 60
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=expires_in)).timestamp()),
        "type": "access",
    }
    token = jwt.encode(payload, _access_key(settings), algorithm=settings.jwt_algorithm)
    return token, expires_in


def decode_access_token(token: str, settings: Settings | None = None) -> uuid.UUID:
    settings = settings or get_settings()
    try:
        payload = jwt.decode(token, _access_key(settings), algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise InvalidCredentials("Invalid access token.") from exc

    if payload.get("type") != "access":
        raise InvalidCredentials("Wrong token type.")

    sub = payload.get("sub")
    if not sub:
        raise InvalidCredentials("Token missing subject.")
    try:
        return uuid.UUID(sub)
    except (TypeError, ValueError) as exc:
        raise InvalidCredentials("Invalid subject.") from exc


def generate_refresh_token(settings: Settings | None = None) -> str:
    """Return a 256-bit cryptographically random refresh token, URL-safe encoded.

    Output is 43 chars, well under the 64-char column we store the SHA-256
    hex digest in. The plaintext is returned to the caller once and never
    persisted — only its SHA-256 hex digest is.
    """
    return secrets.token_urlsafe(32)


def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def require_current_user_id(token: str | None, settings: Settings | None = None) -> uuid.UUID:
    if not token:
        raise AuthenticationRequired("Missing access token.")
    return decode_access_token(token, settings)
