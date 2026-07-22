"""monthly category budgets

Revision ID: 20260722_1200
Revises: 20260722_0900
Create Date: 2026-07-22 12:00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260722_1200"
down_revision: str | Sequence[str] | None = "20260722_0900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "monthly_category_budgets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("month_start", sa.Date(), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint("amount > 0", name=op.f("ck_monthly_category_budgets_amount_positive")),
        sa.CheckConstraint(
            "EXTRACT(DAY FROM month_start) = 1",
            name=op.f("ck_monthly_category_budgets_month_first_day"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_monthly_category_budgets_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["categories.id"],
            name=op.f("fk_monthly_category_budgets_category_id_categories"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_monthly_category_budgets")),
        sa.UniqueConstraint(
            "user_id",
            "category_id",
            "month_start",
            name="uq_monthly_category_budgets_user_category_month",
        ),
    )
    op.create_index(
        op.f("ix_monthly_category_budgets_user_month"),
        "monthly_category_budgets",
        ["user_id", "month_start"],
        unique=False,
    )
    op.create_index(
        op.f("ix_monthly_category_budgets_category_id"),
        "monthly_category_budgets",
        ["category_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_monthly_category_budgets_category_id"),
        table_name="monthly_category_budgets",
    )
    op.drop_index(
        op.f("ix_monthly_category_budgets_user_month"),
        table_name="monthly_category_budgets",
    )
    op.drop_table("monthly_category_budgets")
