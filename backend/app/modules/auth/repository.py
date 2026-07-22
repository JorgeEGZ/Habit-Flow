from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import RefreshToken


async def create(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    token_hash: str,
    expires_at: datetime,
) -> RefreshToken:
    record = RefreshToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=expires_at,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def get_active_by_hash(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked_at.is_(None),
        RefreshToken.expires_at > datetime.now(timezone.utc),
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_by_hash(session: AsyncSession, token_hash: str) -> RefreshToken | None:
    """Return any refresh-token row by hash, regardless of revocation.

    Used by the service layer to detect reuse of an already-rotated token.
    """
    stmt = select(RefreshToken).where(RefreshToken.token_hash == token_hash)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def revoke(session: AsyncSession, record: RefreshToken) -> None:
    record.revoked_at = datetime.now(timezone.utc)
    await session.commit()


async def revoke_all_for_user(
    session: AsyncSession,
    user_id: uuid.UUID,
    *,
    commit: bool = True,
) -> None:
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc))
    )
    await session.execute(stmt)
    if commit:
        await session.commit()
