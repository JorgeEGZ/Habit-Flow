"""Async database engine and session factory.

The engine and session factory are built lazily on first access rather than
at module import. This means ``import app.db.session`` is safe in tests and
scripts (no DB connection is opened until a session is actually requested),
and lets us reset/replace the engine via :func:`set_engine` for tests.

Module-level ``engine`` and ``AsyncSessionLocal`` are exposed via PEP 562
``__getattr__`` so existing call sites that do
``from app.db.session import engine`` keep working without triggering a build.
"""
from __future__ import annotations

import sys
from collections.abc import AsyncGenerator
from typing import Any

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import get_settings


def _build_engine() -> AsyncEngine:
    settings = get_settings()
    return create_async_engine(
        settings.database_url,
        echo=settings.debug,
        pool_pre_ping=True,
        future=True,
    )


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = _build_engine()
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            class_=AsyncSession,
        )
    return _session_factory


def set_engine(engine: AsyncEngine | None) -> None:
    """Replace the cached engine. Pass None to clear and force a rebuild."""
    global _engine, _session_factory
    _engine = engine
    _session_factory = None


def reset_engine() -> None:
    """Drop the cached engine and session factory."""
    global _engine, _session_factory
    if _engine is not None:
        # The engine is sync-disposed; in tests this is fine because there's
        # no in-flight work, and in production the lifespan in app.main
        # disposes the engine explicitly at shutdown.
        try:
            _engine.sync_engine.dispose()
        except Exception:
            pass
    _engine = None
    _session_factory = None


# PEP 562 module-level __getattr__: makes `from app.db.session import engine`
# work without triggering a build at import time. The build happens on first
# attribute access, by which point tests have had a chance to call
# set_engine(...) with a SQLite engine.
def __getattr__(name: str) -> Any:
    if name == "engine":
        return get_engine()
    if name == "AsyncSessionLocal":
        return get_session_factory()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with get_session_factory()() as session:
        yield session


# Make `dir(app.db.session)` still show the lazy names.
_lazy_exports = ("engine", "AsyncSessionLocal")
if hasattr(sys, "modules") and __name__ in sys.modules:
    _module = sys.modules[__name__]
    if not hasattr(_module, "__all__"):
        _module.__all__ = list(_lazy_exports)  # type: ignore[attr-defined]
