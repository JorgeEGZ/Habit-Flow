from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.exc import IntegrityError

from app.core.config import get_app_timezone, get_settings
from app.core.exceptions import (
    AccountNotFound,
    BudgetRequiresExpenseCategory,
    CategoryNotFound,
    MonthlyBudgetAlreadyExists,
    MonthlyBudgetNotFound,
    RecurringDateNotScheduled,
    RecurringOccurrenceAlreadyRegistered,
    RecurringRuleInactive,
    RecurringTransactionNotFound,
    ResourceInUse,
    TransactionNotFound,
    ValidationError,
)
from app.modules.finances import repository as finances_repo
from app.modules.finances.models import (
    ENTRY_EXPENSE,
    ENTRY_INCOME,
    Account,
    Category,
    MonthlyCategoryBudget,
    RecurringTransaction,
    Transaction,
)
from app.modules.finances.schemas import (
    AccountCreate,
    AccountUpdate,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    MonthlyCategoryBudgetCreate,
    MonthlyCategoryBudgetProgress,
    MonthlyCategoryBudgetRead,
    MonthlyCategoryBudgetUpdate,
    MonthlyCategoryBudgetsRead,
    RecurringTransactionCreate,
    RecurringOccurrenceRegistrationCreate,
    RecurringOccurrenceRegistrationRead,
    RecurringTransactionRead,
    RecurringTransactionUpdate,
    SpendingByCategoryItem,
    SpendingByCategoryRead,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
    UpcomingRecurringDateGroup,
    UpcomingRecurringOccurrence,
    UpcomingRecurringRead,
)


MONTH_PATTERN = re.compile(r"^[1-9]\d{3}-(0[1-9]|1[0-2])$")
UPCOMING_RECURRING_WINDOWS = frozenset({7, 30})
MAX_EXPORT_RANGE_DAYS = 366


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


def current_app_date() -> date:
    settings = get_settings()
    return datetime.now(timezone.utc).astimezone(
        get_app_timezone(settings.app_timezone)
    ).date()


def _spending_month_bounds(month: str | None, *, today: date) -> tuple[str, date, date]:
    if month is None:
        year = today.year
        month_number = today.month
    else:
        if not MONTH_PATTERN.fullmatch(month):
            raise ValueError("Month must use YYYY-MM format.")
        year, month_number = (int(part) for part in month.split("-"))

    period_start = date(year, month_number, 1)
    if month_number == 12:
        next_month_start = date(year + 1, 1, 1)
    else:
        next_month_start = date(year, month_number + 1, 1)
    period_end = next_month_start - timedelta(days=1)
    return period_start.strftime("%Y-%m"), period_start, period_end


def _share_percentage(amount: int, total: int) -> float:
    if total == 0:
        return 0.0
    return float(
        (Decimal(amount) * Decimal("100") / Decimal(total)).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    )


def resolve_transaction_export_dates(
    *,
    from_date: date | None,
    to_date: date | None,
    today: date | None = None,
) -> tuple[date, date]:
    if (from_date is None) != (to_date is None):
        raise ValueError("from and to must be provided together.")
    if from_date is None or to_date is None:
        _month, period_start, period_end = _spending_month_bounds(None, today=today or current_app_date())
        return period_start, period_end
    if from_date > to_date:
        raise ValueError("from must not be after to.")
    if (to_date - from_date).days + 1 > MAX_EXPORT_RANGE_DAYS:
        raise ValueError("Export range must not exceed 366 days.")
    return from_date, to_date


def _monthly_budget_read(budget: MonthlyCategoryBudget) -> MonthlyCategoryBudgetRead:
    return MonthlyCategoryBudgetRead(
        id=budget.id,
        user_id=budget.user_id,
        category_id=budget.category_id,
        month=budget.month_start.strftime("%Y-%m"),
        amount=budget.amount,
        created_at=budget.created_at,
        updated_at=budget.updated_at,
    )


def _last_day_of_month(year: int, month: int) -> int:
    if month == 12:
        return (date(year + 1, 1, 1) - timedelta(days=1)).day
    return (date(year, month + 1, 1) - timedelta(days=1)).day


def _iter_daily_occurrences(
    *, start_date: date, end_date: date | None, period_start: date, period_end: date
) -> list[date]:
    first_date = max(start_date, period_start)
    last_date = min(end_date or period_end, period_end)
    if first_date > last_date:
        return []
    return [first_date + timedelta(days=offset) for offset in range((last_date - first_date).days + 1)]


