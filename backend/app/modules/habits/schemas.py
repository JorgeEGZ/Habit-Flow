from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.habits.models import FREQUENCY_DAILY

# ---------- Habit ----------

Frequency = Literal["daily", "weekly"]
TrackingMode = Literal["boolean", "numeric"]


class HabitBase(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class HabitCreate(HabitBase):
    tracking_mode: TrackingMode
    target_value: int | None = Field(default=None, le=10**12)
    unit: str | None = Field(default=None, max_length=20)
    frequency: Frequency = FREQUENCY_DAILY

    # Cross-field mode/frequency invariants are enforced in the service layer
    # so they produce the API's consistent domain validation response.


class HabitUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    target_value: int | None = Field(default=None, le=10**12)
    unit: str | None = Field(default=None, max_length=20)

    # tracking_mode and frequency are intentionally absent and extra fields
    # are forbidden, making both values immutable after creation.


class HabitRead(HabitBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    tracking_mode: TrackingMode
    target_value: int | None
    unit: str | None
    frequency: Frequency
    created_at: datetime
    updated_at: datetime


# ---------- HabitLog ----------

LogId = uuid.UUID


class HabitLogIn(BaseModel):
    """Input for a habit log entry.

    The shape is the same regardless of the habit's tracking_mode — the
    service decides whether ``logged_value`` is required (numeric) or
    forbidden (boolean) based on the parent habit. This keeps the request
    shape uniform and avoids a discriminated-union dance in the route.
    """
    logged_on: date
    # Optional free-text, max 255 to match the DB column.
    note: str | None = Field(default=None, max_length=255)
    # Required for numeric habits, must be absent for boolean habits.
    # Kept on the single input model so the client posts one consistent shape.
    logged_value: int | None = Field(default=None, ge=0, le=10**12)


# Kept for service-layer tests that want to assert the variant explicitly.
class HabitLogNumericIn(HabitLogIn):
    """Convenience alias: a HabitLogIn whose logged_value must be set."""

    logged_value: int = Field(ge=0, le=10**12)


class HabitLogBooleanIn(HabitLogIn):
    """Convenience alias: a HabitLogIn whose logged_value must be None."""


class HabitLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    habit_id: uuid.UUID
    logged_on: date
    completed: bool
    logged_value: int | None
    note: str | None
    created_at: datetime
    updated_at: datetime


# ---------- Progress ----------

class HabitProgressRead(BaseModel):
    habit_id: uuid.UUID
    tracking_mode: TrackingMode
    frequency: Frequency
    period_start: date
    period_end: date
    current_value: int = Field(ge=0)
    target_value: int = Field(gt=0)
    remaining_value: int = Field(ge=0)
    unit: str | None
    completed: bool
    log_for_date: HabitLogRead | None


# ---------- Streak ----------

class HabitStreak(BaseModel):
    current: int = Field(ge=0)
    longest: int = Field(ge=0)
