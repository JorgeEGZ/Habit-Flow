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
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.mixins import UUIDPrimaryKeyMixin


ACCOUNT_CHECKING = "checking"
ACCOUNT_SAVINGS = "savings"
ACCOUNT_CASH = "cash"
ACCOUNT_CREDIT = "credit"
ACCOUNT_TYPES = (ACCOUNT_CHECKING, ACCOUNT_SAVINGS, ACCOUNT_CASH, ACCOUNT_CREDIT)

ENTRY_INCOME = "income"
ENTRY_EXPENSE = "expense"
ENTRY_TYPES = (ENTRY_INCOME, ENTRY_EXPENSE)

FREQUENCY_DAILY = "daily"
FREQUENCY_WEEKLY = "weekly"
FREQUENCY_MONTHLY = "monthly"
FREQUENCIES = (FREQUENCY_DAILY, FREQUENCY_WEEKLY, FREQUENCY_MONTHLY)


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


class Account(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    initial_balance: Mapped[int] = mapped_column(BigInteger, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "type IN ('checking','savings','cash','credit')",
            name="ck_accounts_type",
        ),
        CheckConstraint(
            "initial_balance >= 0",
            name="ck_accounts_initial_balance_nonnegative",
        ),
        Index("ix_accounts_user_id", "user_id"),
    )


class Category(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "categories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[str] = mapped_column(String(10), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "type IN ('income','expense')",
            name="ck_categories_type",
        ),
        Index("ix_categories_user_id", "user_id"),
        Index("ix_categories_user_id_type", "user_id", "type"),
    )


class Transaction(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    transaction_date: Mapped[date] = mapped_column(Date, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "type IN ('income','expense')",
            name="ck_transactions_type",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_transactions_amount_positive",
        ),
        Index("ix_transactions_user_id", "user_id"),
        Index("ix_transactions_account_id_date", "account_id", "transaction_date"),
        Index("ix_transactions_category_id", "category_id"),
        Index("ix_transactions_user_id_date", "user_id", "transaction_date"),
    )


class RecurringTransaction(UUIDPrimaryKeyMixin, TimestampedMixin, Base):
    __tablename__ = "recurring_transactions"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id"),
        nullable=False,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("categories.id"),
        nullable=False,
    )
    type: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[int] = mapped_column(BigInteger, nullable=False)
    description: Mapped[str | None] = mapped_column(String(255), nullable=True)
    frequency: Mapped[str] = mapped_column(String(20), nullable=False)
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    last_generated_at: Mapped[date | None] = mapped_column(Date, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint(
            "type IN ('income','expense')",
            name="ck_recurring_transactions_type",
        ),
        CheckConstraint(
            "amount > 0",
            name="ck_recurring_transactions_amount_positive",
        ),
        CheckConstraint(
            "frequency IN ('daily','weekly','monthly')",
            name="ck_recurring_transactions_frequency",
        ),
        CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_recurring_transactions_date_range",
        ),
        Index("ix_recurring_transactions_user_id", "user_id"),
        Index(
            "ix_recurring_transactions_user_active_frequency",
            "user_id",
            "is_active",
            "frequency",
        ),
        Index("ix_recurring_transactions_account_id", "account_id"),
        Index("ix_recurring_transactions_category_id", "category_id"),
    )
