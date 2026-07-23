"""Integration coverage for user-scoped CSV and XLSX exports."""
from __future__ import annotations

import csv
from datetime import date
from io import BytesIO, StringIO

import pytest
from httpx import AsyncClient
from openpyxl import load_workbook


pytestmark = pytest.mark.asyncio


async def _register_and_login(client: AsyncClient, email: str) -> str:
    password = "correcthorse"
    await client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = await client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _headers(token: str) -> dict[str, str]:
    return {"authorization": f"Bearer {token}"}


async def _create_account_and_category(client: AsyncClient, token: str) -> tuple[str, str]:
    headers = _headers(token)
    account = await client.post(
        "/api/v1/finances/accounts",
        headers=headers,
        json={"name": "Primary account", "type": "checking", "initial_balance": 0},
    )
    category = await client.post(
        "/api/v1/finances/categories",
        headers=headers,
        json={"name": "=Formula category", "type": "expense"},
    )
    assert account.status_code == 201
    assert category.status_code == 201
    return account.json()["id"], category.json()["id"]


def _csv_rows(response) -> list[list[str]]:
    assert response.content.startswith(b"\xef\xbb\xbf")
    return list(csv.reader(StringIO(response.content.decode("utf-8-sig"))))


async def test_export_endpoints_require_authentication(client: AsyncClient) -> None:
    for path in (
        "/api/v1/finances/exports/transactions.csv",
        "/api/v1/finances/exports/transactions.xlsx",
        "/api/v1/finances/exports/monthly-budgets.csv",
        "/api/v1/finances/exports/monthly-budgets.xlsx",
        "/api/v1/savings/exports/goals.csv",
        "/api/v1/savings/exports/goals.xlsx",
    ):
        response = await client.get(path)
        assert response.status_code == 401


async def test_transaction_exports_filter_scope_and_sanitize_cells(client: AsyncClient) -> None:
    owner = await _register_and_login(client, "export-owner@example.com")
    other = await _register_and_login(client, "export-other@example.com")
    account_id, category_id = await _create_account_and_category(client, owner)
    other_account_id, other_category_id = await _create_account_and_category(client, other)

    created = await client.post(
        "/api/v1/finances/transactions",
        headers=_headers(owner),
        json={
            "account_id": account_id,
            "category_id": category_id,
            "type": "expense",
            "amount": 1200,
            "description": "=SUM(A1:A2)",
            "transaction_date": "2026-07-01",
        },
    )
    assert created.status_code == 201
    await client.post(
        "/api/v1/finances/transactions",
        headers=_headers(other),
        json={
            "account_id": other_account_id,
            "category_id": other_category_id,
            "type": "expense",
            "amount": 9999,
            "description": "Other user",
            "transaction_date": "2026-07-01",
        },
    )

    response = await client.get(
        "/api/v1/finances/exports/transactions.csv",
        headers=_headers(owner),
        params={"from": "2026-07-01", "to": "2026-07-31", "type": "expense"},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["content-disposition"].endswith('habitflow-transactions-2026-07-01-to-2026-07-31.csv"')
    rows = _csv_rows(response)
    assert rows[0] == [
        "transaction_date", "type", "amount", "account_name", "category_name", "description",
        "transaction_id", "account_id", "category_id", "created_at",
    ]
    assert len(rows) == 2
    assert rows[1][2] == "1200"
    assert rows[1][4] == "'=Formula category"
    assert rows[1][5] == "'=SUM(A1:A2)"
    assert "9999" not in response.text

    workbook_response = await client.get(
        "/api/v1/finances/exports/transactions.xlsx",
        headers=_headers(owner),
        params={"from": "2026-07-01", "to": "2026-07-31", "sort": "asc"},
    )
    assert workbook_response.status_code == 200
    assert workbook_response.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument")
    workbook = load_workbook(BytesIO(workbook_response.content))
    worksheet = workbook.active
    assert worksheet.freeze_panes == "A2"
    assert worksheet.auto_filter.ref == "A1:J2"
    assert worksheet["A1"].font.bold is True
    assert worksheet["E2"].value == "'=Formula category"
    assert worksheet["F2"].value == "'=SUM(A1:A2)"


@pytest.mark.parametrize(
    "params",
    [
        {"from": "2026-07-01"},
        {"from": "2026-07-02", "to": "2026-07-01"},
        {"from": "2025-01-01", "to": "2026-01-02"},
    ],
)
async def test_transaction_export_rejects_invalid_ranges(client: AsyncClient, params: dict[str, str]) -> None:
    token = await _register_and_login(client, f"invalid-export-{len(params)}-{params['from']}@example.com")
    response = await client.get(
        "/api/v1/finances/exports/transactions.csv",
        headers=_headers(token),
        params=params,
    )
    assert response.status_code == 422


async def test_budget_exports_reuse_budget_progress(client: AsyncClient) -> None:
    token = await _register_and_login(client, "budget-export@example.com")
    account_id, category_id = await _create_account_and_category(client, token)
    headers = _headers(token)
    await client.post(
        "/api/v1/finances/transactions",
        headers=headers,
        json={
            "account_id": account_id,
            "category_id": category_id,
            "type": "expense",
            "amount": 600,
            "description": "Budget spending",
            "transaction_date": "2026-07-31",
        },
    )
    budget = await client.post(
        "/api/v1/finances/budgets",
        headers=headers,
        json={"category_id": category_id, "month": "2026-07", "amount": 500},
    )
    assert budget.status_code == 201

    csv_response = await client.get(
        "/api/v1/finances/exports/monthly-budgets.csv",
        headers=headers,
        params={"month": "2026-07"},
    )
    rows = _csv_rows(csv_response)
    assert rows[1][0:8] == ["2026-07", "'=Formula category", "500", "600", "0", "100", "1", "120.0"]
    assert rows[1][8] == "true"

    xlsx_response = await client.get(
        "/api/v1/finances/exports/monthly-budgets.xlsx",
        headers=headers,
        params={"month": "2026-07"},
    )
    workbook = load_workbook(BytesIO(xlsx_response.content))
    assert workbook.active["H2"].value == 120.0
    assert workbook.active["H2"].number_format == "0.00"


async def test_savings_exports_include_aggregated_contributions(client: AsyncClient) -> None:
    owner = await _register_and_login(client, "savings-export-owner@example.com")
    other = await _register_and_login(client, "savings-export-other@example.com")
    created = await client.post(
        "/api/v1/savings/goals",
        headers=_headers(owner),
        json={"name": "=Trip", "description": "=Unsafe", "target_amount": 1000},
    )
    goal_id = created.json()["id"]
    await client.post(
        f"/api/v1/savings/goals/{goal_id}/contributions",
        headers=_headers(owner),
        json={"amount": 400, "contribution_date": "2026-07-10"},
    )
    await client.post(
        "/api/v1/savings/goals",
        headers=_headers(other),
        json={"name": "Other goal", "target_amount": 10},
    )

    csv_response = await client.get("/api/v1/savings/exports/goals.csv", headers=_headers(owner))
    rows = _csv_rows(csv_response)
    assert len(rows) == 2
    assert rows[1][0] == "'=Trip"
    assert rows[1][1] == "'=Unsafe"
    assert rows[1][2:7] == ["1000", "400", "600", "40", "active"]

    xlsx_response = await client.get("/api/v1/savings/exports/goals.xlsx", headers=_headers(owner))
    workbook = load_workbook(BytesIO(xlsx_response.content))
    assert workbook.active["A2"].value == "'=Trip"
    assert workbook.active["D2"].value == 400
