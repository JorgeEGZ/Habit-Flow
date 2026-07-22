"""Service tests for the finances module."""
from __future__ import annotations

from datetime import date

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    AccountNotFound,
    CategoryNotFound,
    RecurringTransactionNotFound,
    ResourceInUse,
    TransactionNotFound,
    ValidationError,
)
from app.core.security import hash_password
from app.modules.finances import service as finances_service
from app.modules.finances.schemas import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryUpdate,
    RecurringTransactionCreate,
    RecurringTransactionUpdate,
    TransactionCreate,
    TransactionUpdate,
)
from app.modules.users.models import User


async def _make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash=hash_password("correcthorse"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def test_account_crud_and_dynamic_balance(session: AsyncSession) -> None:
    user = await _make_user(session, "fa1@example.com")
    account = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Cash", type="cash", initial_balance=1000),
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
            type="income",
            amount=500,
            description="Paycheck",
            transaction_date=date(2026, 6, 17),
        ),
    )
    await finances_service.create_transaction(
        session,
        user_id=user.id,
        payload=TransactionCreate(
            account_id=account.id,
            category_id=expense_category.id,
            type="expense",
            amount=200,
            description="Lunch",
            transaction_date=date(2026, 6, 18),
        ),
    )

    refreshed = await finances_service.get_account(session, user_id=user.id, account_id=account.id)
    assert refreshed.current_balance == 1300

    updated = await finances_service.update_account(
        session,
        user_id=user.id,
        account_id=account.id,
        payload=AccountUpdate(name="Wallet"),
    )
    assert updated.name == "Wallet"
    assert updated.current_balance == 1300


async def test_spending_by_category_aggregates_monthly_expenses(session: AsyncSession) -> None:
    user = await _make_user(session, "spending-owner@example.com")
    other_user = await _make_user(session, "spending-other@example.com")
    account = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Cash", type="cash", initial_balance=0),
    )
    other_account = await finances_service.create_account(
        session,
        user_id=other_user.id,
        payload=AccountCreate(name="Other cash", type="cash", initial_balance=0),
    )
    food = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Food", type="expense"),
    )
    transport = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Transport", type="expense"),
    )
    income = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Salary", type="income"),
    )
    other_food = await finances_service.create_category(
        session,
        user_id=other_user.id,
        payload=CategoryCreate(name="Food", type="expense"),
    )

    fixtures = [
        (account.id, food.id, "expense", 100, date(2026, 7, 1)),
        (account.id, food.id, "expense", 50, date(2026, 7, 31)),
        (account.id, transport.id, "expense", 150, date(2026, 7, 16)),
        (account.id, food.id, "expense", 900, date(2026, 6, 30)),
        (account.id, food.id, "expense", 800, date(2026, 8, 1)),
        (account.id, income.id, "income", 1000, date(2026, 7, 10)),
    ]
    for account_id, category_id, entry_type, amount, transaction_date in fixtures:
        await finances_service.create_transaction(
            session,
            user_id=user.id,
            payload=TransactionCreate(
                account_id=account_id,
                category_id=category_id,
                type=entry_type,
                amount=amount,
                description=None,
                transaction_date=transaction_date,
            ),
        )
    await finances_service.create_transaction(
        session,
        user_id=other_user.id,
        payload=TransactionCreate(
            account_id=other_account.id,
            category_id=other_food.id,
            type="expense",
            amount=777,
            description=None,
            transaction_date=date(2026, 7, 15),
        ),
    )

    summary = await finances_service.get_spending_by_category(
        session,
        user_id=user.id,
        month="2026-07",
    )

    assert summary.month == "2026-07"
    assert summary.period_start == date(2026, 7, 1)
    assert summary.period_end == date(2026, 7, 31)
    assert summary.total_expenses == 300
    assert [item.category_name for item in summary.categories] == ["Food", "Transport"]
    assert [(item.amount, item.transaction_count) for item in summary.categories] == [
        (150, 2),
        (150, 1),
    ]
    assert [item.share_percentage for item in summary.categories] == [50.0, 50.0]

    empty_summary = await finances_service.get_spending_by_category(
        session,
        user_id=user.id,
        month="2026-09",
    )
    assert empty_summary.total_expenses == 0
    assert empty_summary.categories == []

    default_month_summary = await finances_service.get_spending_by_category(
        session,
        user_id=user.id,
        today=date(2026, 7, 20),
    )
    assert default_month_summary.month == "2026-07"


