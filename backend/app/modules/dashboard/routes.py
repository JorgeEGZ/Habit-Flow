from __future__ import annotations

from datetime import date

from fastapi import APIRouter

from app.core.dependencies import CurrentUser, DbSession
from app.modules.dashboard import service as dashboard_service
from app.modules.dashboard.schemas import DashboardFinances, DashboardHabits, DashboardSavings, DashboardSummary

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/summary", response_model=DashboardSummary)
async def get_summary(session: DbSession, user: CurrentUser) -> DashboardSummary:
    return await dashboard_service.get_summary(session, user_id=user.id, today=date.today())


@router.get("/habits", response_model=DashboardHabits)
async def get_habits(session: DbSession, user: CurrentUser) -> DashboardHabits:
    return await dashboard_service.get_habits(session, user_id=user.id, today=date.today())


@router.get("/savings", response_model=DashboardSavings)
async def get_savings(session: DbSession, user: CurrentUser) -> DashboardSavings:
    return await dashboard_service.get_savings(session, user_id=user.id)


@router.get("/finances", response_model=DashboardFinances)
async def get_finances(session: DbSession, user: CurrentUser) -> DashboardFinances:
    return await dashboard_service.get_finances(session, user_id=user.id, today=date.today())
