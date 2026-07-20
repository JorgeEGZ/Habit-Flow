from __future__ import annotations

import uuid

from app.core.exceptions import SavingGoalNotFound, ValidationError
from app.modules.savings import repository as savings_repo
from app.modules.savings.models import STATUS_ACTIVE, STATUS_COMPLETED, SavingGoal
from app.modules.savings.schemas import (
    SavingContributionIn,
    SavingContributionRead,
    SavingGoalCreate,
    SavingGoalProgress,
    SavingGoalUpdate,
)


def _derive_status(current_amount: int, target_amount: int) -> str:
    return STATUS_COMPLETED if current_amount >= target_amount else STATUS_ACTIVE


def _completion_percentage(current_amount: int, target_amount: int) -> int:
    return min(100, (current_amount * 100) // target_amount)


def _validate_positive_amount(amount: int, *, label: str) -> None:
    if amount <= 0:
        raise ValidationError(f"{label} must be greater than zero.")


def _apply_derived_status(goal: SavingGoal, current_amount: int) -> SavingGoal:
    goal.status = _derive_status(current_amount, goal.target_amount)
    return goal


async def create_goal(
    session,
    *,
    user_id: uuid.UUID,
    payload: SavingGoalCreate,
) -> SavingGoal:
    _validate_positive_amount(payload.target_amount, label="Target amount")
    status = _derive_status(0, payload.target_amount)
    return await savings_repo.create_goal(
        session,
        user_id=user_id,
        name=payload.name,
        description=payload.description,
        target_amount=payload.target_amount,
        target_date=payload.target_date,
        status=status,
    )


async def list_goals(session, *, user_id: uuid.UUID) -> list[SavingGoal]:
    rows = await savings_repo.list_goals_for_user(session, user_id=user_id)
    goals: list[SavingGoal] = []
    for goal, current_amount in rows:
        goals.append(_apply_derived_status(goal, current_amount))
    return goals


async def get_goal(session, *, user_id: uuid.UUID, goal_id: uuid.UUID) -> SavingGoal:
    row = await savings_repo.get_goal_with_progress(
        session, goal_id=goal_id, user_id=user_id
    )
    if not row:
        raise SavingGoalNotFound()
    goal, current_amount = row
    return _apply_derived_status(goal, current_amount)


async def update_goal(
    session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    payload: SavingGoalUpdate,
) -> SavingGoal:
    row = await savings_repo.get_goal_with_progress(
        session, goal_id=goal_id, user_id=user_id
    )
    if not row:
        raise SavingGoalNotFound()

    goal, current_amount = row
    fields = payload.model_dump(exclude_unset=True)
    if "target_amount" in fields and fields["target_amount"] is not None:
        _validate_positive_amount(fields["target_amount"], label="Target amount")
        fields["status"] = _derive_status(current_amount, fields["target_amount"])
    else:
        fields["status"] = _derive_status(current_amount, goal.target_amount)
    updated = await savings_repo.update_goal(session, goal, fields=fields)
    return _apply_derived_status(updated, current_amount)


async def delete_goal(session, *, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    goal = await savings_repo.get_goal_by_id_and_user(
        session, goal_id=goal_id, user_id=user_id
    )
    if not goal:
        raise SavingGoalNotFound()
    await savings_repo.delete_goal(session, goal)


async def list_contributions(
    session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> list[SavingContributionRead]:
    await get_goal(session, user_id=user_id, goal_id=goal_id)
    return await savings_repo.list_contributions_for_goal(session, saving_goal_id=goal_id)


async def add_contribution(
    session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    payload: SavingContributionIn,
):
    goal_row = await savings_repo.get_goal_with_progress(
        session, goal_id=goal_id, user_id=user_id
    )
    if not goal_row:
        raise SavingGoalNotFound()

    _goal, _current_amount = goal_row
    _validate_positive_amount(payload.amount, label="Contribution amount")

    contribution = await savings_repo.create_contribution(
        session,
        saving_goal_id=goal_id,
        amount=payload.amount,
        note=payload.note,
        contribution_date=payload.contribution_date,
    )

    refreshed = await savings_repo.get_goal_with_progress(
        session, goal_id=goal_id, user_id=user_id
    )
    assert refreshed is not None
    updated_goal, updated_amount = refreshed
    derived_status = _derive_status(updated_amount, updated_goal.target_amount)
    if updated_goal.status != derived_status:
        await savings_repo.update_goal(
            session,
            updated_goal,
            fields={"status": derived_status},
        )
    return contribution


async def get_progress(
    session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> SavingGoalProgress:
    row = await savings_repo.get_goal_with_progress(
        session, goal_id=goal_id, user_id=user_id
    )
    if not row:
        raise SavingGoalNotFound()

    goal, current_amount = row
    status = _derive_status(current_amount, goal.target_amount)
    return SavingGoalProgress(
        saving_goal_id=goal.id,
        current_amount=current_amount,
        target_amount=goal.target_amount,
        completion_percentage=_completion_percentage(current_amount, goal.target_amount),
        status=status,
    )
