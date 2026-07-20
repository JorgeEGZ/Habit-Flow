from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


STATUS_ACTIVE = "active"
STATUS_COMPLETED = "completed"


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


class SavingGoal(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "saving_goals"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    target_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default=STATUS_ACTIVE)

    __table_args__ = (
        CheckConstraint("target_amount > 0", name="ck_saving_goals_target_amount_positive"),
        CheckConstraint(
            "status IN ('active','completed')",
            name="ck_saving_goals_status",
        ),
        Index("ix_saving_goals_user_id", "user_id"),
    )


class SavingContribution(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "saving_contributions"

    saving_goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("saving_goals.id", ondelete="CASCADE"),
        nullable=False,
    )
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    contribution_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_saving_contributions_amount_positive"),
        Index(
            "ix_saving_contributions_goal_date",
            "saving_goal_id",
            "contribution_date",
        ),
    )
