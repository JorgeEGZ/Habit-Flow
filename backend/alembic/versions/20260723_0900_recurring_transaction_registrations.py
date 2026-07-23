"""recurring transaction registrations

Revision ID: 20260723_0900
Revises: 20260722_1200
Create Date: 2026-07-23 09:00:00
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260723_0900"
down_revision: str | Sequence[str] | None = "20260722_1200"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "recurring_transaction_registrations",
        sa.Column("transaction_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("recurring_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("occurrence_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["recurring_id"], ["recurring_transactions.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("transaction_id"),
        sa.UniqueConstraint("recurring_id", "occurrence_date", name="uq_recurring_transaction_registrations_recurring_occurrence"),
    )
    op.create_index("ix_recurring_transaction_registrations_recurring_occurrence", "recurring_transaction_registrations", ["recurring_id", "occurrence_date"])
    op.create_index("ix_recurring_transaction_registrations_occurrence_date", "recurring_transaction_registrations", ["occurrence_date"])


def downgrade() -> None:
    op.drop_index("ix_recurring_transaction_registrations_occurrence_date", table_name="recurring_transaction_registrations")
    op.drop_index("ix_recurring_transaction_registrations_recurring_occurrence", table_name="recurring_transaction_registrations")
    op.drop_table("recurring_transaction_registrations")
