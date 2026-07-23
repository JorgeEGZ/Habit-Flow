"""Service tests for the savings module."""
from __future__ import annotations

import pytest
from datetime import date
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import SavingContributionNotFound, SavingGoalNotFound, ValidationError
from app.core.security import hash_password
from app.modules.savings import service as savings_service
from app.modules.savings.schemas import (
    SavingContributionIn,
    SavingContributionUpdate,
    SavingGoalCreate,
    SavingGoalUpdate,
)
from app.modules.users.models import User


async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash=hash_password("correcthorse"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_create_goal_defaults_to_active(session: AsyncSession) -> None:
    user = await _make_user(session, "alice@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(
            name="Emergency fund",
            description="Buffer",
            target_amount=5000000,
            target_date=date(2026, 12, 31),
        ),
    )
    assert goal.user_id == user.id
    assert goal.status == "active"
    assert goal.created_at is not None
    assert goal.updated_at is not None


async def test_list_goals_scoped_to_user(session: AsyncSession) -> None:
    alice = await _make_user(session, "alice2@example.com")
    bob = await _make_user(session, "bob2@example.com")
    await savings_service.create_goal(
        session,
        user_id=alice.id,
        payload=SavingGoalCreate(name="A1", target_amount=1000),
    )
    await savings_service.create_goal(
        session,
        user_id=bob.id,
        payload=SavingGoalCreate(name="B1", target_amount=2000),
    )

    alice_goals = await savings_service.list_goals(session, user_id=alice.id)
    bob_goals = await savings_service.list_goals(session, user_id=bob.id)

    assert {goal.name for goal in alice_goals} == {"A1"}
    assert {goal.name for goal in bob_goals} == {"B1"}


async def test_get_goal_returns_404_for_other_user(session: AsyncSession) -> None:
    alice = await _make_user(session, "alice3@example.com")
    bob = await _make_user(session, "bob3@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=alice.id,
        payload=SavingGoalCreate(name="Mine", target_amount=1000),
    )

    with pytest.raises(SavingGoalNotFound):
        await savings_service.get_goal(session, user_id=bob.id, goal_id=goal.id)


async def test_add_contribution_requires_positive_amount(session: AsyncSession) -> None:
    user = await _make_user(session, "carol@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Goal", target_amount=1000),
    )

    with pytest.raises(ValidationError):
        await savings_service.add_contribution(
            session,
            user_id=user.id,
            goal_id=goal.id,
            payload=SavingContributionIn(amount=0, contribution_date=date(2026, 6, 17)),
        )


async def test_progress_caps_at_100_and_goal_completes(session: AsyncSession) -> None:
    user = await _make_user(session, "dave@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Trip", target_amount=100),
    )
    first = await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingContributionIn(amount=60, contribution_date=date(2026, 6, 17)),
    )
    second = await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingContributionIn(amount=70, contribution_date=date(2026, 6, 18)),
    )
    third = await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingContributionIn(amount=25, contribution_date=date(2026, 6, 19)),
    )

    progress = await savings_service.get_progress(
        session,
        user_id=user.id,
        goal_id=goal.id,
    )
    refreshed = await savings_service.get_goal(session, user_id=user.id, goal_id=goal.id)
    contributions = await savings_service.list_contributions(
        session,
        user_id=user.id,
        goal_id=goal.id,
    )

    assert first.amount == 60
    assert second.amount == 70
    assert third.amount == 25
    assert progress.current_amount == 155
    assert progress.completion_percentage == 100
    assert progress.status == "completed"
    assert refreshed.status == "completed"
    assert len(contributions) == 3


async def test_update_goal_recomputes_status_from_progress(session: AsyncSession) -> None:
    user = await _make_user(session, "erin@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Laptop", target_amount=100),
    )
    await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingContributionIn(amount=100, contribution_date=date(2026, 6, 17)),
    )

    updated = await savings_service.update_goal(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingGoalUpdate(target_amount=150),
    )

    progress = await savings_service.get_progress(
        session,
        user_id=user.id,
        goal_id=goal.id,
    )

    assert updated.status == "active"
    assert progress.current_amount == 100
    assert progress.completion_percentage == 66
    assert progress.status == "active"


async def test_delete_goal_cascades_contributions(session: AsyncSession) -> None:
    user = await _make_user(session, "frank@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Bike", target_amount=100),
    )
    await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingContributionIn(amount=25, contribution_date=date(2026, 6, 17)),
    )

    await savings_service.delete_goal(session, user_id=user.id, goal_id=goal.id)

    with pytest.raises(SavingGoalNotFound):
        await savings_service.get_goal(session, user_id=user.id, goal_id=goal.id)


async def test_update_contribution_recalculates_progress_and_status(session: AsyncSession) -> None:
    user = await _make_user(session, "contribution-update@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Trip", target_amount=100),
    )
    contribution = await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingContributionIn(
            amount=100,
            note="  Initial deposit  ",
            contribution_date=date(2026, 6, 17),
        ),
    )
    assert contribution.note == "Initial deposit"

    updated = await savings_service.update_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        contribution_id=contribution.id,
        payload=SavingContributionUpdate(amount=60, note="   "),
    )
    progress = await savings_service.get_progress(session, user_id=user.id, goal_id=goal.id)
    refreshed_goal = await savings_service.get_goal(session, user_id=user.id, goal_id=goal.id)

    assert updated.amount == 60
    assert updated.note is None
    assert progress.current_amount == 60
    assert progress.status == "active"
    assert refreshed_goal.status == "active"


async def test_delete_contribution_recalculates_progress(session: AsyncSession) -> None:
    user = await _make_user(session, "contribution-delete@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Laptop", target_amount=100),
    )
    contribution = await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingContributionIn(amount=100, contribution_date=date(2026, 6, 17)),
    )

    await savings_service.delete_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        contribution_id=contribution.id,
    )
    progress = await savings_service.get_progress(session, user_id=user.id, goal_id=goal.id)

    assert progress.current_amount == 0
    assert progress.status == "active"
    with pytest.raises(SavingContributionNotFound):
        await savings_service.delete_contribution(
            session,
            user_id=user.id,
            goal_id=goal.id,
            contribution_id=contribution.id,
        )


async def test_contribution_rejects_future_dates_and_allows_historical_dates(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "contribution-dates@example.com")
    goal = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Reserve", target_amount=100),
    )

    historical = await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal.id,
        payload=SavingContributionIn(amount=10, contribution_date=date(2020, 1, 1)),
    )
    assert historical.contribution_date == date(2020, 1, 1)

    with pytest.raises(ValidationError):
        await savings_service.add_contribution(
            session,
            user_id=user.id,
            goal_id=goal.id,
            payload=SavingContributionIn(amount=10, contribution_date=date(2999, 1, 1)),
        )
