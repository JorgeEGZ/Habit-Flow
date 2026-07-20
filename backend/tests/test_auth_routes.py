"""HTTP integration tests for the auth routes."""
from __future__ import annotations

import pytest
from httpx import AsyncClient


pytestmark = pytest.mark.asyncio


async def test_register_returns_201_with_user_payload(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "email": "r1@example.com",
            "password": "correcthorse",
            "full_name": "R One",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["email"] == "r1@example.com"
    assert body["full_name"] == "R One"
    assert "id" in body


async def test_register_rejects_short_password(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "r2@example.com", "password": "short"},
    )
    assert response.status_code == 422


async def test_register_rejects_duplicate_email(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "r3@example.com", "password": "correcthorse"},
    )
    response = await client.post(
        "/api/v1/auth/register",
        json={"email": "r3@example.com", "password": "different1"},
    )
    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_already_taken"


async def test_login_returns_token_pair(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "l1@example.com", "password": "correcthorse"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "l1@example.com", "password": "correcthorse"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["refresh_token"]


async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "l2@example.com", "password": "correcthorse"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "l2@example.com", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_refresh_rotates_and_old_token_is_rejected_on_reuse(
    client: AsyncClient,
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "ref@example.com", "password": "correcthorse"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "ref@example.com", "password": "correcthorse"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    # First refresh succeeds and returns a new pair.
    first_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert first_refresh.status_code == 200

    # Reusing the old refresh token triggers reuse detection.
    second_refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert second_refresh.status_code == 401
    assert second_refresh.json()["error"]["code"] == "refresh_token_reuse_detected"


async def test_logout_returns_204_and_revokes_token(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "lo@example.com", "password": "correcthorse"},
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "lo@example.com", "password": "correcthorse"},
    )
    refresh_token = login_resp.json()["refresh_token"]

    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh_token},
    )
    assert logout_resp.status_code == 204

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert refresh_resp.status_code == 401


async def test_users_me_requires_bearer(client: AsyncClient) -> None:
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


async def test_users_me_returns_authenticated_user(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={
            "email": "me@example.com",
            "password": "correcthorse",
            "full_name": "Me Myself",
        },
    )
    login_resp = await client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "correcthorse"},
    )
    access_token = login_resp.json()["access_token"]

    response = await client.get(
        "/api/v1/users/me",
        headers={"authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["full_name"] == "Me Myself"
