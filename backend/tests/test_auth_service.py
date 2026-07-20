"""Unit tests for app.modules.auth.service."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    EmailAlreadyTaken,
    InvalidCredentials,
    InvalidRefreshToken,
    RefreshTokenReuse,
)
from app.core.security import hash_refresh_token
from app.modules.auth import repository as auth_repo
from app.modules.auth.schemas import RegisterIn
from app.modules.auth.service import login, logout, refresh_tokens, register


pytestmark = pytest.mark.asyncio


async def test_register_creates_user(session: AsyncSession) -> None:
    user = await register(
        session,
        RegisterIn(email="alice@example.com", password="correcthorse", full_name="Alice"),
    )
    assert user.id is not None
    assert user.email == "alice@example.com"
    assert user.full_name == "Alice"
    assert user.password_hash != "correcthorse"  # hashed


async def test_register_rejects_duplicate_email(session: AsyncSession) -> None:
    await register(
        session,
        RegisterIn(email="bob@example.com", password="correcthorse"),
    )
    with pytest.raises(EmailAlreadyTaken):
        await register(
            session,
            RegisterIn(email="bob@example.com", password="anotherpw1"),
        )


async def test_login_returns_token_pair_for_valid_credentials(session: AsyncSession) -> None:
    await register(
        session,
        RegisterIn(email="carol@example.com", password="correcthorse"),
    )
    pair = await login(session, "carol@example.com", "correcthorse")
    assert pair.access_token
    assert pair.refresh_token
    assert pair.token_type == "bearer"
    assert pair.expires_in > 0


async def test_login_rejects_wrong_password(session: AsyncSession) -> None:
    await register(
        session,
        RegisterIn(email="dave@example.com", password="correcthorse"),
    )
    with pytest.raises(InvalidCredentials):
        await login(session, "dave@example.com", "wrongpassword")


async def test_login_rejects_unknown_email(session: AsyncSession) -> None:
    with pytest.raises(InvalidCredentials):
        await login(session, "nobody@example.com", "irrelevant")


async def test_refresh_rotates_and_revokes_old_token(session: AsyncSession) -> None:
    user = await register(
        session,
        RegisterIn(email="erin@example.com", password="correcthorse"),
    )
    pair1 = await login(session, "erin@example.com", "correcthorse")
    pair2 = await refresh_tokens(session, pair1.refresh_token)

    # The refresh token rotates (the access token is a stateless JWT and may
    # be byte-identical when issued in the same second — that's expected).
    assert pair2.refresh_token != pair1.refresh_token

    # The first refresh token must be revoked.
    first_hash = hash_refresh_token(pair1.refresh_token)
    record = await auth_repo.get_by_hash(session, first_hash)
    assert record is not None
    assert record.revoked_at is not None
    assert record.user_id == user.id


async def test_refresh_rejects_revoked_token_and_revokes_all_user_tokens(
    session: AsyncSession,
) -> None:
    user = await register(
        session,
        RegisterIn(email="frank@example.com", password="correcthorse"),
    )
    pair1 = await login(session, "frank@example.com", "correcthorse")
    # Rotate once — pair1.refresh is now revoked, a new active token exists.
    await refresh_tokens(session, pair1.refresh_token)

    with pytest.raises(RefreshTokenReuse):
        await refresh_tokens(session, pair1.refresh_token)

    # All tokens for this user must be revoked after reuse detection.
    from sqlalchemy import select

    from app.modules.auth.models import RefreshToken

    rows = (await session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))).scalars().all()
    assert rows, "expected refresh tokens for the user to exist"
    for row in rows:
        assert row.revoked_at is not None, f"token {row.id} was not revoked after reuse"


async def test_refresh_rejects_unknown_token(session: AsyncSession) -> None:
    with pytest.raises(InvalidRefreshToken):
        await refresh_tokens(session, "definitely-not-a-real-token")


async def test_refresh_rejects_expired_token(session: AsyncSession) -> None:
    user = await register(
        session,
        RegisterIn(email="gail@example.com", password="correcthorse"),
    )
    pair = await login(session, "gail@example.com", "correcthorse")
    # Reach into the DB and expire the row directly.
    from sqlalchemy import update

    from app.modules.auth.models import RefreshToken

    token_hash = hash_refresh_token(pair.refresh_token)
    past = datetime.now(timezone.utc) - timedelta(seconds=1)
    await session.execute(
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .values(expires_at=past)
    )
    await session.commit()
    # Suppress unused warning.
    assert user.id is not None

    with pytest.raises(InvalidRefreshToken):
        await refresh_tokens(session, pair.refresh_token)


async def test_logout_revokes_token(session: AsyncSession) -> None:
    await register(
        session,
        RegisterIn(email="henry@example.com", password="correcthorse"),
    )
    pair = await login(session, "henry@example.com", "correcthorse")
    await logout(session, pair.refresh_token)

    # A logged-out token is a revoked token — replay attempts are detected as
    # reuse and burn the rest of the family. The user must log in again.
    with pytest.raises(RefreshTokenReuse):
        await refresh_tokens(session, pair.refresh_token)


async def test_logout_is_noop_for_unknown_token(session: AsyncSession) -> None:
    # Should not raise.
    await logout(session, "definitely-not-a-real-token")
