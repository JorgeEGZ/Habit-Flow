from __future__ import annotations

import uuid
from collections.abc import Iterable
from datetime import date, datetime, timezone

from app.core.config import get_app_timezone, get_settings
from app.modules.dashboard import repository as dashboard_repo
from app.modules.dashboard.schemas import (
    DashboardAccountBalance,
    DashboardFinanceInsights,
    DashboardFinances,
    DashboardGoalSummary,
    DashboardHabits,
    DashboardRecentTransaction,
    DashboardSavings,
    DashboardSavingsProgress,
    DashboardStreakSummary,
    DashboardSummary,
    DashboardTopSpendingCategory,
    DashboardUpcomingRecurring,
)
from app.modules.finances import service as finances_service
from app.modules.habits import service as habits_service
from app.modules.habits.models import FREQUENCY_DAILY, FREQUENCY_WEEKLY, TRACKING_BOOLEAN
from app.modules.savings.models import STATUS_ACTIVE, STATUS_COMPLETED

RECENT_TRANSACTIONS_LIMIT = 5


def current_app_date() -> date:
    settings = get_settings()
    return datetime.now(timezone.utc).astimezone(
        get_app_timezone(settings.app_timezone)
    ).date()


def _month_bounds(today: date) -> tuple[date, date]:
    month_start = today.replace(day=1)
    if today.month == 12:
        next_month_start = date(today.year + 1, 1, 1)
    else:
        next_month_start = date(today.year, today.month + 1, 1)
    return month_start, next_month_start


def _habit_completed(tracking_mode: str, target_value: int | None, logged_value: int | None) -> bool:
    if tracking_mode == TRACKING_BOOLEAN:
        return True
    if target_value is None or logged_value is None:
        return False
    return logged_value >= target_value


def _streak_from_days(days: list[date], today: date) -> tuple[int, int]:
    if not days:
        return 0, 0

    longest = 1
    run = 1
    for previous, current in zip(days, days[1:]):
        if (current - previous).days == 1:
            run += 1
            longest = max(longest, run)
        else:
            run = 1

    current = 0 if (today - days[-1]).days > 1 else run
    return current, longest


def _best_streak_summary(
    summaries: Iterable[DashboardStreakSummary],
    *,
    key: str,
) -> DashboardStreakSummary | None:
    best: DashboardStreakSummary | None = None
    for summary in summaries:
        if getattr(summary, key) <= 0:
            continue
        if best is None:
            best = summary
            continue
        candidate = getattr(summary, key)
        best_value = getattr(best, key)
        if candidate > best_value:
            best = summary
            continue
        if candidate == best_value and (summary.longest, summary.current, summary.title) > (
            best.longest,
            best.current,
            best.title,
        ):
            best = summary
    return best


async def get_habits(
    session,
    *,
    user_id: uuid.UUID,
    today: date | None = None,
) -> DashboardHabits:
    today = today or current_app_date()
    rows = await dashboard_repo.fetch_habit_rows(session, user_id=user_id)
    progress = await habits_service.get_habit_progress(
        session,
        user_id=user_id,
        as_of=today,
        today=today,
    )

    completed_today = 0
    habit_days: dict[uuid.UUID, list[date]] = {}
    habits_by_id = {}
    daily_habits_total = 0
    weekly_habits_total = 0

    for habit, log in rows:
        if habit.id not in habits_by_id:
            habits_by_id[habit.id] = habit
            habit_days[habit.id] = []
            if habit.frequency == FREQUENCY_DAILY:
                daily_habits_total += 1
            elif habit.frequency == FREQUENCY_WEEKLY:
                weekly_habits_total += 1
        if habit.frequency != FREQUENCY_DAILY or log is None:
            continue
        if _habit_completed(habit.tracking_mode, habit.target_value, log.logged_value):
            habit_days[habit.id].append(log.logged_on)
            if log.logged_on == today:
                completed_today += 1

    summaries = []
    for habit_id, habit in habits_by_id.items():
        if habit.frequency != FREQUENCY_DAILY:
            continue
        current, longest = _streak_from_days(habit_days.get(habit_id, []), today)
        summaries.append(
            DashboardStreakSummary(
                habit_id=habit.id,
                title=habit.title,
                current=current,
                longest=longest,
            )
        )

    current_summary = _best_streak_summary(summaries, key="current")
    longest_summary = _best_streak_summary(summaries, key="longest")

    return DashboardHabits(
        completed_today=completed_today,
        total_active_habits=len(habits_by_id),
        daily_habits_total=daily_habits_total,
        weekly_habits_total=weekly_habits_total,
        weekly_goals_completed=sum(
            1
            for item in progress
            if item.frequency == FREQUENCY_WEEKLY and item.completed
        ),
        current_streak_summary=current_summary,
        longest_streak_summary=longest_summary,
    )


