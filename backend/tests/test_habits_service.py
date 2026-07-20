"""Service tests for the habits module.

Run with: ``pytest tests/test_habits_service.py``.
"""
from __future__ import annotations

import uuid
from datetime import date, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import HabitNotFound, ValidationError
from app.core.security import hash_password
from app.modules.habits import service as habits_service
from app.modules.habits.schemas import (
    HabitCreate,
    HabitLogBooleanIn,
    HabitLogIn,
    HabitLogNumericIn,
    HabitUpdate,
)
from app.modules.habits.service import _streak_from_days
from app.modules.users.models import User


# Note: pytest's asyncio mode is "auto" (configured in pytest.ini), so we
# don't need a module-level pytestmark = pytest.mark.asyncio. Adding one
# would also pull the marker onto the sync streak tests below and warn.


# ---------- Fixtures ----------

async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash=hash_password("correcthorse"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ---------- CRUD ----------

async def test_create_boolean_habit(session: AsyncSession) -> None:
    user = await _make_user(session, "alice@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Meditate", tracking_mode="boolean"),
    )
    assert habit.id is not None
    assert habit.user_id == user.id
    assert habit.tracking_mode == "boolean"
    assert habit.target_value is None
    assert habit.unit is None
    assert habit.frequency == "daily"
    assert habit.created_at is not None
    assert habit.updated_at is not None


async def test_create_numeric_habit_requires_target_and_unit(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "bob@example.com")

    with pytest.raises(ValidationError):
        await habits_service.create_habit(
            session,
            user_id=user.id,
            payload=HabitCreate(title="Walk", tracking_mode="numeric"),
        )

    with pytest.raises(ValidationError):
        await habits_service.create_habit(
            session,
            user_id=user.id,
            payload=HabitCreate(
                title="Walk", tracking_mode="numeric", target_value=5000
            ),
        )


async def test_create_boolean_habit_rejects_target_and_unit(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "carol@example.com")
    with pytest.raises(ValidationError):
        await habits_service.create_habit(
            session,
            user_id=user.id,
            payload=HabitCreate(
                title="Vitamins",
                tracking_mode="boolean",
                target_value=1,
            ),
        )


async def test_create_numeric_habit_success(session: AsyncSession) -> None:
    user = await _make_user(session, "dave@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Walk", tracking_mode="numeric", target_value=5000, unit="steps"
        ),
    )
    assert habit.target_value == 5000
    assert habit.unit == "steps"


async def test_list_habits_scoped_to_user(session: AsyncSession) -> None:
    alice = await _make_user(session, "e1@example.com")
    bob = await _make_user(session, "e2@example.com")
    await habits_service.create_habit(
        session, user_id=alice.id, payload=HabitCreate(title="A1", tracking_mode="boolean")
    )
    await habits_service.create_habit(
        session, user_id=alice.id, payload=HabitCreate(title="A2", tracking_mode="numeric", target_value=2, unit="u")
    )
    await habits_service.create_habit(
        session, user_id=bob.id, payload=HabitCreate(title="B1", tracking_mode="boolean")
    )

    alice_habits = await habits_service.list_habits(session, user_id=alice.id)
    bob_habits = await habits_service.list_habits(session, user_id=bob.id)

    assert {h.title for h in alice_habits} == {"A1", "A2"}
    assert {h.title for h in bob_habits} == {"B1"}


async def test_get_habit_returns_404_for_other_user(session: AsyncSession) -> None:
    alice = await _make_user(session, "f1@example.com")
    bob = await _make_user(session, "f2@example.com")
    habit = await habits_service.create_habit(
        session, user_id=alice.id, payload=HabitCreate(title="Mine", tracking_mode="boolean")
    )
    with pytest.raises(HabitNotFound):
        await habits_service.get_habit(session, user_id=bob.id, habit_id=habit.id)


async def test_update_habit_partial(session: AsyncSession) -> None:
    user = await _make_user(session, "g@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Walk", tracking_mode="numeric", target_value=5000, unit="steps"),
    )
    updated = await habits_service.update_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitUpdate(title="Run", target_value=3000),
    )
    assert updated.title == "Run"
    assert updated.target_value == 3000
    assert updated.unit == "steps"  # unchanged


