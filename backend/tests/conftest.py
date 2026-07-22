"""Pytest fixtures: async SQLite engine, session, FastAPI test client, helpers."""
from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

from app.core.config import get_settings
from app.core.dependencies import get_db as get_db_dependency
from app.core.security import hash_password
from app.db import session as db_session
from app.db.base import Base
from app.main import app
from app.modules.users.models import User


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def engine():
    test_engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield test_engine
    await test_engine.dispose()


@pytest_asyncio.fixture
async def session_factory(engine):
    return async_sessionmaker(
        bind=engine,
        expire_on_commit=False,
        class_=AsyncSession,
    )


@pytest_asyncio.fixture
async def db_session_override(session_factory):
    """Override the FastAPI get_db dependency for the duration of a test.

    FastAPI captures the dependency callable at import time, so monkeypatching
    the module attribute does not work — we must register a proper override
    on the app.
    """

    async def _get_db_override() -> AsyncGenerator[AsyncSession, None]:
        async with session_factory() as session:
            yield session

    app.dependency_overrides[get_db_dependency] = _get_db_override
    yield
    app.dependency_overrides.pop(get_db_dependency, None)


@pytest_asyncio.fixture
async def session(db_session_override, session_factory) -> AsyncGenerator[AsyncSession, None]:
    """A session bound to the test engine, for direct DB access in tests."""
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session_override) -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    # base_url must be a fully-qualified URL; httpx validates it on the first
    # request. Using a real-looking host avoids any DNS lookup since requests
    # are routed through ASGITransport, not the network stack.
    settings = get_settings()
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={
            "Origin": settings.cors_origins[0],
            settings.csrf_header_name: settings.csrf_header_value,
        },
    ) as ac:
        yield ac


@pytest_asyncio.fixture
async def test_user(session: AsyncSession) -> User:
    user = User(
        email="fixture@example.com",
        password_hash=hash_password("supersecret"),
        full_name="Fixture User",
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


@pytest.fixture
def settings():
    return get_settings()