@pytest.mark.parametrize(
    ("start_date", "period_start", "period_end", "expected"),
    [
        (date(2026, 1, 28), date(2026, 2, 1), date(2026, 3, 31), [date(2026, 2, 28), date(2026, 3, 28)]),
        (date(2024, 1, 29), date(2024, 2, 1), date(2024, 3, 31), [date(2024, 2, 29), date(2024, 3, 29)]),
        (date(2026, 1, 30), date(2026, 2, 1), date(2026, 3, 31), [date(2026, 2, 28), date(2026, 3, 30)]),
        (date(2026, 1, 31), date(2026, 2, 1), date(2026, 3, 31), [date(2026, 2, 28), date(2026, 3, 31)]),
    ],
)
def test_monthly_occurrences_keep_the_permanent_start_day_anchor(
    start_date: date,
    period_start: date,
    period_end: date,
    expected: list[date],
) -> None:
    assert finances_service._iter_monthly_occurrences(
        start_date=start_date,
        end_date=None,
        period_start=period_start,
        period_end=period_end,
    ) == expected


async def test_upcoming_recurring_projects_active_user_rules_without_writes(
    session: AsyncSession,
) -> None:
    user = await _make_user(session, "upcoming-owner@example.com")
    other_user = await _make_user(session, "upcoming-other@example.com")
    account = await finances_service.create_account(
        session, user_id=user.id, payload=AccountCreate(name="Cash", type="cash", initial_balance=0)
    )
    other_account = await finances_service.create_account(
        session, user_id=other_user.id, payload=AccountCreate(name="Other", type="cash", initial_balance=0)
    )
    expense = await finances_service.create_category(
        session, user_id=user.id, payload=CategoryCreate(name="Housing", type="expense")
    )
    bills = await finances_service.create_category(
        session, user_id=user.id, payload=CategoryCreate(name="Bills", type="expense")
    )
    income = await finances_service.create_category(
        session, user_id=user.id, payload=CategoryCreate(name="Salary", type="income")
    )
    other_expense = await finances_service.create_category(
        session, user_id=other_user.id, payload=CategoryCreate(name="Other", type="expense")
    )

    daily = await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=expense.id, type="expense", amount=100, description="Daily", frequency="daily", start_date=date(2026, 7, 22), end_date=date(2026, 7, 23), is_active=True),
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=bills.id, type="expense", amount=25, description="Utilities", frequency="daily", start_date=date(2026, 7, 22), end_date=date(2026, 7, 22), is_active=True),
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=income.id, type="income", amount=200, description="Weekly", frequency="weekly", start_date=date(2026, 7, 18), end_date=None, is_active=True),
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=expense.id, type="expense", amount=850, description="Rent", frequency="monthly", start_date=date(2026, 1, 31), end_date=None, is_active=True),
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=income.id, type="income", amount=300, description="Salary", frequency="monthly", start_date=date(2026, 7, 22), end_date=None, is_active=True),
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=income.id, type="income", amount=50, description="Future", frequency="daily", start_date=date(2026, 8, 20), end_date=date(2026, 8, 20), is_active=True),
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=expense.id, type="expense", amount=999, description="Paused", frequency="daily", start_date=date(2026, 7, 22), end_date=None, is_active=False),
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=expense.id, type="expense", amount=999, description="Expired", frequency="daily", start_date=date(2026, 7, 1), end_date=date(2026, 7, 21), is_active=True),
    )
    await finances_service.create_recurring(
        session,
        user_id=other_user.id,
        payload=RecurringTransactionCreate(account_id=other_account.id, category_id=other_expense.id, type="expense", amount=999, description="Other", frequency="daily", start_date=date(2026, 7, 22), end_date=None, is_active=True),
    )

    summary = await finances_service.get_upcoming_recurring(
        session, user_id=user.id, days=30, today=date(2026, 7, 22)
    )

    assert summary.period_start == date(2026, 7, 22)
    assert summary.period_end == date(2026, 8, 20)
    assert summary.total_income == 1150
    assert summary.total_expenses == 1075
    assert summary.net == 75
    assert [group.date for group in summary.date_groups] == [
        date(2026, 7, 22), date(2026, 7, 23), date(2026, 7, 25), date(2026, 7, 31),
        date(2026, 8, 1), date(2026, 8, 8), date(2026, 8, 15), date(2026, 8, 20),
    ]
    assert [item.description for item in summary.date_groups[0].occurrences] == ["Utilities", "Daily", "Salary"]
    assert summary.date_groups[3].occurrences[0].description == "Rent"
    assert daily.last_generated_at is None
    assert await finances_service.list_transactions(session, user_id=user.id) == []


