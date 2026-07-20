from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.health.repository import ping as ping_query


async def check_db(session: AsyncSession) -> bool:
    return await ping_query(session)