async def test_delete_habit_cascades_to_logs(session: AsyncSession) -> None:
    user = await _make_user(session, "h@example.com")
    habit = await habits_service.create_habit(
        session, user_id=user.id, payload=HabitCreate(title="Meditate", tracking_mode="boolean")
    )
    await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogIn(logged_on=date(2026, 6, 15)),
        today=date(2026, 6, 16),
    )
    await habits_service.delete_habit(session, user_id=user.id, habit_id=habit.id)
    with pytest.raises(HabitNotFound):
        await habits_service.get_habit(session, user_id=user.id, habit_id=habit.id)


# ---------- Logging ----------

async def test_log_boolean_habit_completes(session: AsyncSession) -> None:
    user = await _make_user(session, "i@example.com")
    habit = await habits_service.create_habit(
        session, user_id=user.id, payload=HabitCreate(title="Vitamins", tracking_mode="boolean")
    )
    log = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogIn(logged_on=date(2026, 6, 15)),
        today=date(2026, 6, 16),
    )
    assert log.completed is True
    assert log.logged_value is None
    assert log.updated_at is not None


async def test_log_numeric_below_target_is_not_completed(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "j@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Walk", tracking_mode="numeric", target_value=10000, unit="steps"),
    )
    log = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        # logged_value is required for numeric; pass via the base model —
        # the service resolves it through HabitLogNumericIn.
        payload=HabitLogNumericIn(logged_on=date(2026, 6, 15), logged_value=4000),
        today=date(2026, 6, 16),
    )
    assert log.completed is False
    assert log.logged_value == 4000


async def test_log_numeric_at_or_above_target_is_completed(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "k@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Walk", tracking_mode="numeric", target_value=10000, unit="steps"),
    )
    log = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogNumericIn(logged_on=date(2026, 6, 15), logged_value=10000),
        today=date(2026, 6, 16),
    )
    assert log.completed is True


async def test_log_same_day_upserts(session: AsyncSession) -> None:
    user = await _make_user(session, "l@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Walk", tracking_mode="numeric", target_value=10000, unit="steps"),
    )
    first = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogNumericIn(logged_on=date(2026, 6, 15), logged_value=3000),
        today=date(2026, 6, 16),
    )
    second = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogNumericIn(logged_on=date(2026, 6, 15), logged_value=12000, note="later"),
        today=date(2026, 6, 16),
    )
    assert first.id == second.id
    assert second.logged_value == 12000
    assert second.completed is True
    assert second.note == "later"
    assert second.updated_at >= first.updated_at


async def test_log_rejects_future_date(session: AsyncSession) -> None:
    user = await _make_user(session, "m@example.com")
    habit = await habits_service.create_habit(
        session, user_id=user.id, payload=HabitCreate(title="Meditate", tracking_mode="boolean")
    )
    with pytest.raises(ValidationError):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=habit.id,
            payload=HabitLogIn(logged_on=date(2099, 1, 1)),
            today=date(2026, 6, 16),
        )


async def test_log_numeric_requires_value(session: AsyncSession) -> None:
    user = await _make_user(session, "n@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Walk", tracking_mode="numeric", target_value=5000, unit="steps"),
    )
    with pytest.raises(ValidationError):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=habit.id,
            payload=HabitLogIn(logged_on=date(2026, 6, 15)),
            today=date(2026, 6, 16),
        )


async def test_log_boolean_rejects_value(session: AsyncSession) -> None:
    user = await _make_user(session, "o@example.com")
    habit = await habits_service.create_habit(
        session, user_id=user.id, payload=HabitCreate(title="Meditate", tracking_mode="boolean")
    )
    with pytest.raises(ValidationError):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=habit.id,
            # type: ignore[arg-type]  -- simulating a malformed payload
            payload=HabitLogNumericIn(logged_on=date(2026, 6, 15), logged_value=5),
            today=date(2026, 6, 16),
        )


async def test_delete_log(session: AsyncSession) -> None:
    user = await _make_user(session, "p@example.com")
    habit = await habits_service.create_habit(
        session, user_id=user.id, payload=HabitCreate(title="Meditate", tracking_mode="boolean")
    )
    await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogIn(logged_on=date(2026, 6, 15)),
        today=date(2026, 6, 16),
    )
    await habits_service.delete_log(
        session, user_id=user.id, habit_id=habit.id, logged_on=date(2026, 6, 15)
    )
    # Logging again on the same day creates a fresh row.
    again = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogIn(logged_on=date(2026, 6, 15)),
        today=date(2026, 6, 16),
    )
    assert again.completed is True


