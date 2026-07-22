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


async def test_create_boolean_weekly_habit(session: AsyncSession) -> None:
    user = await _make_user(session, "weekly-boolean@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Run",
            tracking_mode="boolean",
            frequency="weekly",
            target_value=2,
        ),
    )

    assert habit.frequency == "weekly"
    assert habit.target_value == 2
    assert habit.unit is None


async def test_create_numeric_weekly_habit_trims_unit(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "weekly-numeric@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Run distance",
            tracking_mode="numeric",
            frequency="weekly",
            target_value=15,
            unit=" km ",
        ),
    )

    assert habit.frequency == "weekly"
    assert habit.target_value == 15
    assert habit.unit == "km"


@pytest.mark.parametrize("target_value", [0, 8])
async def test_create_boolean_weekly_rejects_target_outside_range(
    session: AsyncSession,
    target_value: int,
) -> None:
    user = await _make_user(
        session, f"weekly-range-{target_value}@example.com"
    )

    with pytest.raises(ValidationError):
        await habits_service.create_habit(
            session,
            user_id=user.id,
            payload=HabitCreate(
                title="Run",
                tracking_mode="boolean",
                frequency="weekly",
                target_value=target_value,
            ),
        )


async def test_create_boolean_weekly_rejects_unit(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "weekly-unit@example.com")

    with pytest.raises(ValidationError):
        await habits_service.create_habit(
            session,
            user_id=user.id,
            payload=HabitCreate(
                title="Run",
                tracking_mode="boolean",
                frequency="weekly",
                target_value=2,
                unit="times",
            ),
        )


async def test_create_numeric_habit_rejects_blank_unit(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "blank-unit@example.com")

    with pytest.raises(ValidationError):
        await habits_service.create_habit(
            session,
            user_id=user.id,
            payload=HabitCreate(
                title="Walk",
                tracking_mode="numeric",
                target_value=5000,
                unit="   ",
            ),
        )


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


# ---------- Progress ----------

async def _progress_for_habit(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    habit_id: uuid.UUID,
    as_of: date,
    today: date,
):
    progress = await habits_service.get_habit_progress(
        session,
        user_id=user_id,
        as_of=as_of,
        today=today,
    )
    return next(item for item in progress if item.habit_id == habit_id)


async def test_boolean_daily_progress_with_and_without_log(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "progress-boolean-daily@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Meditate", tracking_mode="boolean"),
    )
    as_of = date(2026, 7, 15)

    before_log = await _progress_for_habit(
        session, user_id=user.id, habit_id=habit.id, as_of=as_of, today=as_of
    )
    assert (before_log.current_value, before_log.target_value) == (0, 1)
    assert before_log.remaining_value == 1
    assert before_log.completed is False
    assert before_log.log_for_date is None

    log = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogIn(logged_on=as_of),
        today=as_of,
    )
    after_log = await _progress_for_habit(
        session, user_id=user.id, habit_id=habit.id, as_of=as_of, today=as_of
    )
    assert (after_log.current_value, after_log.target_value) == (1, 1)
    assert after_log.remaining_value == 0
    assert after_log.completed is True
    assert after_log.log_for_date is not None
    assert after_log.log_for_date.id == log.id


async def test_numeric_daily_progress_with_and_without_log(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "progress-numeric-daily@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Read", tracking_mode="numeric", target_value=30, unit="minutes"
        ),
    )
    as_of = date(2026, 7, 15)

    no_log = await _progress_for_habit(
        session, user_id=user.id, habit_id=habit.id, as_of=as_of, today=as_of
    )
    assert (no_log.current_value, no_log.remaining_value, no_log.completed) == (0, 30, False)

    await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogNumericIn(logged_on=as_of, logged_value=20),
        today=as_of,
    )
    logged = await _progress_for_habit(
        session, user_id=user.id, habit_id=habit.id, as_of=as_of, today=as_of
    )
    assert (logged.current_value, logged.target_value, logged.remaining_value) == (20, 30, 10)
    assert logged.completed is False
    assert logged.log_for_date is not None


async def test_boolean_weekly_progress_counts_dates_and_same_day_upsert_once(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "progress-boolean-weekly@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Run", tracking_mode="boolean", frequency="weekly", target_value=2
        ),
    )
    monday = date(2026, 7, 13)
    for logged_on in (monday, monday + timedelta(days=1), monday + timedelta(days=1)):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=habit.id,
            payload=HabitLogIn(logged_on=logged_on),
            today=monday + timedelta(days=2),
        )

    progress = await _progress_for_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        as_of=monday + timedelta(days=2),
        today=monday + timedelta(days=2),
    )
    assert progress.period_start == monday
    assert progress.period_end == monday + timedelta(days=6)
    assert progress.current_value == 2
    assert progress.remaining_value == 0
    assert progress.completed is True


async def test_numeric_weekly_progress_updates_same_day_sum(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "progress-numeric-weekly@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Run", tracking_mode="numeric", frequency="weekly", target_value=15, unit="km"
        ),
    )
    monday = date(2026, 7, 13)
    for logged_on, value in ((monday, 4), (monday + timedelta(days=1), 6)):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=habit.id,
            payload=HabitLogNumericIn(logged_on=logged_on, logged_value=value),
            today=monday + timedelta(days=1),
        )
    initial = await _progress_for_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        as_of=monday + timedelta(days=1),
        today=monday + timedelta(days=1),
    )
    assert (initial.current_value, initial.remaining_value, initial.completed) == (10, 5, False)

    await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        payload=HabitLogNumericIn(logged_on=monday + timedelta(days=1), logged_value=12),
        today=monday + timedelta(days=1),
    )
    updated = await _progress_for_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        as_of=monday + timedelta(days=1),
        today=monday + timedelta(days=1),
    )
    assert (updated.current_value, updated.remaining_value, updated.completed) == (16, 0, True)


async def test_weekly_progress_uses_monday_sunday_iso_boundaries(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "progress-boundaries@example.com")
    habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Gym", tracking_mode="boolean", frequency="weekly", target_value=3
        ),
    )
    monday = date(2026, 7, 13)
    for logged_on in (
        monday - timedelta(days=1),
        monday,
        monday + timedelta(days=6),
        monday + timedelta(days=7),
    ):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=habit.id,
            payload=HabitLogIn(logged_on=logged_on),
            today=monday + timedelta(days=7),
        )

    progress = await _progress_for_habit(
        session,
        user_id=user.id,
        habit_id=habit.id,
        as_of=monday + timedelta(days=6),
        today=monday + timedelta(days=7),
    )
    assert progress.period_start == monday
    assert progress.period_end == monday + timedelta(days=6)
    assert progress.current_value == 2
    assert progress.completed is False


async def test_progress_rejects_future_as_of(session: AsyncSession) -> None:
    user = await _make_user(session, "progress-future@example.com")
    today = date(2026, 7, 15)

    with pytest.raises(ValidationError):
        await habits_service.get_habit_progress(
            session,
            user_id=user.id,
            as_of=today + timedelta(days=1),
            today=today,
        )


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
