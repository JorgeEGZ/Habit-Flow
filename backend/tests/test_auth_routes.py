"""HTTP integration tests for the auth routes."""
from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import verify_password
from app.modules.auth.models import RefreshToken
from app.modules.users.models import User


pytestmark = pytest.mark.asyncio

AUTH_HEADERS = {
    "Origin": get_settings().cors_origins[0],
    get_settings().csrf_header_name: get_settings().csrf_header_value,
}


async def _register_and_login(
    client: AsyncClient,
    *,
    email: str,
    password: str = "correcthorse",
    full_name: str | None = None,
) -> str:
    await client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password, "full_name": full_name},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": password},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


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


async def test_login_sets_refresh_cookie_and_returns_access_token_only(
    client: AsyncClient,
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "l1@example.com", "password": "correcthorse"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "l1@example.com", "password": "correcthorse"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["expires_in"] > 0
    assert "refresh_token" not in body
    set_cookie = response.headers["set-cookie"].lower()
    assert "habitflow_refresh=" in set_cookie
    assert "httponly" in set_cookie
    assert "samesite=lax" in set_cookie
    assert "path=/api/v1/auth" in set_cookie


async def test_login_rejects_wrong_password(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "l2@example.com", "password": "correcthorse"},
    )
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "l2@example.com", "password": "wrongpassword"},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


async def test_refresh_rotates_and_old_cookie_is_rejected_on_reuse(
    client: AsyncClient,
) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "ref@example.com", "password": "correcthorse"},
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "ref@example.com", "password": "correcthorse"},
        headers=AUTH_HEADERS,
    )
    old_refresh_token = login_response.cookies.get("habitflow_refresh")
    assert old_refresh_token

    first_refresh = await client.post("/api/v1/auth/refresh", headers=AUTH_HEADERS)
    assert first_refresh.status_code == 200
    assert "refresh_token" not in first_refresh.json()
    assert first_refresh.cookies.get("habitflow_refresh") != old_refresh_token

    client.cookies.clear()
    second_refresh = await client.post(
        "/api/v1/auth/refresh",
        headers={**AUTH_HEADERS, "Cookie": f"habitflow_refresh={old_refresh_token}"},
    )
    assert second_refresh.status_code == 401
    assert second_refresh.json()["error"]["code"] == "refresh_token_reuse_detected"
    assert "max-age=0" in second_refresh.headers["set-cookie"].lower()


async def test_refresh_rejects_missing_or_invalid_cookie(client: AsyncClient) -> None:
    missing = await client.post("/api/v1/auth/refresh", headers=AUTH_HEADERS)
    assert missing.status_code == 401
    assert missing.json()["error"]["code"] == "invalid_refresh_token"

    invalid = await client.post(
        "/api/v1/auth/refresh",
        headers={**AUTH_HEADERS, "Cookie": "habitflow_refresh=not-a-valid-token"},
    )
    assert invalid.status_code == 401
    assert invalid.json()["error"]["code"] == "invalid_refresh_token"
    assert "max-age=0" in invalid.headers["set-cookie"].lower()


async def test_refresh_and_logout_reject_request_bodies(client: AsyncClient) -> None:
    refresh = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "ignored"},
        headers=AUTH_HEADERS,
    )
    assert refresh.status_code == 400
    assert refresh.json()["error"]["code"] == "validation_error"

    logout = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": "ignored"},
        headers=AUTH_HEADERS,
    )
    assert logout.status_code == 400
    assert logout.json()["error"]["code"] == "validation_error"


async def test_logout_clears_cookie_and_revokes_token(client: AsyncClient) -> None:
    await client.post(
        "/api/v1/auth/register",
        json={"email": "lo@example.com", "password": "correcthorse"},
    )
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "lo@example.com", "password": "correcthorse"},
        headers=AUTH_HEADERS,
    )
    refresh_token = login_response.cookies.get("habitflow_refresh")
    assert refresh_token

    logout_response = await client.post("/api/v1/auth/logout", headers=AUTH_HEADERS)
    assert logout_response.status_code == 204
    assert "max-age=0" in logout_response.headers["set-cookie"].lower()

    client.cookies.clear()
    refresh_response = await client.post(
        "/api/v1/auth/refresh",
        headers={**AUTH_HEADERS, "Cookie": f"habitflow_refresh={refresh_token}"},
    )
    assert refresh_response.status_code == 401
    assert refresh_response.json()["error"]["code"] == "refresh_token_reuse_detected"


async def test_logout_is_idempotent_without_cookie(client: AsyncClient) -> None:
    response = await client.post("/api/v1/auth/logout", headers=AUTH_HEADERS)
    assert response.status_code == 204
    assert "max-age=0" in response.headers["set-cookie"].lower()


async def test_cookie_auth_requires_csrf_header(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "correcthorse"},
        headers={
            "Origin": get_settings().cors_origins[0],
            get_settings().csrf_header_name: "",
        },
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_validation_failed"


async def test_cookie_auth_rejects_untrusted_origin(client: AsyncClient) -> None:
    response = await client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "correcthorse"},
        headers={"Origin": "https://untrusted.example", get_settings().csrf_header_name: "1"},
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "untrusted_origin"


