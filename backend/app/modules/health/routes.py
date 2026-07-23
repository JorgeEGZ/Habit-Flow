from fastapi import APIRouter, HTTPException, status

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


@router.get("/live")
async def liveness_check() -> dict[str, str]:
    return {
        "status": "ok",
        "version": "1.0.0",
    }


@router.get("/ready")
async def readiness_check(session: DbSession) -> dict[str, str]:
    if not await check_db(session):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is unavailable.",
        )

    return {
        "status": "ok",
        "version": "1.0.0",
        "database": "ok",
    }
