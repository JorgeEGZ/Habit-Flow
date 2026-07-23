from __future__ import annotations

import uuid
from datetime import date
from typing import Literal

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.core.dependencies import CurrentUser, DbSession
from app.core.exports import csv_export_response, xlsx_export_response
from app.modules.finances import service as finances_service
from app.modules.finances.schemas import (
    AccountCreate,
    AccountRead,
    AccountUpdate,
    CategoryCreate,
    CategoryRead,
    CategoryUpdate,
    MonthlyCategoryBudgetCreate,
    MonthlyCategoryBudgetRead,
    MonthlyCategoryBudgetUpdate,
    MonthlyCategoryBudgetsRead,
    RecurringTransactionCreate,
    RecurringOccurrenceRegistrationCreate,
    RecurringOccurrenceRegistrationRead,
    RecurringTransactionRead,
    RecurringTransactionUpdate,
    SpendingByCategoryRead,
    TransactionCreate,
    TransactionRead,
    TransactionUpdate,
    UpcomingRecurringRead,
)

router = APIRouter(prefix="/finances", tags=["finances"])

MONTH_QUERY_PATTERN = r"^[1-9]\d{3}-(0[1-9]|1[0-2])$"
TRANSACTION_EXPORT_HEADERS = (
    "transaction_date",
    "type",
    "amount",
    "account_name",
    "category_name",
    "description",
    "transaction_id",
    "account_id",
    "category_id",
    "created_at",
)
MONTHLY_BUDGET_EXPORT_HEADERS = (
    "month",
    "category_name",
    "budget_amount",
    "spent_amount",
    "remaining_amount",
    "over_budget_amount",
    "transaction_count",
    "usage_percentage",
    "exceeded",
    "budget_id",
    "category_id",
)


# ---------- Accounts ----------

@router.get("/accounts", response_model=list[AccountRead])
async def list_accounts(session: DbSession, user: CurrentUser) -> list[AccountRead]:
    accounts = await finances_service.list_accounts(session, user_id=user.id)
    return [AccountRead.model_validate(account) for account in accounts]


