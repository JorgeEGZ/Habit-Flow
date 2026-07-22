from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.core.dependencies import CurrentUser, DbSession
from app.modules.users import service as users_service
from app.modules.users.schemas import PasswordUpdate, UserRead, UserUpdate

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=UserRead)
async def read_me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.patch("/me", response_model=UserRead)
async def update_me(
    payload: UserUpdate,
    session: DbSession,
    user: CurrentUser,
) -> UserRead:
    updated = await users_service.update_user(session, user, payload)
    return UserRead.model_validate(updated)


@router.patch("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def update_my_password(
    payload: PasswordUpdate,
    session: DbSession,
    user: CurrentUser,
) -> Response:
    await users_service.update_password(session, user, payload)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
