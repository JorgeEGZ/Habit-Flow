from fastapi import APIRouter

from app.core.dependencies import DbSession
from app.modules.health.service import check_db

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health_check(session: DbSession) -> dict[str, str]:
    db_ok = await check_db(session)
    return {
        "status": "ok",
        "version": "1.0.0",
        "database": "ok" if db_ok else "unreachable",
    }
