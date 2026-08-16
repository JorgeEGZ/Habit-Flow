# API Specification

Base URL: `/api/v1`
Auth: `Authorization: Bearer <access_token>`
Content type: `application/json`

## Conventions

- IDs are UUIDs.
- All money fields are integer cents.
- All dates are ISO 8601 (`YYYY-MM-DD`).
- Timestamps include timezone offset.
- Error format:

```json
{ "error": { "code": "string", "message": "string" } }
```

## Auth

### POST /auth/register

Request:
```json
{ "email": "user@example.com", "password": "...", "full_name": "..." }
```

Response 201:
```json
{ "id": "uuid", "email": "user@example.com", "full_name": "...", "created_at": "2026-06-08T12:00:00+00:00" }
```

### POST /auth/login

Request:
```json
{ "email": "user@example.com", "password": "..." }
```

Response 200:
```json
{
  "access_token": "...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

The response also sets an HttpOnly refresh-token cookie. The raw refresh token is never included in JSON.

### POST /auth/refresh

Reads and rotates the HttpOnly refresh-token cookie. The endpoint accepts no request body. If a refresh token that has *already been rotated or logged out* is presented, the entire family of tokens for that user is revoked and the request fails with `error.code = "refresh_token_reuse_detected"`.

Response 200:
```json
{ "access_token": "...", "token_type": "bearer", "expires_in": 1800 }
```

The refresh token is rotated and returned only as a replacement HttpOnly cookie.

### POST /auth/logout

Reads the HttpOnly refresh-token cookie, revokes it when present, and clears the cookie. The endpoint accepts no request body and is idempotent when the cookie is absent.

Response 204 (no body).

### Errors

| HTTP | `error.code` | When |
|---|---|---|
| 401 | `invalid_refresh_token` | Unknown or expired refresh token. |
| 401 | `refresh_token_reuse_detected` | A revoked refresh token was presented. The user must log in again. |

## Habits

All habit endpoints require `Authorization: Bearer <access_token>`. Cross-user access returns 404 (never 403), so a habit belonging to another user looks indistinguishable from a non-existent one.

### Habit shape

A habit has a `tracking_mode` of `boolean` (did/didn't) or `numeric` (counted against a target). Numeric habits require both `target_value` and `unit`; boolean habits must not declare either. The cross-field invariant is enforced by the service, so a violation returns `400 validation_error` regardless of which field was missing or extra.

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "title": "Read 20 min",
  "description": "...",
  "tracking_mode": "boolean" | "numeric",
  "target_value": 10000,
  "unit": "steps",
  "frequency": "daily",
  "created_at": "2026-06-17T10:00:00Z",
  "updated_at": "2026-06-17T10:05:00Z"
}
```

### GET /habits
Returns the current user's habits, oldest first.

### POST /habits
```json
// boolean
{ "title": "Take vitamins", "tracking_mode": "boolean" }
// numeric
{ "title": "Walk", "tracking_mode": "numeric", "target_value": 10000, "unit": "steps" }
```
Returns `201` with the habit shape.

### PATCH /habits/{id}
Partial update. Owner only. `tracking_mode` is not editable; delete and re-create to switch modes. Updates are validated against the merged state, so dropping `unit` on a numeric habit returns `400 validation_error`.

```json
{ "title": "Run", "target_value": 3000 }
```

### DELETE /habits/{id}
Owner only. Hard delete; logs cascade via the FK `ON DELETE CASCADE`. Returns `204`.

### POST /habits/{id}/logs
Logs progress for a single day. Idempotent per `(habit_id, logged_on)`: a second POST for the same day upserts and returns the same `id`.

```json
// boolean
{ "logged_on": "2026-06-15" }
// numeric
{ "logged_on": "2026-06-15", "logged_value": 12000, "note": "morning walk" }
```

Response (`200`):

```json
{
  "id": "uuid",
  "habit_id": "uuid",
  "logged_on": "2026-06-15",
  "completed": true,
  "logged_value": 12000,
  "note": "morning walk",
  "created_at": "2026-06-15T18:30:00Z",
  "updated_at": "2026-06-15T18:45:00Z"
}
```

`completed` is derived: boolean habits are always completed when a log row exists; numeric habits are completed iff `logged_value >= target_value` *at the time of the read*, so a stale row that no longer meets the target surfaces as `completed: false` automatically.

Errors:

