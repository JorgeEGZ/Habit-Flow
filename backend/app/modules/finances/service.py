from __future__ import annotations

import uuid
from datetime import date

from app.core.exceptions import (
    AccountNotFound,
    CategoryNotFound,
    RecurringTransactionNotFound,
    ResourceInUse,
    TransactionNotFound,
    ValidationError,
)
from app.modules.finances import repository as finances_repo
from app.modules.finances.models import Account, Category, RecurringTransaction, Transaction
from app.modules.finances.schemas import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    RecurringTransactionCreate,
    RecurringTransactionRead,
    RecurringTransactionUpdate,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
)


def _validate_positive_amount(amount: int, *, label: str) -> None:
    if amount <= 0:
        raise ValidationError(f"{label} must be greater than zero.")


def _validate_nonnegative_amount(amount: int, *, label: str) -> None:
    if amount < 0:
        raise ValidationError(f"{label} must be zero or greater.")


def _attach_current_balance(account: Account, movement: int) -> Account:
    account.current_balance = account.initial_balance + movement
    return account


def _validate_category_match(entry_type: str, category: Category) -> None:
    if category.type != entry_type:
        raise ValidationError("Category type must match transaction type.")


async def _get_account_or_404(session, *, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    account = await finances_repo.get_account_by_id_and_user(
        session, account_id=account_id, user_id=user_id
    )
    if not account:
        raise AccountNotFound()
    return account


async def _get_category_or_404(
    session,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    category = await finances_repo.get_category_by_id_and_user(
        session, category_id=category_id, user_id=user_id
    )
    if not category:
        raise CategoryNotFound()
    return category


async def _get_transaction_or_404(
    session,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> Transaction:
    transaction = await finances_repo.get_transaction_by_id_and_user(
        session, transaction_id=transaction_id, user_id=user_id
    )
    if not transaction:
        raise TransactionNotFound()
    return transaction


async def _get_recurring_or_404(
    session,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
) -> RecurringTransaction:
    recurring = await finances_repo.get_recurring_by_id_and_user(
        session, recurring_id=recurring_id, user_id=user_id
    )
    if not recurring:
        raise RecurringTransactionNotFound()
    return recurring


def _validate_update_type_change_block(
    *,
    existing_type: str,
    new_type: str | None,
    dependents: int,
) -> None:
    if new_type is not None and new_type != existing_type and dependents > 0:
        raise ResourceInUse("This category type cannot be changed while it is in use.")


# ---------- Accounts ----------

async def list_accounts(session, *, user_id: uuid.UUID) -> list[Account]:
    accounts = await finances_repo.list_accounts_for_user(session, user_id=user_id)
    balance_map = await finances_repo.get_account_balance_map_for_user(
        session, user_id=user_id
    )
    return [
        _attach_current_balance(account, balance_map.get(account.id, 0))
        for account in accounts
    ]


async def get_account(session, *, user_id: uuid.UUID, account_id: uuid.UUID) -> Account:
    account = await _get_account_or_404(session, user_id=user_id, account_id=account_id)
    movement = await finances_repo.get_account_balance(
        session, account_id=account.id, user_id=user_id
    )
    return _attach_current_balance(account, movement)


async def create_account(
    session,
    *,
    user_id: uuid.UUID,
    payload: AccountCreate,
) -> Account:
    _validate_nonnegative_amount(payload.initial_balance, label="Initial balance")
    account = await finances_repo.create_account(
        session,
        user_id=user_id,
        name=payload.name,
        type=payload.type,
        initial_balance=payload.initial_balance,
    )
    return _attach_current_balance(account, 0)


async def update_account(
    session,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID,
    payload: AccountUpdate,
) -> Account:
    account = await _get_account_or_404(session, user_id=user_id, account_id=account_id)
    fields = payload.model_dump(exclude_unset=True)
    if "initial_balance" in fields:
        _validate_nonnegative_amount(fields["initial_balance"], label="Initial balance")
    updated = await finances_repo.update_account(session, account, fields=fields)
    movement = await finances_repo.get_account_balance(
        session, account_id=updated.id, user_id=user_id
    )
    return _attach_current_balance(updated, movement)


async def delete_account(session, *, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
    account = await _get_account_or_404(session, user_id=user_id, account_id=account_id)
    if await finances_repo.count_transactions_for_account(
        session, account_id=account.id, user_id=user_id
    ) > 0:
        raise ResourceInUse("Account has transactions.")
    if await finances_repo.count_recurring_for_account(
        session, account_id=account.id, user_id=user_id
    ) > 0:
        raise ResourceInUse("Account has recurring transactions.")
    await finances_repo.delete_account(session, account)


# ---------- Categories ----------

async def list_categories(session, *, user_id: uuid.UUID) -> list[Category]:
    return await finances_repo.list_categories_for_user(session, user_id=user_id)


async def get_category(
    session,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
) -> Category:
    return await _get_category_or_404(session, user_id=user_id, category_id=category_id)


async def create_category(
    session,
    *,
    user_id: uuid.UUID,
    payload: CategoryCreate,
) -> Category:
    return await finances_repo.create_category(
        session,
        user_id=user_id,
        name=payload.name,
        type=payload.type,
    )


async def update_category(
    session,
    *,
    user_id: uuid.UUID,
    category_id: uuid.UUID,
    payload: CategoryUpdate,
) -> Category:
    category = await _get_category_or_404(session, user_id=user_id, category_id=category_id)
    fields = payload.model_dump(exclude_unset=True)

    if "type" in fields and fields["type"] != category.type:
        tx_count = await finances_repo.count_transactions_for_category(
            session, category_id=category.id, user_id=user_id
        )
        recurring_count = await finances_repo.count_recurring_for_category(
            session, category_id=category.id, user_id=user_id
        )
        if tx_count > 0 or recurring_count > 0:
            raise ResourceInUse("Category type cannot be changed while it is in use.")

    return await finances_repo.update_category(session, category, fields=fields)


async def delete_category(session, *, user_id: uuid.UUID, category_id: uuid.UUID) -> None:
    category = await _get_category_or_404(session, user_id=user_id, category_id=category_id)
    if await finances_repo.count_transactions_for_category(
        session, category_id=category.id, user_id=user_id
    ) > 0:
        raise ResourceInUse("Category has transactions.")
    if await finances_repo.count_recurring_for_category(
        session, category_id=category.id, user_id=user_id
    ) > 0:
        raise ResourceInUse("Category has recurring transactions.")
    await finances_repo.delete_category(session, category)


# ---------- Transactions ----------

async def list_transactions(
    session,
    *,
    user_id: uuid.UUID,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[Transaction]:
    return await finances_repo.list_transactions_for_user(
        session,
        user_id=user_id,
        account_id=account_id,
        category_id=category_id,
        from_date=from_date,
        to_date=to_date,
    )


async def get_transaction(
    session,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
) -> Transaction:
    return await _get_transaction_or_404(
        session, user_id=user_id, transaction_id=transaction_id
    )


async def create_transaction(
    session,
    *,
    user_id: uuid.UUID,
    payload: TransactionCreate,
) -> Transaction:
    _validate_positive_amount(payload.amount, label="Amount")
    account = await _get_account_or_404(session, user_id=user_id, account_id=payload.account_id)
    category = await _get_category_or_404(session, user_id=user_id, category_id=payload.category_id)
    _validate_category_match(payload.type, category)
    return await finances_repo.create_transaction(
        session,
        user_id=user_id,
        account_id=account.id,
        category_id=category.id,
        type=payload.type,
        amount=payload.amount,
        description=payload.description,
        transaction_date=payload.transaction_date,
    )


async def update_transaction(
    session,
    *,
    user_id: uuid.UUID,
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
) -> Transaction:
    transaction = await _get_transaction_or_404(
        session, user_id=user_id, transaction_id=transaction_id
    )
    fields = payload.model_dump(exclude_unset=True)
    amount = fields.get("amount", transaction.amount)
    _validate_positive_amount(amount, label="Amount")

    account_id = fields.get("account_id", transaction.account_id)
    category_id = fields.get("category_id", transaction.category_id)
    entry_type = fields.get("type", transaction.type)

    account = await _get_account_or_404(session, user_id=user_id, account_id=account_id)
    category = await _get_category_or_404(session, user_id=user_id, category_id=category_id)
    _validate_category_match(entry_type, category)

    fields["account_id"] = account.id
    fields["category_id"] = category.id
    fields["type"] = entry_type
    fields["amount"] = amount
    return await finances_repo.update_transaction(session, transaction, fields=fields)


async def delete_transaction(session, *, user_id: uuid.UUID, transaction_id: uuid.UUID) -> None:
    transaction = await _get_transaction_or_404(
        session, user_id=user_id, transaction_id=transaction_id
    )
    await finances_repo.delete_transaction(session, transaction)


# ---------- Recurring transactions ----------

async def list_recurring(
    session,
    *,
    user_id: uuid.UUID,
) -> list[RecurringTransaction]:
    return await finances_repo.list_recurring_for_user(session, user_id=user_id)


async def get_recurring(
    session,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
) -> RecurringTransaction:
    return await _get_recurring_or_404(session, user_id=user_id, recurring_id=recurring_id)


async def create_recurring(
    session,
    *,
    user_id: uuid.UUID,
    payload: RecurringTransactionCreate,
) -> RecurringTransaction:
    _validate_positive_amount(payload.amount, label="Amount")
    account = await _get_account_or_404(session, user_id=user_id, account_id=payload.account_id)
    category = await _get_category_or_404(session, user_id=user_id, category_id=payload.category_id)
    _validate_category_match(payload.type, category)
    return await finances_repo.create_recurring(
        session,
        user_id=user_id,
        account_id=account.id,
        category_id=category.id,
        type=payload.type,
        amount=payload.amount,
        description=payload.description,
        frequency=payload.frequency,
        start_date=payload.start_date,
        end_date=payload.end_date,
        is_active=payload.is_active,
    )


async def update_recurring(
    session,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
    payload: RecurringTransactionUpdate,
) -> RecurringTransaction:
    recurring = await _get_recurring_or_404(
        session, user_id=user_id, recurring_id=recurring_id
    )
    fields = payload.model_dump(exclude_unset=True)
    amount = fields.get("amount", recurring.amount)
    _validate_positive_amount(amount, label="Amount")

    account_id = fields.get("account_id", recurring.account_id)
    category_id = fields.get("category_id", recurring.category_id)
    entry_type = fields.get("type", recurring.type)

    account = await _get_account_or_404(session, user_id=user_id, account_id=account_id)
    category = await _get_category_or_404(session, user_id=user_id, category_id=category_id)
    _validate_category_match(entry_type, category)

    fields["account_id"] = account.id
    fields["category_id"] = category.id
    fields["type"] = entry_type
    fields["amount"] = amount
    return await finances_repo.update_recurring(session, recurring, fields=fields)


async def delete_recurring(session, *, user_id: uuid.UUID, recurring_id: uuid.UUID) -> None:
    recurring = await _get_recurring_or_404(
        session, user_id=user_id, recurring_id=recurring_id
    )
    await finances_repo.delete_recurring(session, recurring)
