from __future__ import annotations

import uuid

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, DbSession
from app.modules.savings import service as savings_service
from app.modules.savings.schemas import (
    SavingContributionIn,
    SavingContributionRead,
    SavingGoalCreate,
    SavingGoalProgress,
    SavingGoalRead,
    SavingGoalUpdate,
)

router = APIRouter(prefix="/savings/goals", tags=["savings"])


@router.get("", response_model=list[SavingGoalRead])
async def list_goals(session: DbSession, user: CurrentUser) -> list[SavingGoalRead]:
    goals = await savings_service.list_goals(session, user_id=user.id)
    return [SavingGoalRead.model_validate(goal) for goal in goals]


@router.post("", response_model=SavingGoalRead, status_code=status.HTTP_201_CREATED)
async def create_goal(
    payload: SavingGoalCreate,
    session: DbSession,
    user: CurrentUser,
) -> SavingGoalRead:
    goal = await savings_service.create_goal(session, user_id=user.id, payload=payload)
    return SavingGoalRead.model_validate(goal)


@router.get("/{goal_id}", response_model=SavingGoalRead)
async def get_goal(
    goal_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> SavingGoalRead:
    goal = await savings_service.get_goal(session, user_id=user.id, goal_id=goal_id)
    return SavingGoalRead.model_validate(goal)


@router.patch("/{goal_id}", response_model=SavingGoalRead)
async def update_goal(
    goal_id: uuid.UUID,
    payload: SavingGoalUpdate,
    session: DbSession,
    user: CurrentUser,
) -> SavingGoalRead:
    goal = await savings_service.update_goal(
        session,
        user_id=user.id,
        goal_id=goal_id,
        payload=payload,
    )
    return SavingGoalRead.model_validate(goal)


@router.delete("/{goal_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_goal(
    goal_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await savings_service.delete_goal(session, user_id=user.id, goal_id=goal_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{goal_id}/contributions", response_model=list[SavingContributionRead])
async def list_contributions(
    goal_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> list[SavingContributionRead]:
    contributions = await savings_service.list_contributions(
        session, user_id=user.id, goal_id=goal_id
    )
    return [SavingContributionRead.model_validate(contribution) for contribution in contributions]


@router.post(
    "/{goal_id}/contributions",
    response_model=SavingContributionRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_contribution(
    goal_id: uuid.UUID,
    payload: SavingContributionIn,
    session: DbSession,
    user: CurrentUser,
) -> SavingContributionRead:
    contribution = await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal_id,
        payload=payload,
    )
    return SavingContributionRead.model_validate(contribution)


@router.get("/{goal_id}/progress", response_model=SavingGoalProgress)
async def get_progress(
    goal_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> SavingGoalProgress:
    return await savings_service.get_progress(
        session, user_id=user.id, goal_id=goal_id
    )
