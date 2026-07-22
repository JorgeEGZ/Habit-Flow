from __future__ import annotations

import uuid

from app.core.exceptions import InvalidCurrentPassword, PasswordMustDiffer
from app.core.security import hash_password, verify_password
from app.modules.auth import repository as auth_repo
from app.modules.users import repository as users_repo
from app.modules.users.models import User
from app.modules.users.schemas import PasswordUpdate, UserUpdate


async def get_user_by_id(session, user_id: uuid.UUID) -> User | None:
    return await users_repo.get_by_id(session, user_id)


async def update_user(session, user: User, payload: UserUpdate) -> User:
    # `exclude_unset=True` means a PATCH body that omits `full_name` does not
    # overwrite the stored value with None — it leaves it untouched. An
    # explicit `{"full_name": null}` will set it to null, which is the
    # conventional PATCH semantics.
    fields = payload.model_dump(exclude_unset=True)
    return await users_repo.update(session, user, fields)


async def update_password(session, user: User, payload: PasswordUpdate) -> None:
    if not verify_password(payload.current_password, user.password_hash):
        raise InvalidCurrentPassword()
    if verify_password(payload.new_password, user.password_hash):
        raise PasswordMustDiffer()

    user.password_hash = hash_password(payload.new_password)
    try:
        await auth_repo.revoke_all_for_user(session, user.id, commit=False)
        await session.commit()
    except Exception:
        await session.rollback()
        raise
