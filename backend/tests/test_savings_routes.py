"""HTTP integration tests for the savings routes."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def _register_and_login(
    client: AsyncClient, *, email: str, password: str = "correcthorse"
) -> str:
    await client.post(
        "/api/v1/auth/register", json={"email": email, "password": password}
    )
    login = await client.post(
        "/api/v1/auth/login", json={"email": email, "password": password}
    )
    assert login.status_code == 200, login.text
    return login.json()["access_token"]


def _auth_headers(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


async def test_list_goals_requires_bearer(client: AsyncClient) -> None:
    response = await client.get("/api/v1/savings/goals")
    assert response.status_code == 401


async def test_create_goal(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="sg1@example.com")
    response = await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(token),
        json={
            "name": "Emergency fund",
            "description": "Buffer",
            "target_amount": 5000000,
            "target_date": "2026-12-31",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Emergency fund"
    assert body["status"] == "active"
    assert body["created_at"] is not None
    assert body["updated_at"] is not None


async def test_list_goals_is_user_scoped(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="sg2a@example.com")
    bob_token = await _register_and_login(client, email="sg2b@example.com")

    await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(alice_token),
        json={"name": "Alice goal", "target_amount": 1000},
    )
    await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(bob_token),
        json={"name": "Bob goal", "target_amount": 2000},
    )

    alice_resp = await client.get(
        "/api/v1/savings/goals", headers=_auth_headers(alice_token)
    )
    bob_resp = await client.get(
        "/api/v1/savings/goals", headers=_auth_headers(bob_token)
    )

    assert alice_resp.status_code == 200
    assert bob_resp.status_code == 200
    assert {goal["name"] for goal in alice_resp.json()} == {"Alice goal"}
    assert {goal["name"] for goal in bob_resp.json()} == {"Bob goal"}


async def test_get_goal_other_user_returns_404(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="sg3a@example.com")
    bob_token = await _register_and_login(client, email="sg3b@example.com")

    created = await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(alice_token),
        json={"name": "Mine", "target_amount": 1000},
    )
    goal_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/savings/goals/{goal_id}", headers=_auth_headers(bob_token)
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "saving_goal_not_found"


async def test_update_goal_recomputes_status(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="sg4@example.com")
    created = await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(token),
        json={"name": "Laptop", "target_amount": 100},
    )
    goal_id = created.json()["id"]
    await client.post(
        f"/api/v1/savings/goals/{goal_id}/contributions",
        headers=_auth_headers(token),
        json={"amount": 100, "contribution_date": "2026-06-17"},
    )

    patched = await client.patch(
        f"/api/v1/savings/goals/{goal_id}",
        headers=_auth_headers(token),
        json={"target_amount": 150},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["status"] == "active"


async def test_delete_goal_returns_204(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="sg5@example.com")
    created = await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(token),
        json={"name": "Trip", "target_amount": 1000},
    )
    goal_id = created.json()["id"]

    deleted = await client.delete(
        f"/api/v1/savings/goals/{goal_id}", headers=_auth_headers(token)
    )
    assert deleted.status_code == 204

    fetched = await client.get(
        f"/api/v1/savings/goals/{goal_id}", headers=_auth_headers(token)
    )
    assert fetched.status_code == 404


async def test_add_contribution_and_progress_caps_at_100(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="sg6@example.com")
    created = await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(token),
        json={"name": "Goal", "target_amount": 100},
    )
    goal_id = created.json()["id"]

    first = await client.post(
        f"/api/v1/savings/goals/{goal_id}/contributions",
        headers=_auth_headers(token),
        json={"amount": 60, "contribution_date": "2026-06-17"},
    )
    second = await client.post(
        f"/api/v1/savings/goals/{goal_id}/contributions",
        headers=_auth_headers(token),
        json={"amount": 70, "contribution_date": "2026-06-18"},
    )
    third = await client.post(
        f"/api/v1/savings/goals/{goal_id}/contributions",
        headers=_auth_headers(token),
        json={"amount": 25, "contribution_date": "2026-06-19"},
    )
    progress = await client.get(
        f"/api/v1/savings/goals/{goal_id}/progress", headers=_auth_headers(token)
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert third.status_code == 201
    assert progress.status_code == 200
    body = progress.json()
    assert body["current_amount"] == 155
    assert body["completion_percentage"] == 100
    assert body["status"] == "completed"


async def test_add_contribution_rejects_zero_amount(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="sg7@example.com")
    created = await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(token),
        json={"name": "Goal", "target_amount": 100},
    )
    goal_id = created.json()["id"]

    response = await client.post(
        f"/api/v1/savings/goals/{goal_id}/contributions",
        headers=_auth_headers(token),
        json={"amount": 0, "contribution_date": "2026-06-17"},
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


async def test_contributions_other_user_returns_404(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="sg8a@example.com")
    bob_token = await _register_and_login(client, email="sg8b@example.com")

    created = await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(alice_token),
        json={"name": "Mine", "target_amount": 1000},
    )
    goal_id = created.json()["id"]

    response = await client.post(
        f"/api/v1/savings/goals/{goal_id}/contributions",
        headers=_auth_headers(bob_token),
        json={"amount": 10, "contribution_date": "2026-06-17"},
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "saving_goal_not_found"