async def test_cors_allows_credentials_and_csrf_header(client: AsyncClient) -> None:
    response = await client.options(
        "/api/v1/auth/refresh",
        headers={
            "Origin": get_settings().cors_origins[0],
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type,x-csrf-protection",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-credentials"] == "true"
    assert response.headers["access-control-allow-origin"] == get_settings().cors_origins[0]
    assert "x-csrf-protection" in response.headers["access-control-allow-headers"].lower()


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
    login_response = await client.post(
        "/api/v1/auth/login",
        json={"email": "me@example.com", "password": "correcthorse"},
        headers=AUTH_HEADERS,
    )
    access_token = login_response.json()["access_token"]

    response = await client.get(
        "/api/v1/users/me",
        headers={"authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["email"] == "me@example.com"
    assert body["full_name"] == "Me Myself"


async def test_update_me_trims_and_clears_full_name(client: AsyncClient) -> None:
    token = await _register_and_login(
        client,
        email="profile@example.com",
        full_name="Original Name",
    )
    headers = {"authorization": f"Bearer {token}"}

    updated = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "  Updated Name  "},
    )
    assert updated.status_code == 200
    assert updated.json()["full_name"] == "Updated Name"
    assert updated.json()["email"] == "profile@example.com"

    cleared = await client.patch(
        "/api/v1/users/me",
        headers=headers,
        json={"full_name": "   "},
    )
    assert cleared.status_code == 200
    assert cleared.json()["full_name"] is None


@pytest.mark.parametrize(
    "payload",
    [
        {"email": "changed@example.com"},
        {"unknown_field": "value"},
    ],
)
async def test_update_me_rejects_email_and_unknown_fields(
    client: AsyncClient,
    payload: dict[str, str],
) -> None:
    token = await _register_and_login(
        client,
        email=f"profile-reject-{next(iter(payload))}@example.com",
    )
    response = await client.patch(
        "/api/v1/users/me",
        headers={"authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422


async def test_password_update_requires_bearer(client: AsyncClient) -> None:
    response = await client.patch(
        "/api/v1/users/me/password",
        json={
            "current_password": "correcthorse",
            "new_password": "newcorrecthorse",
        },
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "authentication_required"


@pytest.mark.parametrize(
    ("case_name", "payload"),
    [
        (
            "current-too-short",
            {"current_password": "short", "new_password": "newcorrecthorse"},
        ),
        (
            "current-too-long",
            {"current_password": "x" * 129, "new_password": "newcorrecthorse"},
        ),
        (
            "new-too-short",
            {"current_password": "correcthorse", "new_password": "short"},
        ),
        (
            "new-too-long",
            {"current_password": "correcthorse", "new_password": "x" * 129},
        ),
    ],
)
async def test_password_update_validates_password_length(
    client: AsyncClient,
    case_name: str,
    payload: dict[str, str],
) -> None:
    token = await _register_and_login(
        client,
        email=f"password-length-{case_name}@example.com",
    )
    response = await client.patch(
        "/api/v1/users/me/password",
        headers={"authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "payload",
    [
        {"current_password": "correcthorse"},
        {"new_password": "newcorrecthorse"},
        {},
    ],
)
async def test_password_update_requires_both_password_fields(
    client: AsyncClient,
    payload: dict[str, str],
) -> None:
    token = await _register_and_login(
        client,
        email=f"password-required-{len(payload)}-{next(iter(payload), 'none')}@example.com",
    )
    response = await client.patch(
        "/api/v1/users/me/password",
        headers={"authorization": f"Bearer {token}"},
        json=payload,
    )

    assert response.status_code == 422


async def test_password_update_rejects_wrong_current_password_without_changes(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    email = "password-wrong@example.com"
    token = await _register_and_login(client, email=email)
    user = (await session.execute(select(User).where(User.email == email))).scalar_one()
    original_hash = user.password_hash

    response = await client.patch(
        "/api/v1/users/me/password",
        headers={"authorization": f"Bearer {token}"},
        json={
            "current_password": "wrongpassword",
            "new_password": "newcorrecthorse",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_current_password"
    await session.refresh(user)
    assert user.password_hash == original_hash
    tokens = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
    ).scalars().all()
    assert tokens
    assert all(record.revoked_at is None for record in tokens)


async def test_password_update_rejects_same_password(client: AsyncClient) -> None:
    token = await _register_and_login(client, email="password-same@example.com")
    response = await client.patch(
        "/api/v1/users/me/password",
        headers={"authorization": f"Bearer {token}"},
        json={
            "current_password": "correcthorse",
            "new_password": "correcthorse",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "password_must_differ"


async def test_password_update_changes_login_and_revokes_all_refresh_tokens(
    client: AsyncClient,
    session: AsyncSession,
) -> None:
    email = "password-success@example.com"
    token = await _register_and_login(client, email=email)
    second_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correcthorse"},
        headers=AUTH_HEADERS,
    )
    assert second_login.status_code == 200

    response = await client.patch(
        "/api/v1/users/me/password",
        headers={"authorization": f"Bearer {token}"},
        json={
            "current_password": "correcthorse",
            "new_password": "newcorrecthorse",
        },
    )

    assert response.status_code == 204
    assert response.content == b""
    user = (await session.execute(select(User).where(User.email == email))).scalar_one()
    await session.refresh(user)
    assert verify_password("newcorrecthorse", user.password_hash)
    assert not verify_password("correcthorse", user.password_hash)
    tokens = (
        await session.execute(
            select(RefreshToken).where(RefreshToken.user_id == user.id)
        )
    ).scalars().all()
    assert len(tokens) == 2
    assert all(record.revoked_at is not None for record in tokens)

    old_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "correcthorse"},
        headers=AUTH_HEADERS,
    )
    new_login = await client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "newcorrecthorse"},
        headers=AUTH_HEADERS,
    )
    assert old_login.status_code == 401
    assert new_login.status_code == 200
