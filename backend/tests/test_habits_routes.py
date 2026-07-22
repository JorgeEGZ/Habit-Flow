"""HTTP integration tests for the habits routes.

Run with: ``pytest tests/test_habits_routes.py``.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.modules.habits import routes as habits_routes
from app.modules.users.models import User


pytestmark = pytest.mark.asyncio


# ---------- Helpers ----------

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


async def _seed_user(session: AsyncSession, *, email: str) -> User:
    user = User(email=email, password_hash=hash_password("correcthorse"))
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ---------- Auth gate ----------

async def test_list_habits_requires_bearer(client: AsyncClient) -> None:
    response = await client.get("/api/v1/habits")
    assert response.status_code == 401


async def test_create_habit_requires_bearer(client: AsyncClient) -> None:
    response = await client.post("/api/v1/habits", json={"title": "X", "tracking_mode": "boolean"})
    assert response.status_code == 401


async def test_app_timezone_current_date_uses_bogota_offset() -> None:
    assert habits_routes._current_date_in_timezone(
        "America/Bogota",
        now=datetime(2026, 7, 15, 3, tzinfo=timezone.utc),
    ) == date(2026, 7, 14)


# ---------- Progress ----------

async def test_progress_route_uses_app_timezone_when_as_of_is_omitted(
    client: AsyncClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    token = await _register_and_login(client, email="progress-timezone@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Meditate", "tracking_mode": "boolean"},
    )
    captured_timezone: list[str] = []

    def _fixed_today(timezone_name: str, *, now=None) -> date:
        captured_timezone.append(timezone_name)
        return date(2026, 7, 15)

    monkeypatch.setattr(habits_routes, "_current_date_in_timezone", _fixed_today)
    response = await client.get("/api/v1/habits/progress", headers=_auth_headers(token))

    assert response.status_code == 200
    assert captured_timezone == ["America/Bogota"]
    body = response.json()
    assert body[0]["habit_id"] == created.json()["id"]
    assert body[0]["period_start"] == "2026-07-15"


async def test_progress_route_rejects_future_as_of(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="progress-future-route@example.com")
    response = await client.get(
        "/api/v1/habits/progress",
        headers=_auth_headers(token),
        params={"as_of": (date.today() + timedelta(days=1)).isoformat()},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


async def test_progress_route_is_user_scoped_and_not_captured_as_habit_id(
    client: AsyncClient,
) -> None:
    alice_token = await _register_and_login(client, email="progress-alice@example.com")
    bob_token = await _register_and_login(client, email="progress-bob@example.com")
    alice_habit = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(alice_token),
        json={"title": "Alice habit", "tracking_mode": "boolean"},
    )
    await client.post(
        "/api/v1/habits",
        headers=_auth_headers(bob_token),
        json={"title": "Bob habit", "tracking_mode": "boolean"},
    )

    response = await client.get(
        "/api/v1/habits/progress",
        headers=_auth_headers(alice_token),
        params={"as_of": date.today().isoformat()},
    )

    assert response.status_code == 200
    body = response.json()
    assert [item["habit_id"] for item in body] == [alice_habit.json()["id"]]


# ---------- Habit CRUD ----------

async def test_create_boolean_habit(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="r1@example.com")
    response = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Meditate", "tracking_mode": "boolean"},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Meditate"
    assert body["tracking_mode"] == "boolean"
    assert body["target_value"] is None
    assert body["unit"] is None
    assert body["frequency"] == "daily"
    assert "id" in body
    assert "created_at" in body
    assert "updated_at" in body


async def test_create_numeric_habit_requires_target_and_unit(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="r2@example.com")
    # Missing both
    r1 = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Walk", "tracking_mode": "numeric"},
    )
    assert r1.status_code == 400
    assert r1.json()["error"]["code"] == "validation_error"

    # Missing unit
    r2 = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Walk", "tracking_mode": "numeric", "target_value": 5000},
    )
    assert r2.status_code == 400
    assert r2.json()["error"]["code"] == "validation_error"


async def test_create_boolean_rejects_target_and_unit(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="r3@example.com")
    r = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Vitamins", "tracking_mode": "boolean", "target_value": 1},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


async def test_create_numeric_habit_success(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="r4@example.com")
    r = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={
            "title": "Walk",
            "tracking_mode": "numeric",
            "target_value": 5000,
            "unit": "steps",
        },
    )
    assert r.status_code == 201
    body = r.json()
    assert body["target_value"] == 5000
    assert body["unit"] == "steps"


@pytest.mark.parametrize(
    ("payload", "expected_target", "expected_unit"),
    [
        (
            {
                "title": "Run twice",
                "tracking_mode": "boolean",
                "frequency": "weekly",
                "target_value": 2,
            },
            2,
            None,
        ),
        (
            {
                "title": "Run distance",
                "tracking_mode": "numeric",
                "frequency": "weekly",
                "target_value": 15,
                "unit": "km",
            },
            15,
            "km",
        ),
    ],
)
async def test_create_weekly_habit_combinations(
    client: AsyncClient,
    payload: dict[str, object],
    expected_target: int,
    expected_unit: str | None,
) -> None:
    token = await _register_and_login(
        client, email=f"weekly-{payload['tracking_mode']}@example.com"
    )
    response = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json=payload,
    )

    assert response.status_code == 201
    body = response.json()
    assert body["frequency"] == "weekly"
    assert body["target_value"] == expected_target
    assert body["unit"] == expected_unit


@pytest.mark.parametrize(
    "payload",
    [
        {
            "title": "Too few runs",
            "tracking_mode": "boolean",
            "frequency": "weekly",
            "target_value": 0,
        },
        {
            "title": "Too many runs",
            "tracking_mode": "boolean",
            "frequency": "weekly",
            "target_value": 8,
        },
        {
            "title": "Run",
            "tracking_mode": "boolean",
            "frequency": "weekly",
            "target_value": 2,
            "unit": "times",
        },
        {
            "title": "Walk",
            "tracking_mode": "numeric",
            "frequency": "weekly",
            "target_value": 15,
            "unit": "   ",
        },
    ],
)
async def test_create_weekly_habit_rejects_invalid_goal_shape(
    client: AsyncClient,
    payload: dict[str, object],
) -> None:
    token = await _register_and_login(
        client, email=f"invalid-weekly-{payload['title'].replace(' ', '-')}@example.com"
    )
    response = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "validation_error"


async def test_list_habits_is_user_scoped(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="alice@example.com")
    bob_token = await _register_and_login(client, email="bob@example.com")

    for title in ("A1", "A2"):
        await client.post(
            "/api/v1/habits",
            headers=_auth_headers(alice_token),
            json={"title": title, "tracking_mode": "boolean"},
        )
    await client.post(
        "/api/v1/habits",
        headers=_auth_headers(bob_token),
        json={"title": "B1", "tracking_mode": "boolean"},
    )

    alice_resp = await client.get("/api/v1/habits", headers=_auth_headers(alice_token))
    bob_resp = await client.get("/api/v1/habits", headers=_auth_headers(bob_token))

    assert alice_resp.status_code == 200
    assert bob_resp.status_code == 200
    assert {h["title"] for h in alice_resp.json()} == {"A1", "A2"}
    assert {h["title"] for h in bob_resp.json()} == {"B1"}


async def test_get_habit_other_user_returns_404(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="o1@example.com")
    bob_token = await _register_and_login(client, email="o2@example.com")

    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(alice_token),
        json={"title": "Mine", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]

    response = await client.get(
        f"/api/v1/habits/{habit_id}", headers=_auth_headers(bob_token)
    )
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "habit_not_found"


async def test_update_habit_partial(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="u1@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={
            "title": "Walk",
            "tracking_mode": "numeric",
            "target_value": 5000,
            "unit": "steps",
        },
    )
    habit_id = created.json()["id"]

    patched = await client.patch(
        f"/api/v1/habits/{habit_id}",
        headers=_auth_headers(token),
        json={"title": "Run", "target_value": 3000},
    )
    assert patched.status_code == 200
    body = patched.json()
    assert body["title"] == "Run"
    assert body["target_value"] == 3000
    assert body["unit"] == "steps"  # unchanged


async def test_update_habit_violates_invariant_returns_400(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="u2@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={
            "title": "Walk",
            "tracking_mode": "numeric",
            "target_value": 5000,
            "unit": "steps",
        },
    )
    habit_id = created.json()["id"]

    # Drop the unit on a numeric habit — must be rejected.
    r = await client.patch(
        f"/api/v1/habits/{habit_id}",
        headers=_auth_headers(token),
        json={"unit": None},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


@pytest.mark.parametrize(
    "immutable_patch",
    [{"frequency": "weekly"}, {"tracking_mode": "boolean"}],
)
async def test_update_habit_rejects_immutable_fields(
    client: AsyncClient,
    immutable_patch: dict[str, str],
) -> None:
    field_name = next(iter(immutable_patch))
    token = await _register_and_login(
        client, email=f"immutable-{field_name}@example.com"
    )
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={
            "title": "Walk",
            "tracking_mode": "numeric",
            "target_value": 5000,
            "unit": "steps",
        },
    )

    response = await client.patch(
        f"/api/v1/habits/{created.json()['id']}",
        headers=_auth_headers(token),
        json=immutable_patch,
    )

    assert response.status_code == 422


async def test_delete_habit_returns_204_and_removes(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="d1@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "X", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]

    deleted = await client.delete(
        f"/api/v1/habits/{habit_id}", headers=_auth_headers(token)
    )
    assert deleted.status_code == 204

    # Subsequent GET 404s
    fetched = await client.get(
        f"/api/v1/habits/{habit_id}", headers=_auth_headers(token)
    )
    assert fetched.status_code == 404


async def test_delete_habit_other_user_returns_404(
    client: AsyncClient,
) -> None:
    alice_token = await _register_and_login(client, email="do1@example.com")
    bob_token = await _register_and_login(client, email="do2@example.com")

    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(alice_token),
        json={"title": "Mine", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]

    r = await client.delete(
        f"/api/v1/habits/{habit_id}", headers=_auth_headers(bob_token)
    )
    assert r.status_code == 404


# ---------- Logging ----------

async def test_log_boolean_habit(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="lg1@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Vitamins", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]

    r = await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(token),
        json={"logged_on": "2026-06-15"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["completed"] is True
    assert body["logged_value"] is None
    assert body["logged_on"] == "2026-06-15"
    assert "updated_at" in body


async def test_log_numeric_completes_at_or_above_target(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="lg2@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={
            "title": "Walk",
            "tracking_mode": "numeric",
            "target_value": 10000,
            "unit": "steps",
        },
    )
    habit_id = created.json()["id"]

    r = await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(token),
        json={"logged_on": "2026-06-15", "logged_value": 12000},
    )
    assert r.status_code == 200
    assert r.json()["completed"] is True
    assert r.json()["logged_value"] == 12000


async def test_log_numeric_below_target_not_completed(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="lg3@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={
            "title": "Walk",
            "tracking_mode": "numeric",
            "target_value": 10000,
            "unit": "steps",
        },
    )
    habit_id = created.json()["id"]

    r = await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(token),
        json={"logged_on": "2026-06-15", "logged_value": 4000},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["completed"] is False
    assert body["logged_value"] == 4000


async def test_log_same_day_upserts(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="lg4@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={
            "title": "Walk",
            "tracking_mode": "numeric",
            "target_value": 10000,
            "unit": "steps",
        },
    )
    habit_id = created.json()["id"]

    first = await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(token),
        json={"logged_on": "2026-06-15", "logged_value": 3000},
    )
    second = await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(token),
        json={"logged_on": "2026-06-15", "logged_value": 12000, "note": "later"},
    )
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    assert second.json()["logged_value"] == 12000
    assert second.json()["completed"] is True
    assert second.json()["note"] == "later"


async def test_log_numeric_requires_value_returns_400(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="lg5@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={
            "title": "Walk",
            "tracking_mode": "numeric",
            "target_value": 5000,
            "unit": "steps",
        },
    )
    habit_id = created.json()["id"]

    r = await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(token),
        json={"logged_on": "2026-06-15"},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


async def test_log_boolean_rejects_value_returns_400(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="lg6@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Vitamins", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]

    r = await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(token),
        json={"logged_on": "2026-06-15", "logged_value": 5},
    )
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "validation_error"


async def test_log_other_user_habit_returns_404(client: AsyncClient) -> None:
    alice_token = await _register_and_login(client, email="lo1@example.com")
    bob_token = await _register_and_login(client, email="lo2@example.com")

    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(alice_token),
        json={"title": "Mine", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]

    r = await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(bob_token),
        json={"logged_on": "2026-06-15"},
    )
    assert r.status_code == 404


async def test_delete_log_returns_204(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="dl1@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Vitamins", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]
    await client.post(
        f"/api/v1/habits/{habit_id}/logs",
        headers=_auth_headers(token),
        json={"logged_on": "2026-06-15"},
    )

    r = await client.delete(
        f"/api/v1/habits/{habit_id}/logs/2026-06-15",
        headers=_auth_headers(token),
    )
    assert r.status_code == 204


# ---------- Streak ----------

async def test_streak_endpoint_empty(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="s1@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "X", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]

    r = await client.get(
        f"/api/v1/habits/{habit_id}/streak", headers=_auth_headers(token)
    )
    assert r.status_code == 200
    body = r.json()
    assert body["current"] == 0
    assert body["longest"] == 0


async def test_streak_endpoint_counts_recent_completions(
    client: AsyncClient,
) -> None:
    token = await _register_and_login(client, email="s2@example.com")
    created = await client.post(
        "/api/v1/habits",
        headers=_auth_headers(token),
        json={"title": "Meditate", "tracking_mode": "boolean"},
    )
    habit_id = created.json()["id"]

    today = date.today()
    for day in (
        today - timedelta(days=2),
        today - timedelta(days=1),
        today,
    ):
        await client.post(
            f"/api/v1/habits/{habit_id}/logs",
            headers=_auth_headers(token),
            json={"logged_on": day.isoformat()},
        )

    r = await client.get(
        f"/api/v1/habits/{habit_id}/streak", headers=_auth_headers(token)
    )
    assert r.status_code == 200
    body = r.json()
    # The seeded completions form a 3-day run ending on the current day.
    assert body["current"] == 3
    assert body["longest"] == 3
