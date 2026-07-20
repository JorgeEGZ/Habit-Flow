"""habits and habit_logs

Revision ID: 20260616_0900
Revises: 20260608_1200
Create Date: 2026-06-16 09:00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260616_0900"
down_revision: str | Sequence[str] | None = "20260608_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "habits",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("tracking_mode", sa.String(length=10), nullable=False),
        sa.Column("target_value", sa.BigInteger(), nullable=True),
        sa.Column("unit", sa.String(length=20), nullable=True),
        sa.Column("frequency", sa.String(length=10), nullable=False, server_default="daily"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "tracking_mode IN ('boolean','numeric')",
            name=op.f("ck_habits_tracking_mode"),
        ),
        sa.CheckConstraint(
            "(tracking_mode = 'numeric' AND target_value IS NOT NULL AND target_value > 0) "
            "OR (tracking_mode = 'boolean' AND target_value IS NULL)",
            name=op.f("ck_habits_target_value_consistent"),
        ),
        sa.CheckConstraint(
            "(tracking_mode = 'numeric' AND unit IS NOT NULL) "
            "OR (tracking_mode = 'boolean' AND unit IS NULL)",
            name=op.f("ck_habits_unit_consistent"),
        ),
        sa.CheckConstraint(
            "frequency = 'daily'",
            name=op.f("ck_habits_frequency"),
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_habits_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_habits")),
    )
    op.create_index(op.f("ix_habits_user_id"), "habits", ["user_id"])

    op.create_table(
        "habit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("habit_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("logged_on", sa.Date(), nullable=False),
        sa.Column("completed", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("logged_value", sa.BigInteger(), nullable=True),
        sa.Column("note", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.CheckConstraint(
            "logged_value IS NULL OR logged_value >= 0",
            name=op.f("ck_habit_logs_logged_value_nonneg"),
        ),
        sa.CheckConstraint(
            "logged_value IS NOT NULL OR completed = TRUE",
            name=op.f("ck_habit_logs_value_or_completed"),
        ),
        sa.ForeignKeyConstraint(
            ["habit_id"],
            ["habits.id"],
            name=op.f("fk_habit_logs_habit_id_habits"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_habit_logs")),
        sa.UniqueConstraint("habit_id", "logged_on", name=op.f("uq_habit_logs_habit_day")),
    )
    op.create_index(
        op.f("ix_habit_logs_habit_id_logged_on"),
        "habit_logs",
        ["habit_id", "logged_on"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_habit_logs_habit_id_logged_on"), table_name="habit_logs")
    op.drop_table("habit_logs")
    op.drop_index(op.f("ix_habits_user_id"), table_name="habits")
    op.drop_table("habits")