async def get_savings(
    session,
    *,
    user_id: uuid.UUID,
) -> DashboardSavings:
    rows = await dashboard_repo.fetch_savings_rows(session, user_id=user_id)

    total_contributed = 0
    active_count = 0
    completed_count = 0
    total_target = 0
    nearest_goal: DashboardGoalSummary | None = None

    for goal, current_amount in rows:
        total_contributed += current_amount
        total_target += goal.target_amount
        if goal.status == STATUS_ACTIVE:
            active_count += 1
        elif goal.status == STATUS_COMPLETED:
            completed_count += 1

        if goal.status == STATUS_ACTIVE and goal.target_date is not None:
            candidate = DashboardGoalSummary(
                saving_goal_id=goal.id,
                name=goal.name,
                target_date=goal.target_date,
                status=goal.status,
                current_amount=current_amount,
                target_amount=goal.target_amount,
                completion_percentage=min(100, (current_amount * 100) // goal.target_amount),
            )
            if nearest_goal is None:
                nearest_goal = candidate
            else:
                candidate_key = (
                    candidate.target_date,
                    candidate.name,
                    str(candidate.saving_goal_id),
                )
                nearest_key = (
                    nearest_goal.target_date,
                    nearest_goal.name,
                    str(nearest_goal.saving_goal_id),
                )
                if candidate_key < nearest_key:
                    nearest_goal = candidate

    progress = DashboardSavingsProgress(
        current_amount=total_contributed,
        target_amount=total_target,
        completion_percentage=0 if total_target == 0 else min(100, (total_contributed * 100) // total_target),
    )

    return DashboardSavings(
        total_savings_contributed=total_contributed,
        active_goals_count=active_count,
        completed_goals_count=completed_count,
        nearest_goal=nearest_goal,
        savings_progress_summary=progress,
    )


async def get_finances(
    session,
    *,
    user_id: uuid.UUID,
    today: date | None = None,
) -> DashboardFinances:
    today = today or current_app_date()
    month_start, next_month_start = _month_bounds(today)

    monthly_income, monthly_expenses = await dashboard_repo.fetch_finance_monthly_summary(
        session,
        user_id=user_id,
        month_start=month_start,
        next_month_start=next_month_start,
    )
    account_rows = await dashboard_repo.fetch_account_balances(session, user_id=user_id)
    recent_rows = await dashboard_repo.fetch_recent_transactions(
        session,
        user_id=user_id,
        limit=RECENT_TRANSACTIONS_LIMIT,
    )
    spending = await finances_service.get_spending_by_category(
        session,
        user_id=user_id,
        month=today.strftime("%Y-%m"),
        today=today,
    )
    upcoming = await finances_service.get_upcoming_recurring(
        session,
        user_id=user_id,
        days=30,
        today=today,
    )

    account_balances = [
        DashboardAccountBalance(
            account_id=account.id,
            name=account.name,
            type=account.type,
            current_balance=current_balance,
        )
        for account, current_balance in account_rows
    ]
    recent_transactions = [
        DashboardRecentTransaction(
            transaction_id=transaction.id,
            transaction_date=transaction.transaction_date,
            account_id=transaction.account_id,
            account_name=account_name,
            category_id=transaction.category_id,
            category_name=category_name,
            type=transaction.type,
            amount=transaction.amount,
            description=transaction.description,
        )
        for transaction, account_name, category_name in recent_rows
    ]
    top_category = spending.categories[0] if spending.categories else None
    insights = DashboardFinanceInsights(
        as_of=today,
        month=spending.month,
        top_spending_category=(
            DashboardTopSpendingCategory(
                category_id=top_category.category_id,
                category_name=top_category.category_name,
                amount=top_category.amount,
                transaction_count=top_category.transaction_count,
                share_percentage=top_category.share_percentage,
            )
            if top_category
            else None
        ),
        upcoming_recurring=DashboardUpcomingRecurring(
            period_start=upcoming.period_start,
            period_end=upcoming.period_end,
            window_days=30,
            total_income=upcoming.total_income,
            total_expenses=upcoming.total_expenses,
            net=upcoming.net,
            occurrence_count=sum(
                len(group.occurrences) for group in upcoming.date_groups
            ),
        ),
    )

    return DashboardFinances(
        monthly_income=monthly_income,
        monthly_expenses=monthly_expenses,
        monthly_balance=monthly_income - monthly_expenses,
        account_balances=account_balances,
        recent_transactions=recent_transactions,
        insights=insights,
    )


async def get_summary(
    session,
    *,
    user_id: uuid.UUID,
    today: date | None = None,
) -> DashboardSummary:
    today = today or current_app_date()
    habits = await get_habits(session, user_id=user_id, today=today)
    savings = await get_savings(session, user_id=user_id)
    finances = await get_finances(session, user_id=user_id, today=today)
    return DashboardSummary(habits=habits, savings=savings, finances=finances)
