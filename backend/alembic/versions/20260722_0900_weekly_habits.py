"""weekly habit goal constraints

Revision ID: 20260722_0900
Revises: 20260617_1200
Create Date: 2026-07-22 09:00:00

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260722_0900"
down_revision: str | Sequence[str] | None = "20260617_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


GOAL_SHAPE_CONSTRAINT = (
    "(tracking_mode = 'boolean' AND frequency = 'daily' "
    "AND target_value IS NULL AND unit IS NULL) OR "
    "(tracking_mode = 'boolean' AND frequency = 'weekly' "
    "AND target_value IS NOT NULL AND target_value BETWEEN 1 AND 7 "
    "AND unit IS NULL) OR "
    "(tracking_mode = 'numeric' AND frequency IN ('daily','weekly') "
    "AND target_value IS NOT NULL AND target_value > 0 "
    "AND unit IS NOT NULL AND length(trim(unit)) > 0)"
)


def upgrade() -> None:
    invalid_units = op.get_bind().execute(
        sa.text(
            "SELECT COUNT(*) FROM habits "
            "WHERE tracking_mode = 'numeric' AND length(trim(unit)) = 0"
        )
    ).scalar_one()
    if invalid_units:
        raise RuntimeError(
            "Cannot enable weekly habit constraints while numeric habits "
            "with empty units exist. Clean those rows before upgrading."
        )

    with op.batch_alter_table("habits") as batch_op:
        batch_op.drop_constraint(op.f("ck_habits_frequency"), type_="check")
        batch_op.drop_constraint(
            op.f("ck_habits_target_value_consistent"), type_="check"
        )
        batch_op.drop_constraint(
            op.f("ck_habits_unit_consistent"), type_="check"
        )
        batch_op.create_check_constraint(
            op.f("ck_habits_frequency"),
            "frequency IN ('daily','weekly')",
        )
        batch_op.create_check_constraint(
            op.f("ck_habits_goal_shape"),
            GOAL_SHAPE_CONSTRAINT,
        )


def downgrade() -> None:
    weekly_habits = op.get_bind().execute(
        sa.text("SELECT COUNT(*) FROM habits WHERE frequency = 'weekly'")
    ).scalar_one()
    if weekly_habits:
        raise RuntimeError(
            "Cannot downgrade while weekly habits exist. Remove or migrate "
            "those rows explicitly before downgrading."
        )

    with op.batch_alter_table("habits") as batch_op:
        batch_op.drop_constraint(op.f("ck_habits_goal_shape"), type_="check")
        batch_op.drop_constraint(op.f("ck_habits_frequency"), type_="check")
        batch_op.create_check_constraint(
            op.f("ck_habits_target_value_consistent"),
            "(tracking_mode = 'numeric' AND target_value IS NOT NULL "
            "AND target_value > 0) OR "
            "(tracking_mode = 'boolean' AND target_value IS NULL)",
        )
        batch_op.create_check_constraint(
            op.f("ck_habits_unit_consistent"),
            "(tracking_mode = 'numeric' AND unit IS NOT NULL) OR "
            "(tracking_mode = 'boolean' AND unit IS NULL)",
        )
        batch_op.create_check_constraint(
            op.f("ck_habits_frequency"),
            "frequency = 'daily'",
        )
