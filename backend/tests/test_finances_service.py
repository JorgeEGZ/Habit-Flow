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
