from __future__ import annotations

import uuid
from datetime import date

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, DbSession
from app.modules.habits import service as habits_service
from app.modules.habits.schemas import (
    HabitCreate,
    HabitLogIn,
    HabitLogRead,
    HabitRead,
    HabitStreak,
    HabitUpdate,
)

router = APIRouter(prefix="/habits", tags=["habits"])


# ---------- Habit CRUD ----------

@router.post("", response_model=HabitRead, status_code=status.HTTP_201_CREATED)
async def create_habit(
    payload: HabitCreate,
    session: DbSession,
    user: CurrentUser,
) -> HabitRead:
    habit = await habits_service.create_habit(
        session, user_id=user.id, payload=payload
    )
    return HabitRead.model_validate(habit)


@router.get("", response_model=list[HabitRead])
async def list_habits(
    session: DbSession,
    user: CurrentUser,
) -> list[HabitRead]:
    habits = await habits_service.list_habits(session, user_id=user.id)
    return [HabitRead.model_validate(h) for h in habits]


@router.get("/{habit_id}", response_model=HabitRead)
async def get_habit(
    habit_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> HabitRead:
    habit = await habits_service.get_habit(
        session, user_id=user.id, habit_id=habit_id
    )
    return HabitRead.model_validate(habit)


@router.patch("/{habit_id}", response_model=HabitRead)
async def update_habit(
    habit_id: uuid.UUID,
    payload: HabitUpdate,
    session: DbSession,
    user: CurrentUser,
) -> HabitRead:
    habit = await habits_service.update_habit(
        session,
        user_id=user.id,
        habit_id=habit_id,
        payload=payload,
    )
    return HabitRead.model_validate(habit)


@router.delete("/{habit_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_habit(
    habit_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await habits_service.delete_habit(session, user_id=user.id, habit_id=habit_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Logging ----------

@router.post(
    "/{habit_id}/logs",
    response_model=HabitLogRead,
    status_code=status.HTTP_200_OK,
)
async def log_habit(
    habit_id: uuid.UUID,
    payload: HabitLogIn,
    session: DbSession,
    user: CurrentUser,
) -> HabitLogRead:
    log = await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=habit_id,
        payload=payload,
        today=date.today(),
    )
    return HabitLogRead.model_validate(log)


@router.delete(
    "/{habit_id}/logs/{logged_on}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_log(
    habit_id: uuid.UUID,
    logged_on: date,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await habits_service.delete_log(
        session,
        user_id=user.id,
        habit_id=habit_id,
        logged_on=logged_on,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Streak ----------

@router.get("/{habit_id}/streak", response_model=HabitStreak)
async def get_streak(
    habit_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> HabitStreak:
    return await habits_service.compute_streak(
        session,
        user_id=user.id,
        habit_id=habit_id,
        today=date.today(),
    )