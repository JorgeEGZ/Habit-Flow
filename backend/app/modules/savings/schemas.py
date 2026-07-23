from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


GoalStatus = Literal["active", "completed"]


class SavingGoalBase(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class SavingGoalCreate(SavingGoalBase):
    target_amount: int = Field(le=10**12)
    target_date: date | None = None


class SavingGoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    target_amount: int | None = Field(default=None, le=10**12)
    target_date: date | None = None


class SavingGoalRead(SavingGoalBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    target_amount: int
    target_date: date | None
    status: GoalStatus
    created_at: datetime
    updated_at: datetime


class SavingContributionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int = Field(le=10**12)
    note: str | None = Field(default=None, max_length=255)
    contribution_date: date

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None


class SavingContributionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    amount: int | None = Field(default=None, gt=0, le=10**12)
    note: str | None = Field(default=None, max_length=255)
    contribution_date: date | None = None

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "SavingContributionUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one contribution field is required.")
        return self


class SavingContributionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    saving_goal_id: uuid.UUID
    amount: int
    note: str | None
    contribution_date: date
    created_at: datetime
    updated_at: datetime


class SavingGoalProgress(BaseModel):
    saving_goal_id: uuid.UUID
    current_amount: int = Field(ge=0)
    target_amount: int = Field(gt=0)
    completion_percentage: int = Field(ge=0, le=100)
    status: GoalStatus
