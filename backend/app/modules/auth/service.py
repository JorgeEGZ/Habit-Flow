from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.exceptions import (
    EmailAlreadyTaken,
    InvalidCredentials,
    InvalidRefreshToken,
    RefreshTokenReuse,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.modules.auth import repository as auth_repo
from app.modules.auth.schemas import RegisterIn, TokenPair
from app.modules.users import repository as users_repo
from app.modules.users.models import User


async def register(session, payload: RegisterIn) -> User:
    user = User(
        email=payload.email,
        password_hash=hash_password(payload.password),
        full_name=payload.full_name,
    )
    session.add(user)
    try:
        await session.commit()
    except IntegrityError as exc:
        # The unique constraint on users.email rejects the duplicate. The
        # pre-check by email is intentionally absent — a TOCTOU window
        # between read and write would just bounce to this branch anyway,
        # so we save one round trip in the happy path.
        await session.rollback()
        raise EmailAlreadyTaken() from exc
    await session.refresh(user)
    return user


async def login(session, email: str, password: str) -> TokenPair:
    user = await users_repo.get_by_email(session, email)
    if not user or not verify_password(password, user.password_hash):
        raise InvalidCredentials()
    return await _issue_token_pair(session, user.id)


async def refresh_tokens(session, raw_refresh_token: str) -> TokenPair:
    token_hash = hash_refresh_token(raw_refresh_token)
    record = await auth_repo.get_by_hash(session, token_hash)
    if not record:
        raise InvalidRefreshToken()
    if record.revoked_at is not None:
        # Reuse detected: burn the entire family and force re-login.
        await auth_repo.revoke_all_for_user(session, record.user_id)
        raise RefreshTokenReuse()
    if _to_utc(record.expires_at) <= _utcnow():
        raise InvalidRefreshToken()

    await auth_repo.revoke(session, record)
    return await _issue_token_pair(session, record.user_id)


async def logout(session, raw_refresh_token: str) -> None:
    token_hash = hash_refresh_token(raw_refresh_token)
    record = await auth_repo.get_active_by_hash(session, token_hash)
    if not record:
        return
    await auth_repo.revoke(session, record)


async def _issue_token_pair(session, user_id: uuid.UUID) -> TokenPair:
    settings = get_settings()
    access_token, expires_in = create_access_token(user_id, settings)
    raw_refresh = generate_refresh_token(settings)
    refresh_hash = hash_refresh_token(raw_refresh)
    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
    await auth_repo.create(
        session,
        user_id=user_id,
        token_hash=refresh_hash,
        expires_at=expires_at,
    )
    return TokenPair(
        access_token=access_token,
        refresh_token=raw_refresh,
        expires_in=expires_in,
    )


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _to_utc(value: datetime) -> datetime:
    """Coerce a possibly-naive datetime to a UTC-aware datetime.

    Some backends (notably SQLite) drop tzinfo on round-trip; the application
    always stores UTC, so a naive value is interpreted as UTC.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value