def _iter_weekly_occurrences(
    *, start_date: date, end_date: date | None, period_start: date, period_end: date
) -> list[date]:
    days_since_start = max((period_start - start_date).days, 0)
    first_date = start_date + timedelta(days=((days_since_start + 6) // 7) * 7)
    last_date = min(end_date or period_end, period_end)
    if first_date > last_date:
        return []
    return [first_date + timedelta(days=offset) for offset in range(0, (last_date - first_date).days + 1, 7)]


def _iter_monthly_occurrences(
    *, start_date: date, end_date: date | None, period_start: date, period_end: date
) -> list[date]:
    first_month_date = max(start_date, period_start)
    year, month = first_month_date.year, first_month_date.month
    last_date = min(end_date or period_end, period_end)
    occurrences: list[date] = []

    while date(year, month, 1) <= last_date:
        occurrence = date(year, month, min(start_date.day, _last_day_of_month(year, month)))
        if occurrence >= start_date and period_start <= occurrence <= last_date:
            occurrences.append(occurrence)
        if month == 12:
            year, month = year + 1, 1
        else:
            month += 1

    return occurrences


def _recurring_occurrence_dates(
    recurring: RecurringTransaction,
    *,
    period_start: date,
    period_end: date,
) -> list[date]:
    if recurring.frequency == "daily":
        return _iter_daily_occurrences(
            start_date=recurring.start_date,
            end_date=recurring.end_date,
            period_start=period_start,
            period_end=period_end,
        )
    if recurring.frequency == "weekly":
        return _iter_weekly_occurrences(
            start_date=recurring.start_date,
            end_date=recurring.end_date,
            period_start=period_start,
            period_end=period_end,
        )
    return _iter_monthly_occurrences(
        start_date=recurring.start_date,
        end_date=recurring.end_date,
        period_start=period_start,
        period_end=period_end,
    )


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


async def _get_monthly_budget_or_404(
    session,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> MonthlyCategoryBudget:
    budget = await finances_repo.get_monthly_budget_by_id_and_user(
        session,
        budget_id=budget_id,
        user_id=user_id,
    )
    if not budget:
        raise MonthlyBudgetNotFound()
    return budget


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
        budget_count = await finances_repo.count_monthly_budgets_for_category(
            session, category_id=category.id, user_id=user_id
        )
        if tx_count > 0 or recurring_count > 0 or budget_count > 0:
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
    if await finances_repo.count_monthly_budgets_for_category(
        session, category_id=category.id, user_id=user_id
    ) > 0:
        raise ResourceInUse("Category has monthly budgets.")
    await finances_repo.delete_category(session, category)


# ---------- Monthly budgets ----------

async def get_monthly_budgets(
    session,
    *,
    user_id: uuid.UUID,
    month: str | None = None,
    today: date | None = None,
    spending_summary: SpendingByCategoryRead | None = None,
) -> MonthlyCategoryBudgetsRead:
    selected_month, period_start, period_end = _spending_month_bounds(
        month,
        today=today or current_app_date(),
    )
    budget_rows = await finances_repo.list_monthly_budgets_for_user_month(
        session,
        user_id=user_id,
        month_start=period_start,
    )
    if spending_summary is not None:
        if spending_summary.month != selected_month:
            raise ValueError("Spending summary month must match the budget month.")
        spending_rows = [
            (
                item.category_id,
                item.category_name,
                item.amount,
                item.transaction_count,
            )
            for item in spending_summary.categories
        ]
    else:
        spending_rows = await finances_repo.get_expense_spending_by_category(
            session,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
    spending_by_category = {
        category_id: (amount, transaction_count)
        for category_id, _category_name, amount, transaction_count in spending_rows
    }

    budgets: list[MonthlyCategoryBudgetProgress] = []
    for budget, category_name in budget_rows:
        spent_amount, transaction_count = spending_by_category.get(budget.category_id, (0, 0))
        budgets.append(
            MonthlyCategoryBudgetProgress(
                budget_id=budget.id,
                category_id=budget.category_id,
                category_name=category_name,
                budget_amount=budget.amount,
                spent_amount=spent_amount,
                remaining_amount=max(budget.amount - spent_amount, 0),
                over_budget_amount=max(spent_amount - budget.amount, 0),
                transaction_count=transaction_count,
                usage_percentage=_share_percentage(spent_amount, budget.amount),
                exceeded=spent_amount > budget.amount,
            )
        )

    budgets.sort(
        key=lambda item: (
            0 if item.exceeded else 1,
            -item.usage_percentage,
            item.category_name.casefold(),
            str(item.category_id),
        )
    )
    return MonthlyCategoryBudgetsRead(
        month=selected_month,
        period_start=period_start,
        period_end=period_end,
        total_budget_amount=sum(item.budget_amount for item in budgets),
        total_spent_amount=sum(item.spent_amount for item in budgets),
        total_remaining_amount=sum(item.remaining_amount for item in budgets),
        total_over_budget_amount=sum(item.over_budget_amount for item in budgets),
        budgets=budgets,
    )


async def create_monthly_budget(
    session,
    *,
    user_id: uuid.UUID,
    payload: MonthlyCategoryBudgetCreate,
) -> MonthlyCategoryBudgetRead:
    category = await _get_category_or_404(session, user_id=user_id, category_id=payload.category_id)
    if category.type != ENTRY_EXPENSE:
        raise BudgetRequiresExpenseCategory()

    _selected_month, month_start, _period_end = _spending_month_bounds(
        payload.month,
        today=current_app_date(),
    )
    try:
        budget = await finances_repo.create_monthly_budget(
            session,
            user_id=user_id,
            category_id=category.id,
            month_start=month_start,
            amount=payload.amount,
        )
    except IntegrityError as exc:
        await session.rollback()
        raise MonthlyBudgetAlreadyExists() from exc
    return _monthly_budget_read(budget)


async def update_monthly_budget(
    session,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
    payload: MonthlyCategoryBudgetUpdate,
) -> MonthlyCategoryBudgetRead:
    budget = await _get_monthly_budget_or_404(session, user_id=user_id, budget_id=budget_id)
    updated = await finances_repo.update_monthly_budget(session, budget, amount=payload.amount)
    return _monthly_budget_read(updated)


async def delete_monthly_budget(
    session,
    *,
    user_id: uuid.UUID,
    budget_id: uuid.UUID,
) -> None:
    budget = await _get_monthly_budget_or_404(session, user_id=user_id, budget_id=budget_id)
    await finances_repo.delete_monthly_budget(session, budget)


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


async def get_transaction_export_rows(
    session,
    *,
    user_id: uuid.UUID,
    from_date: date,
    to_date: date,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    entry_type: str | None = None,
    sort_order: str = "desc",
) -> list[list[object]]:
    rows = await finances_repo.list_transaction_export_rows_for_user(
        session,
        user_id=user_id,
        from_date=from_date,
        to_date=to_date,
        account_id=account_id,
        category_id=category_id,
        entry_type=entry_type,
        sort_order=sort_order,
    )
    return [
        [
            transaction.transaction_date.isoformat(),
            transaction.type,
            transaction.amount,
            account_name,
            category_name,
            transaction.description,
            str(transaction.id),
            str(transaction.account_id),
            str(transaction.category_id),
            transaction.created_at.isoformat(),
        ]
        for transaction, account_name, category_name in rows
    ]


async def get_monthly_budget_export_rows(
    session,
    *,
    user_id: uuid.UUID,
    month: str | None = None,
    today: date | None = None,
) -> tuple[str, list[list[object]]]:
    summary = await get_monthly_budgets(session, user_id=user_id, month=month, today=today)
    return summary.month, [
        [
            summary.month,
            budget.category_name,
            budget.budget_amount,
            budget.spent_amount,
            budget.remaining_amount,
            budget.over_budget_amount,
            budget.transaction_count,
            budget.usage_percentage,
            str(budget.exceeded).lower(),
            str(budget.budget_id),
            str(budget.category_id),
        ]
        for budget in summary.budgets
    ]


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


async def get_spending_by_category(
    session,
    *,
    user_id: uuid.UUID,
    month: str | None = None,
    today: date | None = None,
) -> SpendingByCategoryRead:
    selected_month, period_start, period_end = _spending_month_bounds(
        month,
        today=today or current_app_date(),
    )
    rows = await finances_repo.get_expense_spending_by_category(
        session,
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
    )
    total_expenses = sum(row[2] for row in rows)

    return SpendingByCategoryRead(
        month=selected_month,
        period_start=period_start,
        period_end=period_end,
        total_expenses=total_expenses,
        categories=[
            SpendingByCategoryItem(
                category_id=category_id,
                category_name=category_name,
                amount=amount,
                transaction_count=transaction_count,
                share_percentage=_share_percentage(amount, total_expenses),
            )
            for category_id, category_name, amount, transaction_count in rows
        ],
    )


async def get_upcoming_recurring(
    session,
    *,
    user_id: uuid.UUID,
    days: int = 30,
    today: date | None = None,
) -> UpcomingRecurringRead:
    if days not in UPCOMING_RECURRING_WINDOWS:
        raise ValueError("days must be either 7 or 30.")

    period_start = today or current_app_date()
    period_end = period_start + timedelta(days=days - 1)
    rules = await finances_repo.list_active_recurring_overlapping_window(
        session,
        user_id=user_id,
        period_start=period_start,
        period_end=period_end,
    )
    registrations = {
        (recurring_id, occurrence_date): transaction_id
        for recurring_id, occurrence_date, transaction_id in await finances_repo.list_recurring_registrations_for_window(
            session,
            user_id=user_id,
            period_start=period_start,
            period_end=period_end,
        )
    }
    grouped: dict[date, list[UpcomingRecurringOccurrence]] = {}

    for recurring, account_name, category_name in rules:
        for occurrence_date in _recurring_occurrence_dates(
            recurring,
            period_start=period_start,
            period_end=period_end,
        ):
            transaction_id = registrations.get((recurring.id, occurrence_date))
            grouped.setdefault(occurrence_date, []).append(
                UpcomingRecurringOccurrence(
                    recurring_id=recurring.id,
                    occurrence_date=occurrence_date,
                    account_id=recurring.account_id,
                    account_name=account_name,
                    category_id=recurring.category_id,
                    category_name=category_name,
                    type=recurring.type,
                    amount=recurring.amount,
                    description=recurring.description,
                    frequency=recurring.frequency,
                    is_registered=transaction_id is not None,
                    transaction_id=transaction_id,
                )
            )

    date_groups: list[UpcomingRecurringDateGroup] = []
    total_income = 0
    total_expenses = 0
    for occurrence_date in sorted(grouped):
        occurrences = sorted(
            grouped[occurrence_date],
            key=lambda item: (
                0 if item.type == ENTRY_EXPENSE else 1,
                item.category_name,
                item.description or "",
                str(item.recurring_id),
            ),
        )
        group_income = sum(item.amount for item in occurrences if item.type == ENTRY_INCOME)
        group_expenses = sum(item.amount for item in occurrences if item.type == ENTRY_EXPENSE)
        total_income += group_income
        total_expenses += group_expenses
        date_groups.append(
            UpcomingRecurringDateGroup(
                date=occurrence_date,
                total_income=group_income,
                total_expenses=group_expenses,
                net=group_income - group_expenses,
                occurrences=occurrences,
            )
        )

    return UpcomingRecurringRead(
        period_start=period_start,
        period_end=period_end,
        window_days=days,
        total_income=total_income,
        total_expenses=total_expenses,
        net=total_income - total_expenses,
        date_groups=date_groups,
    )


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
    if await finances_repo.count_recurring_registrations(session, recurring_id=recurring.id):
        raise ResourceInUse("Recurring transaction has registered occurrences.")
    await finances_repo.delete_recurring(session, recurring)


async def register_recurring_occurrence(
    session,
    *,
    user_id: uuid.UUID,
    recurring_id: uuid.UUID,
    payload: RecurringOccurrenceRegistrationCreate,
) -> RecurringOccurrenceRegistrationRead:
    recurring = await _get_recurring_or_404(session, user_id=user_id, recurring_id=recurring_id)
    if not recurring.is_active:
        raise RecurringRuleInactive()
    if payload.transaction_date not in _recurring_occurrence_dates(
        recurring,
        period_start=payload.transaction_date,
        period_end=payload.transaction_date,
    ):
        raise RecurringDateNotScheduled()
    if await finances_repo.get_recurring_registration(
        session, recurring_id=recurring.id, occurrence_date=payload.transaction_date
    ):
        raise RecurringOccurrenceAlreadyRegistered()

    description = recurring.description
    if "description" in payload.model_fields_set:
        description = payload.description.strip() if payload.description and payload.description.strip() else None
    try:
        transaction = await finances_repo.create_registered_recurring_transaction(
            session,
            user_id=user_id,
            recurring_id=recurring.id,
            occurrence_date=payload.transaction_date,
            account_id=recurring.account_id,
            category_id=recurring.category_id,
            type=recurring.type,
            amount=recurring.amount,
            description=description,
        )
    except IntegrityError as error:
        await session.rollback()
        raise RecurringOccurrenceAlreadyRegistered() from error
    return RecurringOccurrenceRegistrationRead(
        recurring_id=recurring.id,
        occurrence_date=payload.transaction_date,
        transaction=TransactionRead.model_validate(transaction),
    )