| Status | Code | When |
| --- | --- | --- |
| 400 | `validation_error` | `logged_value` missing for a numeric habit, or present for a boolean one, or `logged_on` is in the future |
| 404 | `habit_not_found` | Habit does not exist or belongs to another user |

### DELETE /habits/{id}/logs/{logged_on}
Removes the log for the given day. Idempotent: deleting a non-existent log still returns `204`. Owner only.

### GET /habits/{id}/streak
```json
{ "current": 5, "longest": 12 }
```

`current` is the number of consecutive completed days ending at or before today. If the most recent completed day is older than yesterday, `current` is `0`. `longest` is the maximum run of consecutive completed days anywhere in the log. Only `completed` days count — incomplete logs do not break or extend a streak.

## Savings

All savings endpoints require `Authorization: Bearer <access_token>`. Cross-user access returns 404.

### Saving goal shape

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Emergency fund",
  "description": "...",
  "target_amount": 5000000,
  "target_date": "2026-12-31",
  "status": "active" | "completed",
  "created_at": "2026-06-17T10:00:00Z",
  "updated_at": "2026-06-17T10:00:00Z"
}
```

### GET /savings/goals
Returns the current user's goals, oldest first.

### POST /savings/goals
```json
{ "name": "Emergency fund", "description": "Buffer", "target_amount": 5000000, "target_date": "2026-12-31" }
```
Returns `201` with the goal shape.

### GET /savings/goals/{goal_id}
Returns the goal shape. Owner only.

### PATCH /savings/goals/{goal_id}
Partial update. Owner only. `status` is service-managed and cannot be edited directly.

### DELETE /savings/goals/{goal_id}
Owner only. Hard delete. Returns `204`.

### Saving contribution shape

```json
{
  "id": "uuid",
  "saving_goal_id": "uuid",
  "amount": 100000,
  "note": "...",
  "contribution_date": "2026-06-03",
  "created_at": "2026-06-03T10:00:00Z",
  "updated_at": "2026-06-03T10:00:00Z"
}
```

### GET /savings/goals/{goal_id}/contributions
Returns the contributions for the goal, oldest first.

### POST /savings/goals/{goal_id}/contributions
```json
{ "amount": 100000, "contribution_date": "2026-06-03", "note": "..." }
```
Returns `201` with the contribution shape.

### GET /savings/goals/{goal_id}/progress
```json
{
  "saving_goal_id": "uuid",
  "current_amount": 800000,
  "target_amount": 5000000,
  "completion_percentage": 16,
  "status": "active"
}
```
Progress is computed dynamically from contributions. The percentage is capped at 100.

## Finances

All finance endpoints require `Authorization: Bearer <access_token>`. Cross-user access returns 404.

### Account shape

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Main checking",
  "type": "checking",
  "initial_balance": 0,
  "current_balance": 1500,
  "created_at": "2026-06-17T10:00:00Z",
  "updated_at": "2026-06-17T10:00:00Z"
}
```

### GET /finances/accounts
### POST /finances/accounts
```json
{ "name": "Main checking", "type": "checking", "initial_balance": 0 }
```
### GET /finances/accounts/{id}
### PATCH /finances/accounts/{id}
### DELETE /finances/accounts/{id}
Delete is blocked while transactions or recurring rules reference the account.

### Category shape

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "name": "Salary",
  "type": "income",
  "created_at": "2026-06-17T10:00:00Z",
  "updated_at": "2026-06-17T10:00:00Z"
}
```

### GET /finances/categories
### POST /finances/categories
```json
{ "name": "Salary", "type": "income" }
```
### GET /finances/categories/{id}
### PATCH /finances/categories/{id}
### DELETE /finances/categories/{id}
Delete is blocked while transactions or recurring rules reference the category.

### Transaction shape

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "account_id": "uuid",
  "category_id": "uuid",
  "type": "expense",
  "amount": 25000,
  "description": "Lunch",
  "transaction_date": "2026-06-03",
  "created_at": "2026-06-03T10:00:00Z",
  "updated_at": "2026-06-03T10:00:00Z"
}
```

### GET /finances/transactions?account_id=&category_id=&from=&to=
### POST /finances/transactions
```json
{
  "account_id": "uuid",
  "category_id": "uuid",
  "type": "expense",
  "amount": 25000,
  "description": "Lunch",
  "transaction_date": "2026-06-03"
}
```
### GET /finances/transactions/{id}
### PATCH /finances/transactions/{id}
### DELETE /finances/transactions/{id}

### Recurring transaction shape

