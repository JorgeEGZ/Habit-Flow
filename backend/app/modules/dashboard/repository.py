from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finances.models import Account, Category, Transaction, ENTRY_EXPENSE, ENTRY_INCOME
from app.modules.habits.models import Habit, HabitLog, TRACKING_BOOLEAN, TRACKING_NUMERIC
from app.modules.savings.models import SavingContribution, SavingGoal


def _signed_transaction_amount():
    return case(
        (Transaction.type == ENTRY_INCOME, Transaction.amount),
        else_=-Transaction.amount,
    )


async def fetch_habit_rows(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[tuple[Habit, HabitLog | None]]:
    stmt = (
        select(Habit, HabitLog)
        .outerjoin(HabitLog, HabitLog.habit_id == Habit.id)
        .where(Habit.user_id == user_id)
        .order_by(
            Habit.created_at.asc(),
            Habit.id.asc(),
            HabitLog.logged_on.asc(),
            HabitLog.created_at.asc(),
            HabitLog.id.asc(),
        )
    )
    result = await session.execute(stmt)
    rows = result.all()
    return [(row[0], row[1]) for row in rows]


async def fetch_savings_rows(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[tuple[SavingGoal, int]]:
    stmt = (
        select(
            SavingGoal,
            func.coalesce(func.sum(SavingContribution.amount), 0).label("current_amount"),
        )
        .outerjoin(SavingContribution, SavingContribution.saving_goal_id == SavingGoal.id)
        .where(SavingGoal.user_id == user_id)
        .group_by(SavingGoal.id)
        .order_by(SavingGoal.created_at.asc(), SavingGoal.id.asc())
    )
    result = await session.execute(stmt)
    return [(row[0], int(row[1] or 0)) for row in result.all()]


async def fetch_finance_monthly_summary(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    month_start: date,
    next_month_start: date,
) -> tuple[int, int]:
    income_stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= month_start,
            Transaction.transaction_date < next_month_start,
            Transaction.type == ENTRY_INCOME,
        )
    )
    expense_stmt = (
        select(func.coalesce(func.sum(Transaction.amount), 0))
        .where(
            Transaction.user_id == user_id,
            Transaction.transaction_date >= month_start,
            Transaction.transaction_date < next_month_start,
            Transaction.type == ENTRY_EXPENSE,
        )
    )
    income_result = await session.execute(income_stmt)
    expense_result = await session.execute(expense_stmt)
    return int(income_result.scalar_one() or 0), int(expense_result.scalar_one() or 0)


async def fetch_account_balances(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[tuple[Account, int]]:
    movement = func.coalesce(func.sum(_signed_transaction_amount()), 0)
    stmt = (
        select(Account, (Account.initial_balance + movement).label("current_balance"))
        .outerjoin(
            Transaction,
            (Transaction.account_id == Account.id) & (Transaction.user_id == user_id),
        )
        .where(Account.user_id == user_id)
        .group_by(Account.id)
        .order_by(Account.created_at.asc(), Account.id.asc())
    )
    result = await session.execute(stmt)
    return [(row[0], int(row[1] or 0)) for row in result.all()]


async def fetch_recent_transactions(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    limit: int,
) -> list[tuple[Transaction, str, str]]:
    stmt = (
        select(Transaction, Account.name, Category.name)
        .join(Account, Account.id == Transaction.account_id)
        .join(Category, Category.id == Transaction.category_id)
        .where(Transaction.user_id == user_id)
        .order_by(
            Transaction.transaction_date.desc(),
            Transaction.created_at.desc(),
            Transaction.id.desc(),
        )
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [(row[0], row[1], row[2]) for row in result.all()]
