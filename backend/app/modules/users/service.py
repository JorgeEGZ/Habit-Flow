from __future__ import annotations

import uuid

from app.modules.users import repository as users_repo
from app.modules.users.models import User
from app.modules.users.schemas import UserUpdate


async def get_user_by_id(session, user_id: uuid.UUID) -> User | None:
    return await users_repo.get_by_id(session, user_id)


async def update_user(session, user: User, payload: UserUpdate) -> User:
    # `exclude_unset=True` means a PATCH body that omits `full_name` does not
    # overwrite the stored value with None — it leaves it untouched. An
    # explicit `{"full_name": null}` will set it to null, which is the
    # conventional PATCH semantics.
    fields = payload.model_dump(exclude_unset=True)
    return await users_repo.update(session, user, fields)
