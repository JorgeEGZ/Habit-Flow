from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


# ---------- Habit ----------

# Tracking mode constants. Stored on the row as a VARCHAR, validated by the
# DB CHECK constraint and again at the API layer.
TRACKING_BOOLEAN = "boolean"
TRACKING_NUMERIC = "numeric"

# Frequency constants. The column is in the table because the ERD allows
# it; the API layer rejects anything other than "daily" for now.
FREQUENCY_DAILY = "daily"


class TimestampedMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class Habit(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "habits"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tracking_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    target_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(20), nullable=True)
    frequency: Mapped[str] = mapped_column(
        String(10), nullable=False, default=FREQUENCY_DAILY
    )

    __table_args__ = (
        CheckConstraint(
            "tracking_mode IN ('boolean','numeric')",
            name="ck_habits_tracking_mode",
        ),
        CheckConstraint(
            "(tracking_mode = 'numeric' AND target_value IS NOT NULL "
            "AND target_value > 0) "
            "OR (tracking_mode = 'boolean' AND target_value IS NULL)",
            name="ck_habits_target_value_consistent",
        ),
        CheckConstraint(
            "(tracking_mode = 'numeric' AND unit IS NOT NULL) "
            "OR (tracking_mode = 'boolean' AND unit IS NULL)",
            name="ck_habits_unit_consistent",
        ),
        CheckConstraint(
            "frequency = 'daily'",
            name="ck_habits_frequency",
        ),
        Index("ix_habits_user_id", "user_id"),
    )


# ---------- HabitLog ----------

class HabitLog(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "habit_logs"

    habit_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("habits.id", ondelete="CASCADE"),
        nullable=False,
    )
    logged_on: Mapped[date] = mapped_column(Date, nullable=False)
    # `completed` is denormalized: it's set on write by the service from
    # (logged_value vs. target_value), and is recomputed by the service on
    # every read so that a stale value (e.g. after target_value changes)
    # cannot leak into API responses. The stored column is an optimization
    # for streak queries.
    completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # Numeric habits only; NULL for boolean.
    logged_value: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)

    __table_args__ = (
        # Idempotency: one log per (habit, day). Re-logging the same day
        # upserts. This unique constraint also creates the btree on
        # (habit_id, logged_on) the ERD calls for - Postgres can scan it
        # backwards for ORDER BY logged_on DESC.
        UniqueConstraint("habit_id", "logged_on", name="uq_habit_logs_habit_day"),
        CheckConstraint(
            "logged_value IS NULL OR logged_value >= 0",
            name="ck_habit_logs_logged_value_nonneg",
        ),
        # Boolean logs must have logged_value = NULL; numeric logs must have
        # it set. Enforced at the API layer primarily; this is a safety net.
        CheckConstraint(
            "logged_value IS NOT NULL OR completed = TRUE",
            # A boolean log is always completed=True and never has a value.
            # A numeric log can be completed or not, but if it has no value,
            # we cannot derive completion - so we require completed=TRUE for
            # the no-value path, which the API never actually takes.
            name="ck_habit_logs_value_or_completed",
        ),
        Index("ix_habit_logs_habit_id_logged_on", "habit_id", "logged_on"),
    )