@router.post("/accounts", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
async def create_account(
    payload: AccountCreate,
    session: DbSession,
    user: CurrentUser,
) -> AccountRead:
    account = await finances_service.create_account(session, user_id=user.id, payload=payload)
    return AccountRead.model_validate(account)


@router.get("/accounts/{account_id}", response_model=AccountRead)
async def get_account(
    account_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> AccountRead:
    account = await finances_service.get_account(session, user_id=user.id, account_id=account_id)
    return AccountRead.model_validate(account)


@router.patch("/accounts/{account_id}", response_model=AccountRead)
async def update_account(
    account_id: uuid.UUID,
    payload: AccountUpdate,
    session: DbSession,
    user: CurrentUser,
) -> AccountRead:
    account = await finances_service.update_account(
        session, user_id=user.id, account_id=account_id, payload=payload
    )
    return AccountRead.model_validate(account)


@router.delete("/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await finances_service.delete_account(session, user_id=user.id, account_id=account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Categories ----------

@router.get("/categories", response_model=list[CategoryRead])
async def list_categories(session: DbSession, user: CurrentUser) -> list[CategoryRead]:
    categories = await finances_service.list_categories(session, user_id=user.id)
    return [CategoryRead.model_validate(category) for category in categories]


@router.post("/categories", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    payload: CategoryCreate,
    session: DbSession,
    user: CurrentUser,
) -> CategoryRead:
    category = await finances_service.create_category(session, user_id=user.id, payload=payload)
    return CategoryRead.model_validate(category)


@router.get("/categories/{category_id}", response_model=CategoryRead)
async def get_category(
    category_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> CategoryRead:
    category = await finances_service.get_category(
        session, user_id=user.id, category_id=category_id
    )
    return CategoryRead.model_validate(category)


@router.patch("/categories/{category_id}", response_model=CategoryRead)
async def update_category(
    category_id: uuid.UUID,
    payload: CategoryUpdate,
    session: DbSession,
    user: CurrentUser,
) -> CategoryRead:
    category = await finances_service.update_category(
        session, user_id=user.id, category_id=category_id, payload=payload
    )
    return CategoryRead.model_validate(category)


@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await finances_service.delete_category(session, user_id=user.id, category_id=category_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Monthly budgets ----------

@router.get("/budgets", response_model=MonthlyCategoryBudgetsRead)
async def get_monthly_budgets(
    session: DbSession,
    user: CurrentUser,
    month: str | None = Query(default=None, pattern=MONTH_QUERY_PATTERN),
) -> MonthlyCategoryBudgetsRead:
    return await finances_service.get_monthly_budgets(
        session,
        user_id=user.id,
        month=month,
    )


@router.post(
    "/budgets",
    response_model=MonthlyCategoryBudgetRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_monthly_budget(
    payload: MonthlyCategoryBudgetCreate,
    session: DbSession,
    user: CurrentUser,
) -> MonthlyCategoryBudgetRead:
    return await finances_service.create_monthly_budget(
        session,
        user_id=user.id,
        payload=payload,
    )


@router.patch("/budgets/{budget_id}", response_model=MonthlyCategoryBudgetRead)
async def update_monthly_budget(
    budget_id: uuid.UUID,
    payload: MonthlyCategoryBudgetUpdate,
    session: DbSession,
    user: CurrentUser,
) -> MonthlyCategoryBudgetRead:
    return await finances_service.update_monthly_budget(
        session,
        user_id=user.id,
        budget_id=budget_id,
        payload=payload,
    )


@router.delete("/budgets/{budget_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_monthly_budget(
    budget_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await finances_service.delete_monthly_budget(
        session,
        user_id=user.id,
        budget_id=budget_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Transactions ----------

async def _transaction_export(
    *,
    session: DbSession,
    user: CurrentUser,
    export_format: Literal["csv", "xlsx"],
    from_date: date | None,
    to_date: date | None,
    account_id: uuid.UUID | None,
    category_id: uuid.UUID | None,
    entry_type: Literal["income", "expense"] | None,
    sort_order: Literal["asc", "desc"],
) -> Response:
    try:
        period_start, period_end = finances_service.resolve_transaction_export_dates(
            from_date=from_date,
            to_date=to_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    rows = await finances_service.get_transaction_export_rows(
        session,
        user_id=user.id,
        from_date=period_start,
        to_date=period_end,
        account_id=account_id,
        category_id=category_id,
        entry_type=entry_type,
        sort_order=sort_order,
    )
    filename = f"habitflow-transactions-{period_start.isoformat()}-to-{period_end.isoformat()}.{export_format}"
    if export_format == "csv":
        return csv_export_response(
            headers=TRANSACTION_EXPORT_HEADERS,
            rows=rows,
            filename=filename,
        )
    return xlsx_export_response(
        headers=TRANSACTION_EXPORT_HEADERS,
        rows=rows,
        filename=filename,
        worksheet_title="Transactions",
    )


@router.get("/exports/transactions.csv")
async def export_transactions_csv(
    session: DbSession,
    user: CurrentUser,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    entry_type: Literal["income", "expense"] | None = Query(default=None, alias="type"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sort"),
) -> Response:
    return await _transaction_export(
        session=session,
        user=user,
        export_format="csv",
        from_date=from_date,
        to_date=to_date,
        account_id=account_id,
        category_id=category_id,
        entry_type=entry_type,
        sort_order=sort_order,
    )


@router.get("/exports/transactions.xlsx")
async def export_transactions_xlsx(
    session: DbSession,
    user: CurrentUser,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    entry_type: Literal["income", "expense"] | None = Query(default=None, alias="type"),
    sort_order: Literal["asc", "desc"] = Query(default="desc", alias="sort"),
) -> Response:
    return await _transaction_export(
        session=session,
        user=user,
        export_format="xlsx",
        from_date=from_date,
        to_date=to_date,
        account_id=account_id,
        category_id=category_id,
        entry_type=entry_type,
        sort_order=sort_order,
    )


async def _monthly_budget_export(
    *,
    session: DbSession,
    user: CurrentUser,
    export_format: Literal["csv", "xlsx"],
    month: str | None,
) -> Response:
    selected_month, rows = await finances_service.get_monthly_budget_export_rows(
        session,
        user_id=user.id,
        month=month,
    )
    filename = f"habitflow-monthly-budgets-{selected_month}.{export_format}"
    if export_format == "csv":
        return csv_export_response(
            headers=MONTHLY_BUDGET_EXPORT_HEADERS,
            rows=rows,
            filename=filename,
        )
    return xlsx_export_response(
        headers=MONTHLY_BUDGET_EXPORT_HEADERS,
        rows=rows,
        filename=filename,
        worksheet_title="Monthly budgets",
    )


@router.get("/exports/monthly-budgets.csv")
async def export_monthly_budgets_csv(
    session: DbSession,
    user: CurrentUser,
    month: str | None = Query(default=None, pattern=MONTH_QUERY_PATTERN),
) -> Response:
    return await _monthly_budget_export(
        session=session,
        user=user,
        export_format="csv",
        month=month,
    )


@router.get("/exports/monthly-budgets.xlsx")
async def export_monthly_budgets_xlsx(
    session: DbSession,
    user: CurrentUser,
    month: str | None = Query(default=None, pattern=MONTH_QUERY_PATTERN),
) -> Response:
    return await _monthly_budget_export(
        session=session,
        user=user,
        export_format="xlsx",
        month=month,
    )

@router.get(
    "/insights/spending-by-category",
    response_model=SpendingByCategoryRead,
)
async def get_spending_by_category(
    session: DbSession,
    user: CurrentUser,
    month: str | None = Query(default=None, pattern=MONTH_QUERY_PATTERN),
) -> SpendingByCategoryRead:
    return await finances_service.get_spending_by_category(
        session,
        user_id=user.id,
        month=month,
    )


@router.get(
    "/insights/upcoming-recurring",
    response_model=UpcomingRecurringRead,
)
async def get_upcoming_recurring(
    session: DbSession,
    user: CurrentUser,
    days: Literal["7", "30"] = Query(default="30"),
) -> UpcomingRecurringRead:
    return await finances_service.get_upcoming_recurring(
        session,
        user_id=user.id,
        days=int(days),
    )


@router.get("/transactions", response_model=list[TransactionRead])
async def list_transactions(
    session: DbSession,
    user: CurrentUser,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
) -> list[TransactionRead]:
    transactions = await finances_service.list_transactions(
        session,
        user_id=user.id,
        account_id=account_id,
        category_id=category_id,
        from_date=from_date,
        to_date=to_date,
    )
    return [TransactionRead.model_validate(transaction) for transaction in transactions]


@router.post("/transactions", response_model=TransactionRead, status_code=status.HTTP_201_CREATED)
async def create_transaction(
    payload: TransactionCreate,
    session: DbSession,
    user: CurrentUser,
) -> TransactionRead:
    transaction = await finances_service.create_transaction(
        session, user_id=user.id, payload=payload
    )
    return TransactionRead.model_validate(transaction)


@router.get("/transactions/{transaction_id}", response_model=TransactionRead)
async def get_transaction(
    transaction_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> TransactionRead:
    transaction = await finances_service.get_transaction(
        session, user_id=user.id, transaction_id=transaction_id
    )
    return TransactionRead.model_validate(transaction)


@router.patch("/transactions/{transaction_id}", response_model=TransactionRead)
async def update_transaction(
    transaction_id: uuid.UUID,
    payload: TransactionUpdate,
    session: DbSession,
    user: CurrentUser,
) -> TransactionRead:
    transaction = await finances_service.update_transaction(
        session,
        user_id=user.id,
        transaction_id=transaction_id,
        payload=payload,
    )
    return TransactionRead.model_validate(transaction)


@router.delete("/transactions/{transaction_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transaction(
    transaction_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await finances_service.delete_transaction(
        session, user_id=user.id, transaction_id=transaction_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ---------- Recurring transactions ----------

@router.get("/recurring", response_model=list[RecurringTransactionRead])
async def list_recurring(
    session: DbSession,
    user: CurrentUser,
) -> list[RecurringTransactionRead]:
    recurring = await finances_service.list_recurring(session, user_id=user.id)
    return [RecurringTransactionRead.model_validate(rule) for rule in recurring]


@router.post("/recurring", response_model=RecurringTransactionRead, status_code=status.HTTP_201_CREATED)
async def create_recurring(
    payload: RecurringTransactionCreate,
    session: DbSession,
    user: CurrentUser,
) -> RecurringTransactionRead:
    recurring = await finances_service.create_recurring(
        session, user_id=user.id, payload=payload
    )
    return RecurringTransactionRead.model_validate(recurring)


@router.post(
    "/recurring/{recurring_id}/registrations",
    response_model=RecurringOccurrenceRegistrationRead,
    status_code=status.HTTP_201_CREATED,
)
async def register_recurring_occurrence(
    recurring_id: uuid.UUID,
    payload: RecurringOccurrenceRegistrationCreate,
    session: DbSession,
    user: CurrentUser,
) -> RecurringOccurrenceRegistrationRead:
    return await finances_service.register_recurring_occurrence(
        session,
        user_id=user.id,
        recurring_id=recurring_id,
        payload=payload,
    )


@router.get("/recurring/{recurring_id}", response_model=RecurringTransactionRead)
async def get_recurring(
    recurring_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> RecurringTransactionRead:
    recurring = await finances_service.get_recurring(
        session, user_id=user.id, recurring_id=recurring_id
    )
    return RecurringTransactionRead.model_validate(recurring)


@router.patch("/recurring/{recurring_id}", response_model=RecurringTransactionRead)
async def update_recurring(
    recurring_id: uuid.UUID,
    payload: RecurringTransactionUpdate,
    session: DbSession,
    user: CurrentUser,
) -> RecurringTransactionRead:
    recurring = await finances_service.update_recurring(
        session,
        user_id=user.id,
        recurring_id=recurring_id,
        payload=payload,
    )
    return RecurringTransactionRead.model_validate(recurring)


@router.delete("/recurring/{recurring_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    recurring_id: uuid.UUID,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await finances_service.delete_recurring(
        session, user_id=user.id, recurring_id=recurring_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
