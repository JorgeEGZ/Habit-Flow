from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.habits.models import FREQUENCY_DAILY

# ---------- Habit ----------

FrequencyDaily = Literal["daily"]
TrackingMode = Literal["boolean", "numeric"]


class HabitBase(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class HabitCreate(HabitBase):
    tracking_mode: TrackingMode
    target_value: int | None = Field(default=None, ge=1, le=10**12)
    unit: str | None = Field(default=None, max_length=20)
    frequency: FrequencyDaily = FREQUENCY_DAILY

    # The cross-field invariant (numeric requires target_value + unit;
    # boolean must not declare either) is enforced in the service layer so
    # it raises our domain ValidationError and produces a consistent HTTP
    # response shape. See habits.service._validate_tracking_shape.


class HabitUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)
    target_value: int | None = Field(default=None, ge=1, le=10**12)
    unit: str | None = Field(default=None, max_length=20)

    # We don't allow changing `tracking_mode` after creation. Doing so would
    # require migrating every existing log's shape; not worth the complexity
    # for MVP. If a user really wants to switch, they delete and re-create.


class HabitRead(HabitBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    tracking_mode: TrackingMode
    target_value: int | None
    unit: str | None
    frequency: FrequencyDaily
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


# ---------- Streak ----------

class HabitStreak(BaseModel):
    current: int = Field(ge=0)
    longest: int = Field(ge=0)
