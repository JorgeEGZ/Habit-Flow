from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


AccountType = Literal["checking", "savings", "cash", "credit"]
EntryType = Literal["income", "expense"]
RecurringFrequency = Literal["daily", "weekly", "monthly"]


class AccountBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: AccountType
    initial_balance: int = Field(ge=0, le=10**12)


class AccountCreate(AccountBase):
    pass


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    type: AccountType | None = None
    initial_balance: int | None = Field(default=None, ge=0, le=10**12)


class AccountRead(AccountBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    current_balance: int
    created_at: datetime
    updated_at: datetime


class CategoryBase(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    type: EntryType


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=80)
    type: EntryType | None = None


class CategoryRead(CategoryBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class MonthlyCategoryBudgetCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category_id: uuid.UUID
    month: str = Field(pattern=r"^[1-9]\d{3}-(0[1-9]|1[0-2])$")
    amount: int = Field(gt=0, le=10**12)


class MonthlyCategoryBudgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(gt=0, le=10**12)


class MonthlyCategoryBudgetRead(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    category_id: uuid.UUID
    month: str
    amount: int = Field(gt=0)
    created_at: datetime
    updated_at: datetime


class MonthlyCategoryBudgetProgress(BaseModel):
    budget_id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    budget_amount: int = Field(gt=0)
    spent_amount: int = Field(ge=0)
    remaining_amount: int = Field(ge=0)
    over_budget_amount: int = Field(ge=0)
    transaction_count: int = Field(ge=0)
    usage_percentage: float = Field(ge=0)
    exceeded: bool


class MonthlyCategoryBudgetsRead(BaseModel):
    month: str
    period_start: date
    period_end: date
    total_budget_amount: int = Field(ge=0)
    total_spent_amount: int = Field(ge=0)
    total_remaining_amount: int = Field(ge=0)
    total_over_budget_amount: int = Field(ge=0)
    budgets: list[MonthlyCategoryBudgetProgress]


class TransactionBase(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID
    type: EntryType
    amount: int = Field(le=10**12)
    description: str | None = Field(default=None, max_length=255)
    transaction_date: date


class TransactionCreate(TransactionBase):
    pass


class TransactionUpdate(BaseModel):
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    type: EntryType | None = None
    amount: int | None = Field(default=None, le=10**12)
    description: str | None = Field(default=None, max_length=255)
    transaction_date: date | None = None


class TransactionRead(TransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime


class RecurringTransactionBase(BaseModel):
    account_id: uuid.UUID
    category_id: uuid.UUID
    type: EntryType
    amount: int = Field(le=10**12)
    description: str | None = Field(default=None, max_length=255)
    frequency: RecurringFrequency
    start_date: date
    end_date: date | None = None
    is_active: bool = True


class RecurringTransactionCreate(RecurringTransactionBase):
    pass


class RecurringTransactionUpdate(BaseModel):
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    type: EntryType | None = None
    amount: int | None = Field(default=None, le=10**12)
    description: str | None = Field(default=None, max_length=255)
    frequency: RecurringFrequency | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_active: bool | None = None


class RecurringTransactionRead(RecurringTransactionBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    last_generated_at: date | None
    created_at: datetime
    updated_at: datetime


class AccountBalance(BaseModel):
    account_id: uuid.UUID
    current_balance: int


class TransactionFilter(BaseModel):
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    from_date: date | None = None
    to_date: date | None = None


class SpendingByCategoryItem(BaseModel):
    category_id: uuid.UUID
    category_name: str
    amount: int = Field(gt=0)
    transaction_count: int = Field(gt=0)
    share_percentage: float = Field(ge=0, le=100)


class SpendingByCategoryRead(BaseModel):
    month: str
    period_start: date
    period_end: date
    total_expenses: int = Field(ge=0)
    categories: list[SpendingByCategoryItem]


class UpcomingRecurringOccurrence(BaseModel):
    recurring_id: uuid.UUID
    occurrence_date: date
    account_id: uuid.UUID
    account_name: str
    category_id: uuid.UUID
    category_name: str
    type: EntryType
    amount: int = Field(gt=0)
    description: str | None
    frequency: RecurringFrequency


class UpcomingRecurringDateGroup(BaseModel):
    date: date
    total_income: int = Field(ge=0)
    total_expenses: int = Field(ge=0)
    net: int
    occurrences: list[UpcomingRecurringOccurrence]


class UpcomingRecurringRead(BaseModel):
    period_start: date
    period_end: date
    window_days: Literal[7, 30]
    total_income: int = Field(ge=0)
    total_expenses: int = Field(ge=0)
    net: int
    date_groups: list[UpcomingRecurringDateGroup]