async def test_upcoming_recurring_seven_day_boundary_and_weekly_anchor(session: AsyncSession) -> None:
    user = await _make_user(session, "upcoming-boundary@example.com")
    account = await finances_service.create_account(
        session, user_id=user.id, payload=AccountCreate(name="Cash", type="cash", initial_balance=0)
    )
    category = await finances_service.create_category(
        session, user_id=user.id, payload=CategoryCreate(name="Food", type="expense")
    )
    await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(account_id=account.id, category_id=category.id, type="expense", amount=10, description="Weekly", frequency="weekly", start_date=date(2026, 7, 18), end_date=None, is_active=True),
    )

    summary = await finances_service.get_upcoming_recurring(
        session, user_id=user.id, days=7, today=date(2026, 7, 22)
    )

    assert summary.period_end == date(2026, 7, 28)
    assert [group.date for group in summary.date_groups] == [date(2026, 7, 25)]


async def test_category_crud_and_type_validation(session: AsyncSession) -> None:
    user = await _make_user(session, "fa2@example.com")
    account = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Bank", type="checking", initial_balance=0),
    )
    category = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Salary", type="income"),
    )
    updated = await finances_service.update_category(
        session,
        user_id=user.id,
        category_id=category.id,
        payload=CategoryUpdate(name="Main Salary"),
    )
    assert updated.name == "Main Salary"

    with pytest.raises(ValidationError):
        await finances_service.create_transaction(
            session,
            user_id=user.id,
            payload=TransactionCreate(
                account_id=account.id,
                category_id=category.id,
                type="expense",
                amount=100,
                description="Mismatch",
                transaction_date=date(2026, 6, 17),
            ),
        )


async def test_transaction_crud_and_ownership(session: AsyncSession) -> None:
    alice = await _make_user(session, "fa3a@example.com")
    bob = await _make_user(session, "fa3b@example.com")
    account = await finances_service.create_account(
        session,
        user_id=alice.id,
        payload=AccountCreate(name="Cash", type="cash", initial_balance=0),
    )
    category = await finances_service.create_category(
        session,
        user_id=alice.id,
        payload=CategoryCreate(name="Salary", type="income"),
    )
    tx = await finances_service.create_transaction(
        session,
        user_id=alice.id,
        payload=TransactionCreate(
            account_id=account.id,
            category_id=category.id,
            type="income",
            amount=250,
            description="Freelance",
            transaction_date=date(2026, 6, 17),
        ),
    )

    with pytest.raises(TransactionNotFound):
        await finances_service.get_transaction(session, user_id=bob.id, transaction_id=tx.id)

    updated = await finances_service.update_transaction(
        session,
        user_id=alice.id,
        transaction_id=tx.id,
        payload=TransactionUpdate(amount=300, description="Updated"),
    )
    assert updated.amount == 300
    assert updated.description == "Updated"

    await finances_service.delete_transaction(session, user_id=alice.id, transaction_id=tx.id)
    with pytest.raises(TransactionNotFound):
        await finances_service.get_transaction(session, user_id=alice.id, transaction_id=tx.id)


