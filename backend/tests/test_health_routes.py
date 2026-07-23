from __future__ import annotations

import pytest
from httpx import AsyncClient

from app.modules.health import routes as health_routes


@pytest.mark.asyncio
async def test_health_endpoint_is_preserved(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "1.0.0",
        "database": "ok",
    }


@pytest.mark.asyncio
async def test_liveness_does_not_query_database(client: AsyncClient, monkeypatch) -> None:
    async def database_must_not_be_called(*_args, **_kwargs) -> bool:
        raise AssertionError("Liveness must not query the database.")

    monkeypatch.setattr(health_routes, "check_db", database_must_not_be_called)

    response = await client.get("/api/v1/health/live")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "1.0.0",
    }


@pytest.mark.asyncio
async def test_readiness_checks_database(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "version": "1.0.0",
        "database": "ok",
    }


@pytest.mark.asyncio
async def test_readiness_returns_503_when_database_is_unavailable(
    client: AsyncClient, monkeypatch
) -> None:
    async def unavailable_database(*_args, **_kwargs) -> bool:
        return False

    monkeypatch.setattr(health_routes, "check_db", unavailable_database)

    response = await client.get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database is unavailable."}
