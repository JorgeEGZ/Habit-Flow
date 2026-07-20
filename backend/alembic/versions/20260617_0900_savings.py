"""savings goals and contributions

Revision ID: 20260617_0900
Revises: 20260616_0900
Create Date: 2026-06-17 09:00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260617_0900"
down_revision: str | Sequence[str] | None = "20260616_0900"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "saving_goals",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("target_amount", sa.BigInteger(), nullable=False),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="active"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "target_amount > 0",
            name=op.f("ck_saving_goals_target_amount_positive"),
        ),
        sa.CheckConstraint(
            "status IN ('active','completed')",
            name=op.f("ck_saving_goals_status"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_saving_goals_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saving_goals")),
    )
    op.create_index(op.f("ix_saving_goals_user_id"), "saving_goals", ["user_id"])

    op.create_table(
        "saving_contributions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("saving_goal_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("amount", sa.BigInteger(), nullable=False),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("contribution_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "amount > 0",
            name=op.f("ck_saving_contributions_amount_positive"),
        ),
        sa.ForeignKeyConstraint(
            ["saving_goal_id"],
            ["saving_goals.id"],
            name=op.f("fk_saving_contributions_saving_goal_id_saving_goals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_saving_contributions")),
    )
    op.create_index(
        op.f("ix_saving_contributions_goal_date"),
        "saving_contributions",
        ["saving_goal_id", "contribution_date"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_saving_contributions_goal_date"), table_name="saving_contributions")
    op.drop_table("saving_contributions")
    op.drop_index(op.f("ix_saving_goals_user_id"), table_name="saving_goals")
    op.drop_table("saving_goals")
