from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def get_by_id(session: AsyncSession, user_id: uuid.UUID) -> User | None:
    return await session.get(User, user_id)


async def get_by_email(session: AsyncSession, email: str) -> User | None:
    stmt = select(User).where(User.email == email)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def update(
    session: AsyncSession,
    user: User,
    fields: dict[str, Any],
) -> User:
    """Apply a partial update to a user.

    `fields` is expected to be the result of
    ``UserUpdate.model_dump(exclude_unset=True)`` so that absent fields are
    not overwritten. The repository does not validate keys — the service
    layer is responsible for translating a Pydantic payload into the
    allowed field set.
    """
    for key, value in fields.items():
        setattr(user, key, value)
    await session.commit()
    await session.refresh(user)
    return user
