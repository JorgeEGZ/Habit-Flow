"""Migration coverage for weekly habit goal constraints."""
from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


MIGRATION_PATH = (
    Path(__file__).parents[1]
    / "alembic"
    / "versions"
    / "20260722_0900_weekly_habits.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("weekly_habits_migration", MIGRATION_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _create_legacy_habits_table(metadata: sa.MetaData) -> sa.Table:
    return sa.Table(
        "habits",
        metadata,
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("tracking_mode", sa.String(10), nullable=False),
        sa.Column("target_value", sa.BigInteger, nullable=True),
        sa.Column("unit", sa.String(20), nullable=True),
        sa.Column(
            "frequency",
            sa.String(10),
            nullable=False,
            server_default="daily",
        ),
        sa.CheckConstraint(
            "tracking_mode IN ('boolean','numeric')",
            name="ck_habits_tracking_mode",
        ),
        sa.CheckConstraint(
            "(tracking_mode = 'numeric' AND target_value IS NOT NULL "
            "AND target_value > 0) OR "
            "(tracking_mode = 'boolean' AND target_value IS NULL)",
            name="ck_habits_target_value_consistent",
        ),
        sa.CheckConstraint(
            "(tracking_mode = 'numeric' AND unit IS NOT NULL) OR "
            "(tracking_mode = 'boolean' AND unit IS NULL)",
            name="ck_habits_unit_consistent",
        ),
        sa.CheckConstraint(
            "frequency = 'daily'",
            name="ck_habits_frequency",
        ),
    )


def test_upgrade_preserves_daily_rows_and_accepts_weekly_habits() -> None:
    engine = sa.create_engine("sqlite:///:memory:")
    metadata = sa.MetaData()
    habits = _create_legacy_habits_table(metadata)
    metadata.create_all(engine)

    daily_rows = [
        {
            "id": 1,
            "tracking_mode": "boolean",
            "target_value": None,
            "unit": None,
            "frequency": "daily",
        },
        {
            "id": 2,
            "tracking_mode": "numeric",
            "target_value": 30,
            "unit": "minutes",
            "frequency": "daily",
        },
    ]

    with engine.begin() as connection:
        connection.execute(habits.insert(), daily_rows)
        migration = _load_migration()
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()

        migrated_habits = sa.Table("habits", sa.MetaData(), autoload_with=connection)
        assert connection.execute(
            sa.select(migrated_habits).order_by(migrated_habits.c.id)
        ).mappings().all() == daily_rows

        with connection.begin_nested(), pytest.raises(sa.exc.IntegrityError):
            connection.execute(
                migrated_habits.insert(),
                {
                    "id": 3,
                    "tracking_mode": "boolean",
                    "target_value": None,
                    "unit": None,
                    "frequency": "weekly",
                },
            )

        connection.execute(
            migrated_habits.insert(),
            [
                {
                    "id": 4,
                    "tracking_mode": "boolean",
                    "target_value": 2,
                    "unit": None,
                    "frequency": "weekly",
                },
                {
                    "id": 5,
                    "tracking_mode": "numeric",
                    "target_value": 15,
                    "unit": "km",
                    "frequency": "weekly",
                },
            ],
        )

        with pytest.raises(RuntimeError, match="weekly habits exist"):
            migration.downgrade()