async def test_delete_account_blocked_when_transactions_exist(session: AsyncSession) -> None:
    user = await _make_user(session, "fa4@example.com")
    account = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Cash", type="cash", initial_balance=0),
    )
    category = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Salary", type="income"),
    )
    await finances_service.create_transaction(
        session,
        user_id=user.id,
        payload=TransactionCreate(
            account_id=account.id,
            category_id=category.id,
            type="income",
            amount=100,
            description="Income",
            transaction_date=date(2026, 6, 17),
        ),
    )

    with pytest.raises(ResourceInUse):
        await finances_service.delete_account(session, user_id=user.id, account_id=account.id)


async def test_delete_category_blocked_when_transactions_exist(session: AsyncSession) -> None:
    user = await _make_user(session, "fa5@example.com")
    account = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Cash", type="cash", initial_balance=0),
    )
    category = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Food", type="expense"),
    )
    await finances_service.create_transaction(
        session,
        user_id=user.id,
        payload=TransactionCreate(
            account_id=account.id,
            category_id=category.id,
            type="expense",
            amount=100,
            description="Lunch",
            transaction_date=date(2026, 6, 17),
        ),
    )

    with pytest.raises(ResourceInUse):
        await finances_service.delete_category(session, user_id=user.id, category_id=category.id)


async def test_recurring_rules_do_not_generate_transactions(session: AsyncSession) -> None:
    user = await _make_user(session, "fa6@example.com")
    account = await finances_service.create_account(
        session,
        user_id=user.id,
        payload=AccountCreate(name="Bank", type="checking", initial_balance=0),
    )
    category = await finances_service.create_category(
        session,
        user_id=user.id,
        payload=CategoryCreate(name="Salary", type="income"),
    )
    recurring = await finances_service.create_recurring(
        session,
        user_id=user.id,
        payload=RecurringTransactionCreate(
            account_id=account.id,
            category_id=category.id,
            type="income",
            amount=1000,
            description="Monthly pay",
            frequency="monthly",
            start_date=date(2026, 6, 1),
            end_date=None,
            is_active=True,
        ),
    )

    transactions = await finances_service.list_transactions(session, user_id=user.id)
    recurring_rules = await finances_service.list_recurring(session, user_id=user.id)

    assert recurring.id is not None
    assert transactions == []
    assert len(recurring_rules) == 1


async def test_recurring_crud_and_ownership(session: AsyncSession) -> None:
    alice = await _make_user(session, "fa7a@example.com")
    bob = await _make_user(session, "fa7b@example.com")
    account = await finances_service.create_account(
        session,
        user_id=alice.id,
        payload=AccountCreate(name="Bank", type="checking", initial_balance=0),
    )
    category = await finances_service.create_category(
        session,
        user_id=alice.id,
        payload=CategoryCreate(name="Salary", type="income"),
    )
    rule = await finances_service.create_recurring(
        session,
        user_id=alice.id,
        payload=RecurringTransactionCreate(
            account_id=account.id,
            category_id=category.id,
            type="income",
            amount=1000,
            description="Monthly pay",
            frequency="monthly",
            start_date=date(2026, 6, 1),
            end_date=None,
            is_active=True,
        ),
    )

    with pytest.raises(RecurringTransactionNotFound):
        await finances_service.get_recurring(session, user_id=bob.id, recurring_id=rule.id)

    updated = await finances_service.update_recurring(
        session,
        user_id=alice.id,
        recurring_id=rule.id,
        payload=RecurringTransactionUpdate(is_active=False),
    )
    assert updated.is_active is False

    await finances_service.delete_recurring(session, user_id=alice.id, recurring_id=rule.id)
    with pytest.raises(RecurringTransactionNotFound):
        await finances_service.get_recurring(session, user_id=alice.id, recurring_id=rule.id)
