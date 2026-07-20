from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AuthenticationRequired
from app.core.security import require_current_user_id
from app.db.session import get_db
from app.modules.users import service as users_service
from app.modules.users.models import User

# ---------- Database session ----------

DbSession = Annotated[AsyncSession, Depends(get_db)]


# ---------- Current user ----------

async def require_current_user(
    session: DbSession,
    authorization: str | None = Header(default=None),
) -> User:
    """Resolve the calling user from a Bearer token.

    Raises ``AuthenticationRequired`` (HTTP 401, error.code =
    "authentication_required") when:
      - the Authorization header is missing or not a Bearer scheme,
      - the token is invalid or expired,
      - the decoded subject does not match an existing user.

    All non-public endpoints must declare this dependency. Routes that need
    the resolved user take ``user: User = Depends(require_current_user)``.
    """
    if not authorization or not authorization.lower().startswith("bearer "):
        raise AuthenticationRequired("Missing or malformed Authorization header.")
    token = authorization.split(" ", 1)[1].strip()
    user_id = require_current_user_id(token)
    user = await users_service.get_user_by_id(session, user_id)
    if not user:
        raise AuthenticationRequired("Token subject does not match a user.")
    return user


CurrentUser = Annotated[User, Depends(require_current_user)]