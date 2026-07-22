"""HTTP integration tests for the finances routes."""
from __future__ import annotations

from datetime import date

import pytest
from httpx import AsyncClient

from app.modules.finances import service as finances_service


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


async def test_accounts_require_bearer(client: AsyncClient) -> None:
    response = await client.get("/api/v1/finances/accounts")
    assert response.status_code == 401


async def test_spending_by_category_requires_bearer(client: AsyncClient) -> None:
    response = await client.get("/api/v1/finances/insights/spending-by-category")
    assert response.status_code == 401


async def test_monthly_budgets_require_bearer(client: AsyncClient) -> None:
    response = await client.get("/api/v1/finances/budgets")
    assert response.status_code == 401


async def test_upcoming_recurring_requires_bearer(client: AsyncClient) -> None:
    response = await client.get("/api/v1/finances/insights/upcoming-recurring")
    assert response.status_code == 401


@pytest.mark.parametrize("days", [1, 8, 29, 31, "invalid"])
async def test_upcoming_recurring_rejects_invalid_days(
    client: AsyncClient,
    days: int | str,
) -> None:
    token = await _register_and_login(client, email=f"invalid-days-{days}@example.com")
    response = await client.get(
        "/api/v1/finances/insights/upcoming-recurring",
        headers=_auth_headers(token),
        params={"days": days},
    )
    assert response.status_code == 422


