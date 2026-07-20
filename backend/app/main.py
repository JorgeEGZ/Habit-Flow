from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.config import get_settings
from app.core.exceptions import DomainError
from app.db.session import engine
from app.modules.auth.routes import router as auth_router
from app.modules.dashboard.routes import router as dashboard_router
from app.modules.finances.routes import router as finances_router
from app.modules.habits.routes import router as habits_router
from app.modules.health.routes import router as health_router
from app.modules.savings.routes import router as savings_router
from app.modules.users.routes import router as users_router

settings = get_settings()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception as exc:
        print(f"[startup] database unreachable: {exc}")
    yield
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=settings.cors_methods,
    allow_headers=settings.cors_headers,
)


@app.exception_handler(DomainError)
async def domain_error_handler(_: Request, exc: DomainError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
    )


app.include_router(
    health_router,
    prefix="/api/v1",
    tags=["health"],
)
app.include_router(
    auth_router,
    prefix="/api/v1",
    tags=["auth"],
)
app.include_router(
    users_router,
    prefix="/api/v1",
    tags=["users"],
)
app.include_router(
    habits_router,
    prefix="/api/v1",
    tags=["habits"],
)
app.include_router(
    savings_router,
    prefix="/api/v1",
    tags=["savings"],
)
app.include_router(
    dashboard_router,
    prefix="/api/v1",
    tags=["dashboard"],
)
app.include_router(
    finances_router,
    prefix="/api/v1",
    tags=["finances"],
)
