from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.savings.models import SavingContribution, SavingGoal


def _goal_progress_stmt() -> Select[Any]:
    return (
        select(
            SavingGoal,
            func.coalesce(func.sum(SavingContribution.amount), 0).label("current_amount"),
        )
        .outerjoin(SavingContribution, SavingContribution.saving_goal_id == SavingGoal.id)
    )


async def get_goal_by_id_and_user(
    session: AsyncSession,
    *,
    goal_id: uuid.UUID,
    user_id: uuid.UUID,
) -> SavingGoal | None:
    stmt = select(SavingGoal).where(
        SavingGoal.id == goal_id,
        SavingGoal.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def get_goal_with_progress(
    session: AsyncSession,
    *,
    goal_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[SavingGoal, int] | None:
    stmt = (
        _goal_progress_stmt()
        .where(SavingGoal.id == goal_id, SavingGoal.user_id == user_id)
        .group_by(SavingGoal.id)
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return row[0], int(row[1] or 0)


async def list_goals_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[tuple[SavingGoal, int]]:
    stmt = (
        _goal_progress_stmt()
        .where(SavingGoal.user_id == user_id)
        .group_by(SavingGoal.id)
        .order_by(SavingGoal.created_at.asc(), SavingGoal.id.asc())
    )
    result = await session.execute(stmt)
    return [(row[0], int(row[1] or 0)) for row in result.all()]


async def create_goal(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    description: str | None,
    target_amount: int,
    target_date: date | None,
    status: str,
) -> SavingGoal:
    record = SavingGoal(
        user_id=user_id,
        name=name,
        description=description,
        target_amount=target_amount,
        target_date=target_date,
        status=status,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def update_goal(
    session: AsyncSession,
    goal: SavingGoal,
    *,
    fields: dict,
) -> SavingGoal:
    for key, value in fields.items():
        setattr(goal, key, value)
    await session.commit()
    await session.refresh(goal)
    return goal


async def delete_goal(session: AsyncSession, goal: SavingGoal) -> None:
    await session.delete(goal)
    await session.commit()


async def create_contribution(
    session: AsyncSession,
    *,
    saving_goal_id: uuid.UUID,
    amount: int,
    note: str | None,
    contribution_date: date,
) -> SavingContribution:
    record = SavingContribution(
        saving_goal_id=saving_goal_id,
        amount=amount,
        note=note,
        contribution_date=contribution_date,
    )
    session.add(record)
    await session.flush()
    return record


async def get_contribution_for_goal_and_user(
    session: AsyncSession,
    *,
    saving_goal_id: uuid.UUID,
    contribution_id: uuid.UUID,
    user_id: uuid.UUID,
) -> tuple[SavingContribution, SavingGoal] | None:
    stmt = (
        select(SavingContribution, SavingGoal)
        .join(SavingGoal, SavingGoal.id == SavingContribution.saving_goal_id)
        .where(
            SavingContribution.id == contribution_id,
            SavingContribution.saving_goal_id == saving_goal_id,
            SavingGoal.user_id == user_id,
        )
    )
    result = await session.execute(stmt)
    row = result.first()
    if not row:
        return None
    return row[0], row[1]


async def get_contribution_total_for_goal_and_user(
    session: AsyncSession,
    *,
    saving_goal_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    stmt = (
        select(func.coalesce(func.sum(SavingContribution.amount), 0))
        .join(SavingGoal, SavingGoal.id == SavingContribution.saving_goal_id)
        .where(
            SavingContribution.saving_goal_id == saving_goal_id,
            SavingGoal.user_id == user_id,
        )
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def update_contribution(
    session: AsyncSession,
    contribution: SavingContribution,
    *,
    fields: dict,
) -> SavingContribution:
    for key, value in fields.items():
        setattr(contribution, key, value)
    await session.flush()
    return contribution


async def delete_contribution(session: AsyncSession, contribution: SavingContribution) -> None:
    await session.delete(contribution)
    await session.flush()


async def list_contributions_for_goal(
    session: AsyncSession,
    *,
    saving_goal_id: uuid.UUID,
) -> list[SavingContribution]:
    stmt = (
        select(SavingContribution)
        .where(SavingContribution.saving_goal_id == saving_goal_id)
        .order_by(
            SavingContribution.contribution_date.asc(),
            SavingContribution.created_at.asc(),
            SavingContribution.id.asc(),
        )
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
