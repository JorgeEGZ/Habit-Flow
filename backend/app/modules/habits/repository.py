from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import and_, delete as sql_delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.habits.models import Habit, HabitLog


# ---------- Habit ----------

async def get_by_id_and_user(
    session: AsyncSession, *, habit_id: uuid.UUID, user_id: uuid.UUID
) -> Habit | None:
    """Fetch a habit owned by a specific user.

    Cross-user access returns None — the service translates that to 404.
    """
    stmt = select(Habit).where(Habit.id == habit_id, Habit.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> list[Habit]:
    stmt = (
        select(Habit)
        .where(Habit.user_id == user_id)
        .order_by(Habit.created_at.asc(), Habit.id.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_for_user_with_logs_between(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    start_date: date,
    end_date: date,
) -> list[tuple[Habit, list[HabitLog]]]:
    """Load a user's habits with only their logs in the requested period."""
    stmt = (
        select(Habit, HabitLog)
        .outerjoin(
            HabitLog,
            and_(
                HabitLog.habit_id == Habit.id,
                HabitLog.logged_on >= start_date,
                HabitLog.logged_on <= end_date,
            ),
        )
        .where(Habit.user_id == user_id)
        .order_by(Habit.created_at.asc(), Habit.id.asc(), HabitLog.logged_on.asc())
    )
    rows = (await session.execute(stmt)).all()
    grouped: dict[uuid.UUID, tuple[Habit, list[HabitLog]]] = {}
    for habit, log in rows:
        if habit.id not in grouped:
            grouped[habit.id] = (habit, [])
        if log is not None:
            grouped[habit.id][1].append(log)
    return list(grouped.values())


async def create(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    title: str,
    description: str | None,
    tracking_mode: str,
    target_value: int | None,
    unit: str | None,
    frequency: str,
) -> Habit:
    record = Habit(
        user_id=user_id,
        title=title,
        description=description,
        tracking_mode=tracking_mode,
        target_value=target_value,
        unit=unit,
        frequency=frequency,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def update(
    session: AsyncSession,
    habit: Habit,
    *,
    fields: dict,
) -> Habit:
    """Apply a partial update. `fields` is the result of
    ``HabitUpdate.model_dump(exclude_unset=True)``.

    Constraint invariants (numeric-requires-target, etc.) are validated at
    the service layer against the merged state before this is called.
    """
    for key, value in fields.items():
        setattr(habit, key, value)
    await session.commit()
    await session.refresh(habit)
    return habit


async def delete(session: AsyncSession, habit: Habit) -> None:
    await session.delete(habit)
    await session.commit()


# ---------- HabitLog ----------

async def get_log_for_day(
    session: AsyncSession,
    *,
    habit_id: uuid.UUID,
    logged_on: date,
) -> HabitLog | None:
    stmt = select(HabitLog).where(
        HabitLog.habit_id == habit_id,
        HabitLog.logged_on == logged_on,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def upsert_log(
    session: AsyncSession,
    *,
    habit_id: uuid.UUID,
    logged_on: date,
    completed: bool,
    logged_value: int | None,
    note: str | None,
) -> HabitLog:
    """Insert a log row, or update the existing one for (habit_id, logged_on).

    Both SQLite (test) and Postgres (prod) support ``ON CONFLICT DO UPDATE``
    via the dialect-specific insert builders.
    """
    payload = {
        "habit_id": habit_id,
        "logged_on": logged_on,
        "completed": completed,
        "logged_value": logged_value,
        "note": note,
    }
    bind = session.bind
    is_postgres = bool(bind and bind.dialect.name == "postgresql")
    if is_postgres:
        stmt = (
            pg_insert(HabitLog)
            .values(**payload)
            .on_conflict_do_update(
                constraint="uq_habit_logs_habit_day",
                set_={
                    "completed": payload["completed"],
                    "logged_value": payload["logged_value"],
                    "note": payload["note"],
                    "updated_at": func.now(),
                },
            )
        )
    else:
        from sqlalchemy.dialects.sqlite import insert as sqlite_insert

        stmt = sqlite_insert(HabitLog).values(**payload).on_conflict_do_update(
            index_elements=["habit_id", "logged_on"],
            set_={
                "completed": payload["completed"],
                "logged_value": payload["logged_value"],
                "note": payload["note"],
                "updated_at": func.now(),
            },
        )
    await session.execute(stmt)
    await session.commit()
    refreshed = await get_log_for_day(session, habit_id=habit_id, logged_on=logged_on)
    assert refreshed is not None, "upsert must produce a row"
    # Force a re-read from the database so the in-memory object reflects
    # the post-upsert state. Without this, a same-session caller that
    # already has the row mapped would see the stale attribute values.
    await session.refresh(refreshed)
    return refreshed


async def delete_log(
    session: AsyncSession,
    *,
    habit_id: uuid.UUID,
    logged_on: date,
) -> bool:
    """Delete the log for (habit_id, logged_on). Returns True if a row was
    deleted, False if no such row existed.
    """
    stmt = sql_delete(HabitLog).where(
        HabitLog.habit_id == habit_id,
        HabitLog.logged_on == logged_on,
    )
    result = await session.execute(stmt)
    await session.commit()
    return bool(result.rowcount)


async def list_logs_for_habit(
    session: AsyncSession,
    *,
    habit_id: uuid.UUID,
) -> list[HabitLog]:
    """Return all logs for a habit, oldest first.

    Streak calculation derives completion from the current habit state, so
    it needs the underlying logs rather than the stored completed flag.
    """
    stmt = (
        select(HabitLog)
        .where(HabitLog.habit_id == habit_id)
        .order_by(HabitLog.logged_on.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
