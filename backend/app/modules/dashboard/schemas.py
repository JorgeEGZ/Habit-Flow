from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


GoalStatus = Literal["active", "completed"]
AccountType = Literal["checking", "savings", "cash", "credit"]
EntryType = Literal["income", "expense"]


class DashboardStreakSummary(BaseModel):
    habit_id: uuid.UUID
    title: str
    current: int = Field(ge=0)
    longest: int = Field(ge=0)


class DashboardHabits(BaseModel):
    completed_today: int = Field(ge=0)
    total_active_habits: int = Field(ge=0)
    daily_habits_total: int = Field(ge=0)
    weekly_habits_total: int = Field(ge=0)
    weekly_goals_completed: int = Field(ge=0)
    current_streak_summary: DashboardStreakSummary | None = None
    longest_streak_summary: DashboardStreakSummary | None = None


class DashboardGoalSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    saving_goal_id: uuid.UUID
    name: str
    target_date: date | None
    status: GoalStatus
    current_amount: int = Field(ge=0)
    target_amount: int = Field(gt=0)
    completion_percentage: int = Field(ge=0, le=100)


class DashboardSavingsProgress(BaseModel):
    current_amount: int = Field(ge=0)
    target_amount: int = Field(ge=0)
    completion_percentage: int = Field(ge=0, le=100)


class DashboardSavings(BaseModel):
    total_savings_contributed: int = Field(ge=0)
    active_goals_count: int = Field(ge=0)
    completed_goals_count: int = Field(ge=0)
    nearest_goal: DashboardGoalSummary | None = None
    savings_progress_summary: DashboardSavingsProgress


class DashboardAccountBalance(BaseModel):
    account_id: uuid.UUID
    name: str
    type: AccountType
    current_balance: int


class DashboardRecentTransaction(BaseModel):
    transaction_id: uuid.UUID
    transaction_date: date
    account_id: uuid.UUID
    account_name: str
    category_id: uuid.UUID
    category_name: str
    type: EntryType
    amount: int
    description: str | None


class DashboardFinances(BaseModel):
    monthly_income: int = Field(ge=0)
    monthly_expenses: int = Field(ge=0)
    monthly_balance: int
    account_balances: list[DashboardAccountBalance]
    recent_transactions: list[DashboardRecentTransaction]


class DashboardSummary(BaseModel):
    habits: DashboardHabits
    savings: DashboardSavings
    finances: DashboardFinances
