from __future__ import annotations

import uuid
from datetime import date

from app.core.exceptions import HabitNotFound, ValidationError
from app.modules.habits import repository as habits_repo
from app.modules.habits.models import (
    FREQUENCY_DAILY,
    TRACKING_BOOLEAN,
    TRACKING_NUMERIC,
    Habit,
    HabitLog,
)
from app.modules.habits.schemas import (
    HabitCreate,
    HabitLogIn,
    HabitStreak,
    HabitUpdate,
)


# ---------- Helpers ----------

def _derive_completed(habit: Habit, logged_value: int | None) -> bool:
    """Boolean habits are completed iff their log exists; the service always
    sets completed=True for a boolean log. Numeric habits are completed iff
    logged_value >= target_value.

    Always called on read AND on write, so the stored column is a redundant
    optimization and never the source of truth for what the API returns.
    """
    if habit.tracking_mode == TRACKING_BOOLEAN:
        return True
    # numeric
    if logged_value is None or habit.target_value is None:
        return False
    return logged_value >= habit.target_value


def _recompute_completed_in_place(log: HabitLog, habit: Habit) -> None:
    """Mutate ``log.completed`` so the returned object reflects the current
    target_value. Called on every read in the service layer.
    """
    log.completed = _derive_completed(habit, log.logged_value)


def _validate_tracking_shape(
    tracking_mode: str,
    *,
    target_value: int | None,
    unit: str | None,
) -> None:
    """Enforce the cross-field invariant: numeric habits must carry
    target_value and unit; boolean habits must not. Raises our domain
    ``ValidationError`` so HTTP responses use the standard error envelope.

    Pydantic enforces the same on the wire via HabitCreate's model_validator,
    but we re-validate here so direct service calls (and the merged-state
    check inside update_habit) go through the same error type.
    """
    if tracking_mode == TRACKING_NUMERIC:
        if target_value is None or unit is None:
            raise ValidationError(
                "Numeric habits require both target_value and unit."
            )
    elif tracking_mode == TRACKING_BOOLEAN:
        if target_value is not None or unit is not None:
            raise ValidationError(
                "Boolean habits must not declare target_value or unit."
            )
    else:
        raise ValidationError(f"Unknown tracking_mode: {tracking_mode!r}.")


# ---------- Habit CRUD ----------

async def create_habit(session, *, user_id: uuid.UUID, payload: HabitCreate) -> Habit:
    _validate_tracking_shape(
        payload.tracking_mode,
        target_value=payload.target_value,
        unit=payload.unit,
    )
    return await habits_repo.create(
        session,
        user_id=user_id,
        title=payload.title,
        description=payload.description,
        tracking_mode=payload.tracking_mode,
        target_value=payload.target_value,
        unit=payload.unit,
        frequency=payload.frequency or FREQUENCY_DAILY,
    )


async def list_habits(session, *, user_id: uuid.UUID) -> list[Habit]:
    return await habits_repo.list_for_user(session, user_id=user_id)


async def get_habit(session, *, user_id: uuid.UUID, habit_id: uuid.UUID) -> Habit:
    habit = await habits_repo.get_by_id_and_user(
        session, habit_id=habit_id, user_id=user_id
    )
    if not habit:
        raise HabitNotFound()
    return habit


async def update_habit(
    session,
    *,
    user_id: uuid.UUID,
    habit_id: uuid.UUID,
    payload: HabitUpdate,
) -> Habit:
    habit = await get_habit(session, user_id=user_id, habit_id=habit_id)
    fields = payload.model_dump(exclude_unset=True)

    # Validate the merged state still satisfies the tracking-mode invariants
    # before we hand the patch to the repository.
    _validate_tracking_shape(
        habit.tracking_mode,
        target_value=fields.get("target_value", habit.target_value),
        unit=fields.get("unit", habit.unit),
    )

    return await habits_repo.update(session, habit, fields=fields)


async def delete_habit(session, *, user_id: uuid.UUID, habit_id: uuid.UUID) -> None:
    habit = await get_habit(session, user_id=user_id, habit_id=habit_id)
    await habits_repo.delete(session, habit)


# ---------- Logging ----------

async def log_habit(
    session,
    *,
    user_id: uuid.UUID,
    habit_id: uuid.UUID,
    payload: HabitLogIn,
    today: date,
) -> HabitLog:
    habit = await get_habit(session, user_id=user_id, habit_id=habit_id)

    # Reject future dates.
    if payload.logged_on > today:
        raise ValidationError("logged_on cannot be in the future.")

    # Cross-field invariant: numeric habits require a value; boolean habits
    # must not send one. The schema accepts both, so we enforce here.
    if habit.tracking_mode == TRACKING_NUMERIC and payload.logged_value is None:
        raise ValidationError("Numeric habits require logged_value.")
    if habit.tracking_mode == TRACKING_BOOLEAN and payload.logged_value is not None:
        raise ValidationError("Boolean habits must not send logged_value.")

    completed = _derive_completed(habit, payload.logged_value)

    log = await habits_repo.upsert_log(
        session,
        habit_id=habit_id,
        logged_on=payload.logged_on,
        completed=completed,
        logged_value=payload.logged_value,
        note=payload.note,
    )
    # Defense in depth: recompute on the returned object so the API never
    # sees a stale `completed` (e.g. if target_value was just changed in a
    # concurrent transaction).
    _recompute_completed_in_place(log, habit)
    return log


async def delete_log(
    session,
    *,
    user_id: uuid.UUID,
    habit_id: uuid.UUID,
    logged_on: date,
) -> None:
    habit = await get_habit(session, user_id=user_id, habit_id=habit_id)
    await habits_repo.delete_log(session, habit_id=habit_id, logged_on=logged_on)


# ---------- Streak ----------

async def compute_streak(
    session,
    *,
    user_id: uuid.UUID,
    habit_id: uuid.UUID,
    today: date,
) -> HabitStreak:
    """Return the current and longest streak for the given habit.

    ``today`` is injected so tests can pin it. In production, the route
    passes ``date.today()`` from the server's clock.

    Streak = number of consecutive completed days ending at or after
    yesterday. If the most recent completed day is older than yesterday,
    current = 0. Longest is the maximum run of consecutive days anywhere
    in the log.
    """
    habit = await get_habit(session, user_id=user_id, habit_id=habit_id)
    logs = await habits_repo.list_logs_for_habit(session, habit_id=habit_id)
    days = [
        log.logged_on
        for log in logs
        if _derive_completed(habit, log.logged_value)
    ]
    return _streak_from_days(days, today)


def _streak_from_days(days: list[date], today: date) -> HabitStreak:
    if not days:
        return HabitStreak(current=0, longest=0)

    longest = 1
    run = 1
    for prev, curr in zip(days, days[1:]):
        if (curr - prev).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    most_recent = days[-1]
    if (today - most_recent).days > 1:
        current = 0
    else:
        current = run
    return HabitStreak(current=current, longest=longest)
