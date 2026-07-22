"""HTTP integration tests for the dashboard routes."""
from __future__ import annotations

from datetime import date

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


async def test_dashboard_requires_bearer(client: AsyncClient) -> None:
    response = await client.get("/api/v1/dashboard/summary")
    assert response.status_code == 401


async def test_dashboard_empty_state(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="dash-empty@example.com")

    summary = await client.get(
        "/api/v1/dashboard/summary", headers=_auth_headers(token)
    )
    habits = await client.get("/api/v1/dashboard/habits", headers=_auth_headers(token))
    savings = await client.get("/api/v1/dashboard/savings", headers=_auth_headers(token))
    finances = await client.get("/api/v1/dashboard/finances", headers=_auth_headers(token))

    assert summary.status_code == 200
    assert habits.status_code == 200
    assert savings.status_code == 200
    assert finances.status_code == 200
    assert summary.json() == {
        "habits": {
            "completed_today": 0,
            "total_active_habits": 0,
            "daily_habits_total": 0,
            "weekly_habits_total": 0,
            "weekly_goals_completed": 0,
            "current_streak_summary": None,
            "longest_streak_summary": None,
        },
        "savings": {
            "total_savings_contributed": 0,
            "active_goals_count": 0,
            "completed_goals_count": 0,
            "nearest_goal": None,
            "savings_progress_summary": {
                "current_amount": 0,
                "target_amount": 0,
                "completion_percentage": 0,
            },
        },
        "finances": {
            "monthly_income": 0,
            "monthly_expenses": 0,
            "monthly_balance": 0,
            "account_balances": [],
            "recent_transactions": [],
        },
    }


async def test_summary_matches_section_endpoints(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="dash-consistent@example.com")

    habit = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Take vitamins", "tracking_mode": "boolean"},
    )
    await client.post(
        f"/api/v1/habits/{habit.json()['id']}/logs",
        headers=_auth_headers(token),
        json={"logged_on": str(date.today())},
    )

    goal = await client.post(
        "/api/v1/savings/goals",
        headers=_auth_headers(token),
        json={"name": "Emergency fund", "target_amount": 100},
    )
    await client.post(
        f"/api/v1/savings/goals/{goal.json()['id']}/contributions",
        headers=_auth_headers(token),
        json={"amount": 25, "contribution_date": str(date.today())},
    )

    account = await client.post(
        "/api/v1/finances/accounts",
        headers=_auth_headers(token),
        json={"name": "Cash", "type": "cash", "initial_balance": 1000},
    )
    income_category = await client.post(
        "/api/v1/finances/categories",
        headers=_auth_headers(token),
        json={"name": "Salary", "type": "income"},
    )
    await client.post(
        "/api/v1/finances/transactions",
        headers=_auth_headers(token),
        json={
            "account_id": account.json()["id"],
            "category_id": income_category.json()["id"],
            "type": "income",
            "amount": 100,
            "description": "Pay",
            "transaction_date": str(date.today()),
        },
    )

    summary = await client.get("/api/v1/dashboard/summary", headers=_auth_headers(token))
    habits = await client.get("/api/v1/dashboard/habits", headers=_auth_headers(token))
    savings = await client.get("/api/v1/dashboard/savings", headers=_auth_headers(token))
    finances = await client.get("/api/v1/dashboard/finances", headers=_auth_headers(token))

    assert summary.status_code == 200
    assert summary.json()["habits"] == habits.json()
    assert summary.json()["savings"] == savings.json()
    assert summary.json()["finances"] == finances.json()