async def test_upcoming_recurring_defaults_to_thirty_days_and_app_date(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(finances_service, "current_app_date", lambda: date(2026, 7, 22))
    token = await _register_and_login(client, email="default-upcoming@example.com")

    response = await client.get(
        "/api/v1/finances/insights/upcoming-recurring",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "period_start": "2026-07-22",
        "period_end": "2026-08-20",
        "window_days": 30,
        "total_income": 0,
        "total_expenses": 0,
        "net": 0,
        "date_groups": [],
    }


@pytest.mark.parametrize("days", [7, 30])
async def test_upcoming_recurring_accepts_allowed_days(
    client: AsyncClient,
    days: int,
) -> None:
    token = await _register_and_login(client, email=f"allowed-upcoming-{days}@example.com")
    response = await client.get(
        "/api/v1/finances/insights/upcoming-recurring",
        headers=_auth_headers(token),
        params={"days": days},
    )

    assert response.status_code == 200
    assert response.json()["window_days"] == days


@pytest.mark.parametrize("month", ["2026-7", "2026-13", "0000-01"])
async def test_spending_by_category_rejects_invalid_month(
    client: AsyncClient,
    month: str,
) -> None:
    token = await _register_and_login(client, email=f"invalid-month-{month}@example.com")
    response = await client.get(
        "/api/v1/finances/insights/spending-by-category",
        headers=_auth_headers(token),
        params={"month": month},
    )
    assert response.status_code == 422


async def test_spending_by_category_uses_current_app_month_when_omitted(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(finances_service, "current_app_date", lambda: date(2026, 7, 22))
    token = await _register_and_login(client, email="default-spending-month@example.com")

    response = await client.get(
        "/api/v1/finances/insights/spending-by-category",
        headers=_auth_headers(token),
    )

    assert response.status_code == 200
    assert response.json() == {
        "month": "2026-07",
        "period_start": "2026-07-01",
        "period_end": "2026-07-31",
        "total_expenses": 0,
        "categories": [],
    }


@pytest.mark.parametrize("month", ["2026-7", "2026-13", "0000-01"])
async def test_monthly_budgets_reject_invalid_month(client: AsyncClient, month: str) -> None:
    token = await _register_and_login(client, email=f"invalid-budget-month-{month}@example.com")
    response = await client.get(
        "/api/v1/finances/budgets",
        headers=_auth_headers(token),
        params={"month": month},
    )
    assert response.status_code == 422


async def test_monthly_budget_crud_and_validation(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="budget-routes@example.com")
    headers = _auth_headers(token)
    expense = await client.post(
        "/api/v1/finances/categories",
        headers=headers,
        json={"name": "Food", "type": "expense"},
    )
    income = await client.post(
        "/api/v1/finances/categories",
        headers=headers,
        json={"name": "Salary", "type": "income"},
    )
    expense_id = expense.json()["id"]

    created = await client.post(
        "/api/v1/finances/budgets",
        headers=headers,
        json={"category_id": expense_id, "month": "2026-07", "amount": 500},
    )
    assert created.status_code == 201, created.text
    budget_id = created.json()["id"]
    assert created.json()["month"] == "2026-07"

    another_month = await client.post(
        "/api/v1/finances/budgets",
        headers=headers,
        json={"category_id": expense_id, "month": "2026-08", "amount": 500},
    )
    assert another_month.status_code == 201

    duplicate = await client.post(
        "/api/v1/finances/budgets",
        headers=headers,
        json={"category_id": expense_id, "month": "2026-07", "amount": 600},
    )
    assert duplicate.status_code == 409
    assert duplicate.json()["error"]["code"] == "monthly_budget_already_exists"

    invalid_category = await client.post(
        "/api/v1/finances/budgets",
        headers=headers,
        json={"category_id": income.json()["id"], "month": "2026-07", "amount": 500},
    )
    assert invalid_category.status_code == 400
    assert invalid_category.json()["error"]["code"] == "budget_requires_expense_category"

    invalid_fields = await client.patch(
        f"/api/v1/finances/budgets/{budget_id}",
        headers=headers,
        json={"amount": 600, "month": "2026-08"},
    )
    assert invalid_fields.status_code == 422

    invalid_create_fields = await client.post(
        "/api/v1/finances/budgets",
        headers=headers,
        json={"category_id": expense_id, "month": "2026-09", "amount": 500, "account_id": "ignored"},
    )
    assert invalid_create_fields.status_code == 422

    updated = await client.patch(
        f"/api/v1/finances/budgets/{budget_id}",
        headers=headers,
        json={"amount": 600},
    )
    assert updated.status_code == 200
    assert updated.json()["amount"] == 600

    overview = await client.get(
        "/api/v1/finances/budgets",
        headers=headers,
        params={"month": "2026-07"},
    )
    assert overview.status_code == 200
    assert overview.json()["total_budget_amount"] == 600
    assert overview.json()["budgets"][0]["spent_amount"] == 0

    deleted = await client.delete(f"/api/v1/finances/budgets/{budget_id}", headers=headers)
    assert deleted.status_code == 204


async def test_monthly_budget_uses_current_month_and_enforces_ownership(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(finances_service, "current_app_date", lambda: date(2026, 7, 22))
    owner_token = await _register_and_login(client, email="budget-owner-route@example.com")
    other_token = await _register_and_login(client, email="budget-other-route@example.com")
    owner_headers = _auth_headers(owner_token)
    category = await client.post(
        "/api/v1/finances/categories",
        headers=owner_headers,
        json={"name": "Food", "type": "expense"},
    )
    created = await client.post(
        "/api/v1/finances/budgets",
        headers=owner_headers,
        json={"category_id": category.json()["id"], "month": "2026-07", "amount": 500},
    )
    budget_id = created.json()["id"]

    default_month = await client.get("/api/v1/finances/budgets", headers=owner_headers)
    assert default_month.status_code == 200
    assert default_month.json()["month"] == "2026-07"

    other_headers = _auth_headers(other_token)
    assert (await client.patch(f"/api/v1/finances/budgets/{budget_id}", headers=other_headers, json={"amount": 1})).status_code == 404
    assert (await client.delete(f"/api/v1/finances/budgets/{budget_id}", headers=other_headers)).status_code == 404


async def test_account_crud(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="fr1@example.com")
    created = await client.post(
        "/api/v1/finances/accounts",
        headers=_auth_headers(token),
        json={"name": "Cash", "type": "cash", "initial_balance": 1000},
    )
    assert created.status_code == 201
    account_id = created.json()["id"]
    assert created.json()["current_balance"] == 1000

    fetched = await client.get(
        f"/api/v1/finances/accounts/{account_id}", headers=_auth_headers(token)
    )
    assert fetched.status_code == 200

    patched = await client.patch(
        f"/api/v1/finances/accounts/{account_id}",
        headers=_auth_headers(token),
        json={"name": "Wallet"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Wallet"

    deleted = await client.delete(
        f"/api/v1/finances/accounts/{account_id}", headers=_auth_headers(token)
    )
    assert deleted.status_code == 204


async def test_category_crud(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="fr2@example.com")
    created = await client.post(
        "/api/v1/finances/categories",
        headers=_auth_headers(token),
        json={"name": "Salary", "type": "income"},
    )
    assert created.status_code == 201
    category_id = created.json()["id"]

    fetched = await client.get(
        f"/api/v1/finances/categories/{category_id}", headers=_auth_headers(token)
    )
    assert fetched.status_code == 200

    patched = await client.patch(
        f"/api/v1/finances/categories/{category_id}",
        headers=_auth_headers(token),
        json={"name": "Main Salary"},
    )
    assert patched.status_code == 200
    assert patched.json()["name"] == "Main Salary"

    deleted = await client.delete(
        f"/api/v1/finances/categories/{category_id}", headers=_auth_headers(token)
    )
    assert deleted.status_code == 204


async def test_transaction_crud(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="fr3@example.com")
    account = await client.post(
        "/api/v1/finances/accounts",
        headers=_auth_headers(token),
        json={"name": "Cash", "type": "cash", "initial_balance": 0},
    )
    category = await client.post(
        "/api/v1/finances/categories",
        headers=_auth_headers(token),
        json={"name": "Salary", "type": "income"},
    )
    account_id = account.json()["id"]
    category_id = category.json()["id"]

    created = await client.post(
        "/api/v1/finances/transactions",
        headers=_auth_headers(token),
        json={
            "account_id": account_id,
            "category_id": category_id,
            "type": "income",
            "amount": 500,
            "description": "Freelance",
            "transaction_date": "2026-06-17",
        },
    )
    assert created.status_code == 201
    tx_id = created.json()["id"]

    fetched = await client.get(
        f"/api/v1/finances/transactions/{tx_id}", headers=_auth_headers(token)
    )
    assert fetched.status_code == 200

    patched = await client.patch(
        f"/api/v1/finances/transactions/{tx_id}",
        headers=_auth_headers(token),
        json={"amount": 600},
    )
    assert patched.status_code == 200
    assert patched.json()["amount"] == 600

    deleted = await client.delete(
        f"/api/v1/finances/transactions/{tx_id}", headers=_auth_headers(token)
    )
    assert deleted.status_code == 204


async def test_transaction_category_type_validation(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="fr4@example.com")
    account = await client.post(
        "/api/v1/finances/accounts",
        headers=_auth_headers(token),
        json={"name": "Cash", "type": "cash", "initial_balance": 0},
    )
    category = await client.post(
        "/api/v1/finances/categories",
        headers=_auth_headers(token),
        json={"name": "Food", "type": "expense"},
    )

    response = await client.post(
        "/api/v1/finances/transactions",
        headers=_auth_headers(token),
        json={
            "account_id": account.json()["id"],
            "category_id": category.json()["id"],
            "type": "income",
            "amount": 100,
            "description": "Mismatch",
            "transaction_date": "2026-06-17",
        },
    )
    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


async def test_ownership_enforcement_on_nested_resources(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="fr5a@example.com")
    bob_token = await _register_and_login(client, email="fr5b@example.com")

    account = await client.post(
        "/api/v1/finances/accounts",
        headers=_auth_headers(alice_token),
        json={"name": "Cash", "type": "cash", "initial_balance": 0},
    )
    category = await client.post(
        "/api/v1/finances/categories",
        headers=_auth_headers(alice_token),
        json={"name": "Salary", "type": "income"},
    )
    tx = await client.post(
        "/api/v1/finances/transactions",
        headers=_auth_headers(alice_token),
        json={
            "account_id": account.json()["id"],
            "category_id": category.json()["id"],
            "type": "income",
            "amount": 100,
            "description": "Income",
            "transaction_date": "2026-06-17",
        },
    )
    rule = await client.post(
        "/api/v1/finances/recurring",
        headers=_auth_headers(alice_token),
        json={
            "account_id": account.json()["id"],
            "category_id": category.json()["id"],
            "type": "income",
            "amount": 100,
            "description": "Recurring",
            "frequency": "monthly",
            "start_date": "2026-06-01",
            "end_date": None,
            "is_active": True,
        },
    )

    assert (
        await client.get(
            f"/api/v1/finances/accounts/{account.json()['id']}",
            headers=_auth_headers(bob_token),
        )
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/finances/categories/{category.json()['id']}",
            headers=_auth_headers(bob_token),
        )
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/finances/transactions/{tx.json()['id']}",
            headers=_auth_headers(bob_token),
        )
    ).status_code == 404
    assert (
        await client.get(
            f"/api/v1/finances/recurring/{rule.json()['id']}",
            headers=_auth_headers(bob_token),
        )
    ).status_code == 404


async def test_dynamic_balance_and_delete_blocking(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="fr6@example.com")
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
    expense_category = await client.post(
        "/api/v1/finances/categories",
        headers=_auth_headers(token),
        json={"name": "Food", "type": "expense"},
    )
    account_id = account.json()["id"]

    await client.post(
        "/api/v1/finances/transactions",
        headers=_auth_headers(token),
        json={
            "account_id": account_id,
            "category_id": income_category.json()["id"],
            "type": "income",
            "amount": 500,
            "description": "Pay",
            "transaction_date": "2026-06-17",
        },
    )
    await client.post(
        "/api/v1/finances/transactions",
        headers=_auth_headers(token),
        json={
            "account_id": account_id,
            "category_id": expense_category.json()["id"],
            "type": "expense",
            "amount": 200,
            "description": "Lunch",
            "transaction_date": "2026-06-18",
        },
    )

    refreshed = await client.get(
        f"/api/v1/finances/accounts/{account_id}", headers=_auth_headers(token)
    )
    assert refreshed.status_code == 200
    assert refreshed.json()["current_balance"] == 1300

    delete_account = await client.delete(
        f"/api/v1/finances/accounts/{account_id}", headers=_auth_headers(token)
    )
    assert delete_account.status_code == 409
    assert delete_account.json()["error"]["code"] == "resource_in_use"

    delete_category = await client.delete(
        f"/api/v1/finances/categories/{income_category.json()['id']}",
        headers=_auth_headers(token),
    )
    assert delete_category.status_code == 409


async def test_recurring_rules_do_not_generate_transactions(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="fr7@example.com")
    account = await client.post(
        "/api/v1/finances/accounts",
        headers=_auth_headers(token),
        json={"name": "Bank", "type": "checking", "initial_balance": 0},
    )
    category = await client.post(
        "/api/v1/finances/categories",
        headers=_auth_headers(token),
        json={"name": "Salary", "type": "income"},
    )

    recurring = await client.post(
        "/api/v1/finances/recurring",
        headers=_auth_headers(token),
        json={
            "account_id": account.json()["id"],
            "category_id": category.json()["id"],
            "type": "income",
            "amount": 1000,
            "description": "Monthly",
            "frequency": "monthly",
            "start_date": "2026-06-01",
            "end_date": None,
            "is_active": True,
        },
    )
    assert recurring.status_code == 201

    transactions = await client.get(
        "/api/v1/finances/transactions", headers=_auth_headers(token)
    )
    assert transactions.status_code == 200
    assert transactions.json() == []
