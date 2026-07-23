from __future__ import annotations

import uuid

from app.core.exceptions import (
    SavingContributionNotFound,
    SavingGoalNotFound,
    ValidationError,
)
from app.core.exports import current_app_date
from app.modules.savings import repository as savings_repo
from app.modules.savings.models import STATUS_ACTIVE, STATUS_COMPLETED, SavingGoal
from app.modules.savings.schemas import (
    SavingContributionIn,
    SavingContributionRead,
    SavingContributionUpdate,
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


def _validate_contribution_date(contribution_date) -> None:
    if contribution_date > current_app_date():
        raise ValidationError("Contribution date cannot be in the future.")


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


async def get_goal_export_rows(session, *, user_id: uuid.UUID) -> list[list[object]]:
    rows = await savings_repo.list_goals_for_user(session, user_id=user_id)
    return [
        [
            goal.name,
            goal.description,
            goal.target_amount,
            current_amount,
            max(goal.target_amount - current_amount, 0),
            _completion_percentage(current_amount, goal.target_amount),
            _derive_status(current_amount, goal.target_amount),
            goal.target_date.isoformat() if goal.target_date else None,
            str(goal.id),
            goal.created_at.isoformat(),
            goal.updated_at.isoformat(),
        ]
        for goal, current_amount in rows
    ]


async def get_contribution_export_rows(
    session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
) -> list[list[object]]:
    goal = await get_goal(session, user_id=user_id, goal_id=goal_id)
    contributions = await savings_repo.list_contributions_for_goal(
        session, saving_goal_id=goal_id
    )
    return [
        [
            goal.name,
            contribution.contribution_date.isoformat(),
            contribution.amount,
            contribution.note,
            str(contribution.id),
            str(goal.id),
            contribution.created_at.isoformat(),
            contribution.updated_at.isoformat(),
        ]
        for contribution in contributions
    ]


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

    goal, _current_amount = goal_row
    _validate_positive_amount(payload.amount, label="Contribution amount")
    _validate_contribution_date(payload.contribution_date)

    contribution = await savings_repo.create_contribution(
        session,
        saving_goal_id=goal_id,
        amount=payload.amount,
        note=payload.note,
        contribution_date=payload.contribution_date,
    )

    await _commit_contribution_mutation(
        session,
        user_id=user_id,
        goal=goal,
    )
    await session.refresh(contribution)
    return contribution


async def update_contribution(
    session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    contribution_id: uuid.UUID,
    payload: SavingContributionUpdate,
):
    row = await savings_repo.get_contribution_for_goal_and_user(
        session,
        saving_goal_id=goal_id,
        contribution_id=contribution_id,
        user_id=user_id,
    )
    if not row:
        raise SavingContributionNotFound()

    contribution, goal = row
    fields = payload.model_dump(exclude_unset=True)
    if "contribution_date" in fields and fields["contribution_date"] is not None:
        _validate_contribution_date(fields["contribution_date"])

    await savings_repo.update_contribution(session, contribution, fields=fields)
    await _commit_contribution_mutation(session, user_id=user_id, goal=goal)
    await session.refresh(contribution)
    return contribution


async def delete_contribution(
    session,
    *,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    contribution_id: uuid.UUID,
) -> None:
    row = await savings_repo.get_contribution_for_goal_and_user(
        session,
        saving_goal_id=goal_id,
        contribution_id=contribution_id,
        user_id=user_id,
    )
    if not row:
        raise SavingContributionNotFound()

    contribution, goal = row
    await savings_repo.delete_contribution(session, contribution)
    await _commit_contribution_mutation(session, user_id=user_id, goal=goal)


async def _commit_contribution_mutation(session, *, user_id: uuid.UUID, goal: SavingGoal) -> None:
    current_amount = await savings_repo.get_contribution_total_for_goal_and_user(
        session,
        saving_goal_id=goal.id,
        user_id=user_id,
    )
    goal.status = _derive_status(current_amount, goal.target_amount)
    await session.commit()


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