```json
{
  "id": "uuid",
  "user_id": "uuid",
  "account_id": "uuid",
  "category_id": "uuid",
  "type": "income",
  "amount": 5000000,
  "description": "Monthly salary",
  "frequency": "monthly",
  "start_date": "2026-06-01",
  "end_date": null,
  "last_generated_at": null,
  "is_active": true,
  "created_at": "2026-06-17T10:00:00Z",
  "updated_at": "2026-06-17T10:00:00Z"
}
```

### GET /finances/recurring
### POST /finances/recurring
```json
{
  "account_id": "uuid",
  "category_id": "uuid",
  "type": "income",
  "amount": 5000000,
  "description": "Monthly salary",
  "frequency": "monthly",
  "start_date": "2026-06-01",
  "end_date": null,
  "is_active": true
}
```
### GET /finances/recurring/{id}
### PATCH /finances/recurring/{id}
### DELETE /finances/recurring/{id}

Recurring transactions are rules only in this sprint. No automatic generation happens yet.

### Finance reports

### GET /finances/reports/monthly?month=YYYY-MM
### GET /finances/reports/monthly-trends?month=YYYY-MM
### GET /finances/reports/monthly.xlsx?month=YYYY-MM

All report endpoints are authenticated and read-only. `month` is optional and uses strict `YYYY-MM`; when omitted, the application month is resolved in `APP_TIMEZONE`. Reports use real transactions only, while the XLSX endpoint returns a four-worksheet workbook. See [Finance Reports](FINANCE_REPORTS.md) for response semantics, insight values, workbook headers, and frontend request coordination.

## Dashboard

All dashboard endpoints require `Authorization: Bearer <access_token>`. Data is calculated dynamically from habits, savings, and finances. Empty state returns zeros, empty arrays, and `null`. Current-day and current-month calculations use the server date. `total_active_habits` means total owned habits. `nearest_goal` means the nearest active goal with a non-null `target_date`.

### Dashboard summary shape

```json
{
  "habits": {
    "completed_today": 0,
    "total_active_habits": 0,
    "current_streak_summary": null,
    "longest_streak_summary": null
  },
  "savings": {
    "total_savings_contributed": 0,
    "active_goals_count": 0,
    "completed_goals_count": 0,
    "nearest_goal": null,
    "savings_progress_summary": {
      "current_amount": 0,
      "target_amount": 0,
      "completion_percentage": 0
    }
  },
  "finances": {
    "monthly_income": 0,
    "monthly_expenses": 0,
    "monthly_balance": 0,
    "account_balances": [],
    "recent_transactions": []
  }
}
```

### Dashboard habit shape

```json
{
  "completed_today": 0,
  "total_active_habits": 0,
  "current_streak_summary": {
    "habit_id": "uuid",
    "title": "Take vitamins",
    "current": 3,
    "longest": 5
  },
  "longest_streak_summary": {
    "habit_id": "uuid",
    "title": "Read",
    "current": 1,
    "longest": 12
  }
}
```

### Dashboard savings shape

```json
{
  "total_savings_contributed": 0,
  "active_goals_count": 0,
  "completed_goals_count": 0,
  "nearest_goal": {
    "saving_goal_id": "uuid",
    "name": "Emergency fund",
    "target_date": "2026-12-31",
    "status": "active",
    "current_amount": 200000,
    "target_amount": 5000000,
    "completion_percentage": 4
  },
  "savings_progress_summary": {
    "current_amount": 0,
    "target_amount": 0,
    "completion_percentage": 0
  }
}
```

### Dashboard finances shape

```json
{
  "monthly_income": 820000,
  "monthly_expenses": 310000,
  "monthly_balance": 510000,
  "account_balances": [
    { "account_id": "uuid", "name": "Checking", "type": "checking", "current_balance": 1285000 }
  ],
  "recent_transactions": [
    {
      "transaction_id": "uuid",
      "transaction_date": "2026-06-17",
      "account_id": "uuid",
      "account_name": "Checking",
      "category_id": "uuid",
      "category_name": "Salary",
      "type": "income",
      "amount": 500000,
      "description": "Pay"
    }
  ]
}
```

### GET /dashboard/summary
Returns the combined dashboard payload.

### GET /dashboard/habits
Returns habit metrics only.

### GET /dashboard/savings
Returns savings metrics only.

### GET /dashboard/finances
Returns finance metrics only.

## Health

### GET /health/
Public. Returns `{ "status": "ok", "version": "..." }`.
