from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.finances.models import (
    ENTRY_EXPENSE,
    ENTRY_INCOME,
    Account,
    Category,
    MonthlyCategoryBudget,
    RecurringTransaction,
    Transaction,
)


def _signed_amount_expression():
    return case(
        (Transaction.type == ENTRY_INCOME, Transaction.amount),
        else_=-Transaction.amount,
    )


def _recurring_signed_amount_expression():
    return case(
        (RecurringTransaction.type == ENTRY_INCOME, RecurringTransaction.amount),
        else_=-RecurringTransaction.amount,
    )


# ---------- Accounts ----------

async def get_account_by_id_and_user(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Account | None:
    stmt = select(Account).where(Account.id == account_id, Account.user_id == user_id)
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_accounts_for_user(session: AsyncSession, *, user_id: uuid.UUID) -> list[Account]:
    stmt = (
        select(Account)
        .where(Account.user_id == user_id)
        .order_by(Account.created_at.asc(), Account.id.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def get_account_balance(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    stmt = (
        select(func.coalesce(func.sum(_signed_amount_expression()), 0))
        .select_from(Transaction)
        .where(Transaction.account_id == account_id, Transaction.user_id == user_id)
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def get_account_balance_map_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[uuid.UUID, int]:
    stmt = (
        select(
            Transaction.account_id,
            func.coalesce(func.sum(_signed_amount_expression()), 0),
        )
        .where(Transaction.user_id == user_id)
        .group_by(Transaction.account_id)
    )
    result = await session.execute(stmt)
    return {row[0]: int(row[1] or 0) for row in result.all()}


async def create_account(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    type: str,
    initial_balance: int,
) -> Account:
    record = Account(
        user_id=user_id,
        name=name,
        type=type,
        initial_balance=initial_balance,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def update_account(session: AsyncSession, account: Account, *, fields: dict) -> Account:
    for key, value in fields.items():
        setattr(account, key, value)
    await session.commit()
    await session.refresh(account)
    return account


async def delete_account(session: AsyncSession, account: Account) -> None:
    await session.delete(account)
    await session.commit()


async def count_transactions_for_account(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    stmt = select(func.count()).select_from(Transaction).where(
        Transaction.account_id == account_id,
        Transaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def count_recurring_for_account(
    session: AsyncSession,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    stmt = select(func.count()).select_from(RecurringTransaction).where(
        RecurringTransaction.account_id == account_id,
        RecurringTransaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


# ---------- Categories ----------

async def get_category_by_id_and_user(
    session: AsyncSession,
    *,
    category_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Category | None:
    stmt = select(Category).where(
        Category.id == category_id,
        Category.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_categories_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[Category]:
    stmt = (
        select(Category)
        .where(Category.user_id == user_id)
        .order_by(Category.created_at.asc(), Category.id.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    name: str,
    type: str,
) -> Category:
    record = Category(user_id=user_id, name=name, type=type)
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def update_category(session: AsyncSession, category: Category, *, fields: dict) -> Category:
    for key, value in fields.items():
        setattr(category, key, value)
    await session.commit()
    await session.refresh(category)
    return category


async def delete_category(session: AsyncSession, category: Category) -> None:
    await session.delete(category)
    await session.commit()


async def count_transactions_for_category(
    session: AsyncSession,
    *,
    category_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    stmt = select(func.count()).select_from(Transaction).where(
        Transaction.category_id == category_id,
        Transaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


async def count_recurring_for_category(
    session: AsyncSession,
    *,
    category_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    stmt = select(func.count()).select_from(RecurringTransaction).where(
        RecurringTransaction.category_id == category_id,
        RecurringTransaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


# ---------- Monthly budgets ----------

async def get_monthly_budget_by_id_and_user(
    session: AsyncSession,
    *,
    budget_id: uuid.UUID,
    user_id: uuid.UUID,
) -> MonthlyCategoryBudget | None:
    stmt = select(MonthlyCategoryBudget).where(
        MonthlyCategoryBudget.id == budget_id,
        MonthlyCategoryBudget.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_monthly_budgets_for_user_month(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    month_start: date,
) -> list[tuple[MonthlyCategoryBudget, str]]:
    stmt = (
        select(MonthlyCategoryBudget, Category.name)
        .join(Category, Category.id == MonthlyCategoryBudget.category_id)
        .where(
            MonthlyCategoryBudget.user_id == user_id,
            MonthlyCategoryBudget.month_start == month_start,
        )
        .order_by(Category.name.asc(), Category.id.asc())
    )
    result = await session.execute(stmt)
    return [(row[0], row[1]) for row in result.all()]


async def create_monthly_budget(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    month_start: date,
    amount: int,
) -> MonthlyCategoryBudget:
    record = MonthlyCategoryBudget(
        user_id=user_id,
        category_id=category_id,
        month_start=month_start,
        amount=amount,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def update_monthly_budget(
    session: AsyncSession,
    budget: MonthlyCategoryBudget,
    *,
    amount: int,
) -> MonthlyCategoryBudget:
    budget.amount = amount
    await session.commit()
    await session.refresh(budget)
    return budget


async def delete_monthly_budget(session: AsyncSession, budget: MonthlyCategoryBudget) -> None:
    await session.delete(budget)
    await session.commit()


async def count_monthly_budgets_for_category(
    session: AsyncSession,
    *,
    category_id: uuid.UUID,
    user_id: uuid.UUID,
) -> int:
    stmt = select(func.count()).select_from(MonthlyCategoryBudget).where(
        MonthlyCategoryBudget.category_id == category_id,
        MonthlyCategoryBudget.user_id == user_id,
    )
    result = await session.execute(stmt)
    return int(result.scalar_one() or 0)


# ---------- Transactions ----------

async def get_transaction_by_id_and_user(
    session: AsyncSession,
    *,
    transaction_id: uuid.UUID,
    user_id: uuid.UUID,
) -> Transaction | None:
    stmt = select(Transaction).where(
        Transaction.id == transaction_id,
        Transaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_transactions_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[Transaction]:
    stmt = select(Transaction).where(Transaction.user_id == user_id)
    if account_id is not None:
        stmt = stmt.where(Transaction.account_id == account_id)
    if category_id is not None:
        stmt = stmt.where(Transaction.category_id == category_id)
    if from_date is not None:
        stmt = stmt.where(Transaction.transaction_date >= from_date)
    if to_date is not None:
        stmt = stmt.where(Transaction.transaction_date <= to_date)
    stmt = stmt.order_by(
        Transaction.transaction_date.asc(),
        Transaction.created_at.asc(),
        Transaction.id.asc(),
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def create_transaction(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
    type: str,
    amount: int,
    description: str | None,
    transaction_date: date,
) -> Transaction:
    record = Transaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        type=type,
        amount=amount,
        description=description,
        transaction_date=transaction_date,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def update_transaction(
    session: AsyncSession,
    transaction: Transaction,
    *,
    fields: dict,
) -> Transaction:
    for key, value in fields.items():
        setattr(transaction, key, value)
    await session.commit()
    await session.refresh(transaction)
    return transaction


async def delete_transaction(session: AsyncSession, transaction: Transaction) -> None:
    await session.delete(transaction)
    await session.commit()


async def get_expense_spending_by_category(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> list[tuple[uuid.UUID, str, int, int]]:
    total_amount = func.sum(Transaction.amount)
    transaction_count = func.count(Transaction.id)
    stmt = (
        select(
            Category.id,
            Category.name,
            total_amount.label("amount"),
            transaction_count.label("transaction_count"),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == ENTRY_EXPENSE,
            Transaction.transaction_date >= period_start,
            Transaction.transaction_date <= period_end,
        )
        .group_by(Category.id, Category.name)
        .having(total_amount > 0)
        .order_by(total_amount.desc(), Category.name.asc(), Category.id.asc())
    )
    result = await session.execute(stmt)
    return [
        (row[0], row[1], int(row[2]), int(row[3]))
        for row in result.all()
    ]


# ---------- Recurring transactions ----------

async def get_recurring_by_id_and_user(
    session: AsyncSession,
    *,
    recurring_id: uuid.UUID,
    user_id: uuid.UUID,
) -> RecurringTransaction | None:
    stmt = select(RecurringTransaction).where(
        RecurringTransaction.id == recurring_id,
        RecurringTransaction.user_id == user_id,
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def list_recurring_for_user(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> list[RecurringTransaction]:
    stmt = (
        select(RecurringTransaction)
        .where(RecurringTransaction.user_id == user_id)
        .order_by(RecurringTransaction.created_at.asc(), RecurringTransaction.id.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())


async def list_active_recurring_overlapping_window(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    period_start: date,
    period_end: date,
) -> list[tuple[RecurringTransaction, str, str]]:
    """Load active user rules that can produce an occurrence in the window."""
    stmt = (
        select(RecurringTransaction, Account.name, Category.name)
        .join(Account, Account.id == RecurringTransaction.account_id)
        .join(Category, Category.id == RecurringTransaction.category_id)
        .where(
            RecurringTransaction.user_id == user_id,
            RecurringTransaction.is_active.is_(True),
            RecurringTransaction.start_date <= period_end,
            (
                RecurringTransaction.end_date.is_(None)
                | (RecurringTransaction.end_date >= period_start)
            ),
        )
    )
    result = await session.execute(stmt)
    return [(row[0], row[1], row[2]) for row in result.all()]


async def create_recurring(
    session: AsyncSession,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    category_id: uuid.UUID,
    type: str,
    amount: int,
    description: str | None,
    frequency: str,
    start_date: date,
    end_date: date | None,
    is_active: bool,
) -> RecurringTransaction:
    record = RecurringTransaction(
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        type=type,
        amount=amount,
        description=description,
        frequency=frequency,
        start_date=start_date,
        end_date=end_date,
        is_active=is_active,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)
    return record


async def update_recurring(
    session: AsyncSession,
    recurring: RecurringTransaction,
    *,
    fields: dict,
) -> RecurringTransaction:
    for key, value in fields.items():
        setattr(recurring, key, value)
    await session.commit()
    await session.refresh(recurring)
    return recurring


async def delete_recurring(session: AsyncSession, recurring: RecurringTransaction) -> None:
    await session.delete(recurring)
    await session.commit()


def signed_amount_for_type(tx_type: str, amount: int) -> int:
    return amount if tx_type == ENTRY_INCOME else -amount
