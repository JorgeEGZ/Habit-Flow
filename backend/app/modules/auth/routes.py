from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.dependencies import DbSession
from app.modules.auth import service as auth_service
from app.modules.auth.schemas import (
    LoginIn,
    LogoutIn,
    RefreshIn,
    RegisterIn,
    TokenPair,
)
from app.modules.users.models import User
from app.modules.users.schemas import UserRead

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserRead, status_code=201)
async def register(payload: RegisterIn, session: DbSession) -> User:
    return await auth_service.register(session, payload)


@router.post("/login", response_model=TokenPair)
async def login(payload: LoginIn, session: DbSession) -> TokenPair:
    return await auth_service.login(session, payload.email, payload.password)


@router.post("/refresh", response_model=TokenPair)
async def refresh(payload: RefreshIn, session: DbSession) -> TokenPair:
    return await auth_service.refresh_tokens(session, payload.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: LogoutIn, session: DbSession) -> Response:
    await auth_service.logout(session, payload.refresh_token)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