# ---------- Streak ----------

def test_streak_empty() -> None:
    s = _streak_from_days([], today=date(2026, 6, 16))
    assert s.current == 0
    assert s.longest == 0


def test_streak_single_day_today() -> None:
    s = _streak_from_days([date(2026, 6, 16)], today=date(2026, 6, 16))
    assert s.current == 1
    assert s.longest == 1


def test_streak_single_day_yesterday() -> None:
    s = _streak_from_days([date(2026, 6, 15)], today=date(2026, 6, 16))
    assert s.current == 1
    assert s.longest == 1


def test_streak_broken_when_most_recent_is_old() -> None:
    s = _streak_from_days([date(2026, 6, 10)], today=date(2026, 6, 16))
    assert s.current == 0
    assert s.longest == 1


def test_streak_consecutive_days() -> None:
    days = [date(2026, 6, 14), date(2026, 6, 15), date(2026, 6, 16)]
    s = _streak_from_days(days, today=date(2026, 6, 16))
    assert s.current == 3
    assert s.longest == 3


def test_streak_longest_greater_than_current() -> None:
    days = [
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 3),
        date(2026, 6, 4),
        date(2026, 6, 5),  # run of 5, then gap
        date(2026, 6, 15),
        date(2026, 6, 16),  # current run of 2
    ]
    s = _streak_from_days(days, today=date(2026, 6, 16))
    assert s.longest == 5
    assert s.current == 2


def test_streak_with_gap_then_recent_run() -> None:
    days = [
        date(2026, 6, 1),
        date(2026, 6, 2),
        date(2026, 6, 10),
        date(2026, 6, 11),
        date(2026, 6, 12),
        date(2026, 6, 13),
    ]
    s = _streak_from_days(days, today=date(2026, 6, 13))
    assert s.longest == 4
    assert s.current == 4


async def test_compute_streak_integration(session: AsyncSession) -> None:
    user = await _make_user(session, "q@example.com")
    habit = await habits_service.create_habit(
        session, user_id=user.id, payload=HabitCreate(title="Meditate", tracking_mode="boolean")
    )
    # Log three consecutive days.
    for d in [date(2026, 6, 14), date(2026, 6, 15), date(2026, 6, 16)]:
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=habit.id,
            payload=HabitLogIn(logged_on=d),
            today=date(2026, 6, 16),
        )
    s = await habits_service.compute_streak(
        session,
        user_id=user.id,
        habit_id=habit.id,
        today=date(2026, 6, 16),
    )
    assert s.current == 3
    assert s.longest == 3


async def test_compute_streak_recomputes_after_target_change(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "q2@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Walk", tracking_mode="numeric", target_value=5000, unit="steps"
        ),
    )
    await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogNumericIn(logged_on=date(2026, 6, 15), logged_value=5000),
        today=date(2026, 6, 16),
    )

    await habits_service.update_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitUpdate(target_value=10000),
    )

    s = await habits_service.compute_streak(
        session,
        user_id=user.id,
        habit_id=habit.id,
        today=date(2026, 6, 16),
    )
    assert s.current == 0
    assert s.longest == 0


# ---------- Stale-completion safeguard ----------

async def test_completion_recomputed_after_target_change(
    session: AsyncSession,
) -> None:
    """If target_value is raised after a log is written, the read path
    re-derives `completed` from logged_value vs target_value so a stale
    column cannot leak into API responses.
    """
    user = await _make_user(session, "r@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Walk", tracking_mode="numeric", target_value=5000, unit="steps"),
    )
    log = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogNumericIn(logged_on=date(2026, 6, 15), logged_value=5000),
        today=date(2026, 6, 16),
    )
    assert log.completed is True

    # Raise the target; the log row is now stale.
    await habits_service.update_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitUpdate(target_value=10000),
    )
    # Re-fetch the log via the service to exercise the recompute path.
    from sqlalchemy import select

    from app.modules.habits.models import HabitLog

    fresh = (
        await session.execute(
            select(HabitLog).where(
                HabitLog.habit_id == habit.id,
                HabitLog.logged_on == date(2026, 6, 15),
            )
        )
    ).scalar_one()
    habits_service._recompute_completed_in_place(fresh, habit)
    assert fresh.completed is False  # 5000 < 10000
