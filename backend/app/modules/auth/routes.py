from __future__ import annotations

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.dependencies import DbSession
from app.core.exceptions import (
    CsrfValidationFailed,
    InvalidRefreshToken,
    RefreshTokenReuse,
    UntrustedOrigin,
    ValidationError,
)
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import (
    AccessTokenResponse,
    LoginIn,
    RegisterIn,
    TokenPair,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(payload: RegisterIn, session: DbSession) -> User:
    return await auth_service.register(session, payload)


@router.post("/login", response_model=AccessTokenResponse)
async def login(payload: LoginIn, request: Request, session: DbSession) -> Response:
    await _validate_cookie_auth_request(request)
    token_pair = await auth_service.login(session, payload.email, payload.password)
    return _token_response_with_cookie(token_pair)


@router.post("/refresh", response_model=AccessTokenResponse)
async def refresh(request: Request, session: DbSession) -> Response:
    await _validate_cookie_auth_request(request, require_empty_body=True)
    raw_refresh_token = request.cookies.get(get_settings().refresh_cookie_name)
    if not raw_refresh_token:
        raise InvalidRefreshToken()

    try:
        token_pair = await auth_service.refresh_tokens(session, raw_refresh_token)
    except (InvalidRefreshToken, RefreshTokenReuse) as exc:
        # Reuse detection remains a DomainError, but every refresh failure must
        # discard the browser's stale HttpOnly credential.
        return _clear_cookie_error_response(exc)

    return _token_response_with_cookie(token_pair)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(request: Request, session: DbSession) -> Response:
    await _validate_cookie_auth_request(request, require_empty_body=True)
    raw_refresh_token = request.cookies.get(get_settings().refresh_cookie_name)
    if raw_refresh_token:
        await auth_service.logout(session, raw_refresh_token)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response)
    return response


async def _validate_cookie_auth_request(
    request: Request,
    *,
    require_empty_body: bool = False,
) -> None:
    settings = get_settings()
    if request.headers.get("origin") not in settings.cors_origins:
        raise UntrustedOrigin()
    if request.headers.get(settings.csrf_header_name) != settings.csrf_header_value:
        raise CsrfValidationFailed()
    if require_empty_body and await request.body():
        raise ValidationError("This endpoint does not accept a request body.")


def _token_response_with_cookie(token_pair: TokenPair) -> Response:
    response = Response(
        content=AccessTokenResponse(
            access_token=token_pair.access_token,
            token_type=token_pair.token_type,
            expires_in=token_pair.expires_in,
        ).model_dump_json(),
        media_type="application/json",
    )
    _set_refresh_cookie(response, token_pair.refresh_token)
    return response


def _clear_cookie_error_response(
    exc: InvalidRefreshToken | RefreshTokenReuse,
) -> JSONResponse:
    response = JSONResponse(
        content={"error": {"code": exc.code, "message": exc.message}},
        status_code=exc.status_code,
        media_type="application/json",
    )
    _clear_refresh_cookie(response)
    return response


def _set_refresh_cookie(response: Response, raw_refresh_token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.refresh_cookie_name,
        value=raw_refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
        path=settings.refresh_cookie_path,
    )


def _clear_refresh_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        key=settings.refresh_cookie_name,
        path=settings.refresh_cookie_path,
        httponly=True,
        secure=settings.refresh_cookie_secure,
        samesite=settings.refresh_cookie_samesite,
    )
