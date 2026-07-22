"""Service tests for the dashboard module."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.dashboard import service as dashboard_service
from app.modules.finances import service as finances_service
from app.modules.finances.schemas import (
    AccountCreate,
    CategoryCreate,
    RecurringTransactionCreate,
    TransactionCreate,
)
from app.modules.habits import service as habits_service
from app.modules.habits.schemas import HabitCreate, HabitLogIn, HabitLogNumericIn
from app.modules.savings import service as savings_service
from app.modules.savings.schemas import SavingContributionIn, SavingGoalCreate
from app.modules.users.models import User


TODAY = date(2026, 6, 17)


async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash=hash_password("correcthorse"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_empty_dashboard_state(session: AsyncSession) -> None:
    user = await _make_user(session, "dash-empty@example.com")

    summary = await dashboard_service.get_summary(session, user_id=user.id, today=TODAY)
    habits = await dashboard_service.get_habits(session, user_id=user.id, today=TODAY)
    savings = await dashboard_service.get_savings(session, user_id=user.id)
    finances = await dashboard_service.get_finances(session, user_id=user.id, today=TODAY)

    assert summary.habits.completed_today == 0
    assert summary.habits.total_active_habits == 0
    assert summary.habits.current_streak_summary is None
    assert summary.habits.longest_streak_summary is None
    assert summary.savings.total_savings_contributed == 0
    assert summary.savings.active_goals_count == 0
    assert summary.savings.completed_goals_count == 0
    assert summary.savings.nearest_goal is None
    assert summary.savings.savings_progress_summary.current_amount == 0
    assert summary.savings.savings_progress_summary.target_amount == 0
    assert summary.savings.savings_progress_summary.completion_percentage == 0
    assert summary.finances.monthly_income == 0
    assert summary.finances.monthly_expenses == 0
    assert summary.finances.monthly_balance == 0
    assert summary.finances.account_balances == []
    assert summary.finances.recent_transactions == []
    assert summary.finances.insights.as_of == TODAY
    assert summary.finances.insights.month == "2026-06"
    assert summary.finances.insights.top_spending_category is None
    assert summary.finances.insights.upcoming_recurring.total_income == 0
    assert summary.finances.insights.upcoming_recurring.total_expenses == 0
    assert summary.finances.insights.upcoming_recurring.net == 0
    assert summary.finances.insights.upcoming_recurring.occurrence_count == 0
    assert habits == summary.habits
    assert savings == summary.savings
    assert finances == summary.finances


async def test_habit_dashboard_metrics(session: AsyncSession) -> None:
    user = await _make_user(session, "dash-habits@example.com")
    boolean_habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Take vitamins", tracking_mode="boolean"),
    )
    numeric_habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Walk",
            tracking_mode="numeric",
            target_value=10000,
            unit="steps",
        ),
    )

    for logged_on in (date(2026, 6, 16), date(2026, 6, 17)):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=boolean_habit.id,
            payload=HabitLogIn(logged_on=logged_on),
            today=TODAY,
        )

    for logged_on in (
        date(2026, 6, 10),
        date(2026, 6, 11),
        date(2026, 6, 12),
        date(2026, 6, 13),
    ):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=numeric_habit.id,
            payload=HabitLogIn(logged_on=logged_on, logged_value=10000),
            today=TODAY,
        )

    habits = await dashboard_service.get_habits(session, user_id=user.id, today=TODAY)

    assert habits.completed_today == 1
    assert habits.total_active_habits == 2
    assert habits.current_streak_summary is not None
    assert habits.current_streak_summary.habit_id == boolean_habit.id
    assert habits.current_streak_summary.current == 2
    assert habits.longest_streak_summary is not None
    assert habits.longest_streak_summary.habit_id == numeric_habit.id
    assert habits.longest_streak_summary.longest == 4


async def test_habit_dashboard_separates_daily_and_weekly_metrics(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "dash-weekly-habits@example.com")
    daily_habit = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(title="Daily", tracking_mode="boolean"),
    )
    weekly_boolean = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Weekly runs",
            tracking_mode="boolean",
            frequency="weekly",
            target_value=2,
        ),
    )
    weekly_numeric = await habits_service.create_habit(
        session,
        user_id=user.id,
        payload=HabitCreate(
            title="Weekly distance",
            tracking_mode="numeric",
            frequency="weekly",
            target_value=15,
            unit="km",
        ),
    )

    await habits_service.log_habit(
        session,
        user_id=user.id,
        habit_id=daily_habit.id,
        payload=HabitLogIn(logged_on=TODAY),
        today=TODAY,
    )
    for logged_on in (date(2026, 6, 15), date(2026, 6, 16)):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=weekly_boolean.id,
            payload=HabitLogIn(logged_on=logged_on),
            today=TODAY,
        )
    for logged_on, value in ((date(2026, 6, 16), 7), (TODAY, 8)):
        await habits_service.log_habit(
            session,
            user_id=user.id,
            habit_id=weekly_numeric.id,
            payload=HabitLogNumericIn(logged_on=logged_on, logged_value=value),
            today=TODAY,
        )

    habits = await dashboard_service.get_habits(
        session, user_id=user.id, today=TODAY
    )

    assert habits.total_active_habits == 3
    assert habits.daily_habits_total == 1
    assert habits.weekly_habits_total == 2
    assert habits.completed_today == 1
    assert habits.weekly_goals_completed == 2
    assert habits.current_streak_summary is not None
    assert habits.current_streak_summary.habit_id == daily_habit.id


async def test_savings_dashboard_metrics(session: AsyncSession) -> None:
    user = await _make_user(session, "dash-savings@example.com")
    goal_one = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Emergency fund", target_amount=100),
    )
    goal_two = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Trip", target_amount=100, target_date=date(2026, 6, 18)),
    )
    goal_three = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Laptop", target_amount=100, target_date=date(2026, 6, 25)),
    )
    goal_four = await savings_service.create_goal(
        session,
        user_id=user.id,
        payload=SavingGoalCreate(name="Bike", target_amount=100, target_date=date(2026, 6, 30)),
    )

    await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal_one.id,
        payload=SavingContributionIn(amount=20, contribution_date=TODAY),
    )
    await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal_two.id,
        payload=SavingContributionIn(amount=20, contribution_date=TODAY),
    )
    await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal_three.id,
        payload=SavingContributionIn(amount=300, contribution_date=TODAY),
    )
    await savings_service.add_contribution(
        session,
        user_id=user.id,
        goal_id=goal_four.id,
        payload=SavingContributionIn(amount=150, contribution_date=TODAY),
    )

    savings = await dashboard_service.get_savings(session, user_id=user.id)

    assert savings.total_savings_contributed == 490
    assert savings.active_goals_count == 2
    assert savings.completed_goals_count == 2
    assert savings.nearest_goal is not None
    assert savings.nearest_goal.saving_goal_id == goal_two.id
    assert savings.nearest_goal.target_date == date(2026, 6, 18)
    assert savings.savings_progress_summary.current_amount == 490
    assert savings.savings_progress_summary.target_amount == 400
    assert savings.savings_progress_summary.completion_percentage == 100


async def test_finance_dashboard_metrics(session: AsyncSession) -> None:
    user = await _make_user(session, "dash-finances@example.com")
    account_one = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Checking", type="checking", initial_balance=1000),
    )
    account_two = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Cash", type="cash", initial_balance=0),
    )
    income_category = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Salary", type="income"),
    )
    expense_category = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Food", type="expense"),
    )

    fixtures = [
        (account_one.id, income_category.id, "income", 500, "Pay", date(2026, 6, 17)),
        (account_one.id, expense_category.id, "expense", 200, "Lunch", date(2026, 6, 16)),
        (account_one.id, expense_category.id, "expense", 25, "Old bill", date(2026, 5, 31)),
        (account_two.id, income_category.id, "income", 300, "Side gig", date(2026, 6, 15)),
        (account_two.id, expense_category.id, "expense", 100, "Groceries", date(2026, 6, 14)),
        (account_one.id, income_category.id, "income", 20, "Bonus", date(2026, 6, 13)),
        (account_one.id, expense_category.id, "expense", 10, "Snack", date(2026, 6, 12)),
    ]
    for account_id, category_id, tx_type, amount, description, tx_date in fixtures:
        await finances_service.create_transaction(
            session,
            user_id=user.id,
            payload=TransactionCreate(
                account_id=account_id,
                category_id=category_id,
                type=tx_type,  # type: ignore[arg-type]
                amount=amount,
                description=description,
                transaction_date=tx_date,
            ),
        )

    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(
            account_id=account_one.id,
            category_id=expense_category.id,
            type="expense",
            amount=60,
            description="Subscription",
            frequency="monthly",
            start_date=date(2026, 1, 17),
            end_date=None,
            is_active=True,
        ),
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(
            account_id=account_two.id,
            category_id=income_category.id,
            type="income",
            amount=40,
            description="Allowance",
            frequency="weekly",
            start_date=date(2026, 6, 10),
            end_date=None,
            is_active=True,
        ),
    )

    finances = await dashboard_service.get_finances(session, user_id=user.id, today=TODAY)

    assert finances.monthly_income == 820
    assert finances.monthly_expenses == 310
    assert finances.monthly_balance == 510
    balances = {balance.account_id: balance.current_balance for balance in finances.account_balances}
    assert balances[account_one.id] == 1285
    assert balances[account_two.id] == 200
    assert len(finances.recent_transactions) == 5
    assert [row.transaction_date for row in finances.recent_transactions] == [
        date(2026, 6, 17),
        date(2026, 6, 16),
        date(2026, 6, 15),
        date(2026, 6, 14),
        date(2026, 6, 13),
    ]
    assert finances.insights.as_of == TODAY
    assert finances.insights.month == "2026-06"
    assert finances.insights.top_spending_category is not None
    assert finances.insights.top_spending_category.category_name == "Food"
    assert finances.insights.top_spending_category.amount == 310
    assert finances.insights.top_spending_category.transaction_count == 3
    assert finances.insights.top_spending_category.share_percentage == 100
    assert finances.insights.upcoming_recurring.total_income == 200
    assert finances.insights.upcoming_recurring.total_expenses == 60
    assert finances.insights.upcoming_recurring.net == 140
    assert finances.insights.upcoming_recurring.occurrence_count == 6


async def test_finance_dashboard_month_boundary(session: AsyncSession) -> None:
    user = await _make_user(session, "dash-month@example.com")
    account = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Checking", type="checking", initial_balance=0),
    )
    income_category = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Salary", type="income"),
    )
    expense_category = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Food", type="expense"),
    )

    await finances_service.create_transaction(
        session,
        user_id=user.id,
        payload=TransactionCreate(
            account_id=account.id,
            category_id=income_category.id,
            type="income",  # type: ignore[arg-type]
            amount=100,
            description="May income",
            transaction_date=date(2026, 5, 31),
        ),
    )
    await finances_service.create_transaction(
        session,
        user_id=user.id,
        payload=TransactionCreate(
            account_id=account.id,
            category_id=expense_category.id,
            type="expense",  # type: ignore[arg-type]
            amount=40,
            description="May expense",
            transaction_date=date(2026, 5, 31),
        ),
    )
    await finances_service.create_transaction(
        session,
        user_id=user.id,
        payload=TransactionCreate(
            account_id=account.id,
            category_id=income_category.id,
            type="income",  # type: ignore[arg-type]
            amount=250,
            description="June income",
            transaction_date=date(2026, 6, 1),
        ),
    )
    await finances_service.create_transaction(
        session,
        user_id=user.id,
        payload=TransactionCreate(
            account_id=account.id,
            category_id=expense_category.id,
            type="expense",  # type: ignore[arg-type]
            amount=75,
            description="June expense",
            transaction_date=date(2026, 6, 1),
        ),
    )

    finances = await dashboard_service.get_finances(
        session, user_id=user.id, today=date(2026, 6, 1)
    )

    assert finances.monthly_income == 250
    assert finances.monthly_expenses == 75
    assert finances.monthly_balance == 175


async def test_dashboard_aggregate_paths_are_user_scoped(session: AsyncSession) -> None:
    alice = await _make_user(session, "dash-alice@example.com")
    bob = await _make_user(session, "dash-bob@example.com")

    alice_account = await finances_service.create_account(
        session,
        user_id=alice.id,
        payload=AccountCreate(name="Alice checking", type="checking", initial_balance=1000),
    )
    alice_income_category = await finances_service.create_category(
        session,
        user_id=alice.id,
        payload=CategoryCreate(name="Alice salary", type="income"),
    )
    await finances_service.create_transaction(
        session,
        user_id=alice.id,
        payload=TransactionCreate(
            account_id=alice_account.id,
            category_id=alice_income_category.id,
            type="income",  # type: ignore[arg-type]
            amount=500,
            description="Alice pay",
            transaction_date=TODAY,
        ),
    )
    await habits_service.create_habit(
        session,
        user_id=alice.id,
        payload=HabitCreate(title="Alice habit", tracking_mode="boolean"),
    )
    await savings_service.create_goal(
        session,
        user_id=alice.id,
        payload=SavingGoalCreate(name="Alice goal", target_amount=100),
    )

    summary = await dashboard_service.get_summary(session, user_id=bob.id, today=TODAY)
    finances = await dashboard_service.get_finances(session, user_id=bob.id, today=TODAY)

    assert summary.habits.total_active_habits == 0
    assert summary.savings.total_savings_contributed == 0
    assert summary.finances.monthly_income == 0
    assert summary.finances.account_balances == []
    assert summary.finances.insights.top_spending_category is None
    assert summary.finances.insights.upcoming_recurring.occurrence_count == 0
    assert finances.account_balances == []
