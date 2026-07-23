# Architectural Decision Records

Each entry is an immutable record of a significant decision. Newest first.

Format: `## NNN — Title (YYYY-MM-DD, status)`.

---

## 016 - OCI Free Tier single-VM deployment with Nginx (2026-07-23, accepted)

HabitFlow supports an optional OCI Always Free deployment on one ARM64 Ampere
VM. Docker Compose runs Nginx, FastAPI, and PostgreSQL 17 on the same VM.
Nginx is the only public service: it terminates TLS, serves the Vue SPA, and
proxies `/api/` to FastAPI. PostgreSQL is available only through an internal
Docker network and persists below `/srv/habitflow`.

**Why:** A solo developer needs a practical, low-cost deployment path without
introducing Kubernetes, Terraform, a managed database cost, or a provider
dependency in application code.

**Migration controls:** Production uses `MIGRATE_ON_START=false`. The OCI
release script runs one serialized `backend/migrate.sh` command after a
verified PostgreSQL backup and before starting application services. Certbot
uses a persistent webroot challenge and certificate volume. External env files
remain outside the repository with restricted permissions.

**Consequences:** The VM is a single point of failure and local PostgreSQL
backups alone are insufficient for durable recovery. OCI Object Storage or
another off-VM target, restore rehearsals, disk monitoring, and a custom domain
are operational requirements. Render remains transitional until a separately
planned data and DNS cutover is complete.

---

## 015 - Cloud-neutral deployment and serialized production migrations (2026-07-23, accepted)

HabitFlow deploys as a static frontend artifact, a FastAPI container, and
managed PostgreSQL without provider-specific application configuration. Local
Docker Compose and transitional Render deployments retain migration-on-start.

**Why:** A migration to another cloud provider must not require business-code
changes or force a simultaneous frontend and backend deployment model.

**Deployment controls:** `MIGRATE_ON_START` defaults to `true` for local and
transitional deployments. Multi-replica production deployments must run
`alembic upgrade head` once through `backend/migrate.sh`, then start API
replicas with `MIGRATE_ON_START=false`. `PORT` defaults to `8000` so container
platforms can provide their own port. Liveness and readiness endpoints are
separate from the existing backward-compatible health endpoint.

**Consequences:** The frontend is built as a static SPA artifact and must be
rebuilt when `VITE_API_URL` changes. Production deployment documentation uses
cloud-neutral terminology. Remote smoke tests use `BASE_URL` and dedicated
test credentials; provider-specific automation remains deferred until a
target cloud is selected.

---

## 014 - HttpOnly refresh-token transport for public release (2026-07-22, accepted)

Refresh tokens are transported exclusively in a host-only, HttpOnly cookie. Login and refresh return only the short-lived access token in JSON. Refresh and logout read the cookie; refresh rotation replaces it and logout clears it after revocation.

**Why:** The frontend must not receive a long-lived bearer credential in JSON or Web Storage. The cookie preserves reloadable sessions without exposing refresh tokens to JavaScript.

**Security controls:** Cookie-authentication endpoints require an explicit allowed `Origin` and `X-CSRF-Protection: 1`. CORS allows credentials only for configured explicit origins. Local development uses `Secure=false; SameSite=Lax`; production same-site deployments use `Secure=true; SameSite=Lax`, while truly cross-site deployments use `Secure=true; SameSite=None`.

**Consequences:** The API contract for login, refresh, and logout is breaking. Existing clients must be deployed with credentialed requests before the feature is usable end-to-end. Refresh-token rotation and reuse detection remain unchanged.

---

## 013 - Frontend session policy for the internal MVP (2026-07-20, accepted)

Refresh tokens are intentionally kept only in frontend memory for the active browser runtime. They must not be persisted in `localStorage` or `sessionStorage` for the internal MVP.

**Why:** Web Storage is accessible to JavaScript running on the origin. Persisting a long-lived bearer credential there would increase the impact of an XSS compromise. The application is not yet public, so forcing reauthentication after access-token expiry is an acceptable usability trade-off.

**Current behaviour:**

- The access token and user are persisted to restore a session after reload.
- The refresh token is available only until the current frontend runtime ends.
- A reloaded session cannot refresh an expired access token and is redirected to login after an authentication failure.
- Logout before a reload can revoke the in-memory refresh token through the existing logout endpoint.
- Logout after a reload clears the local session but cannot revoke the previously issued refresh token because it is no longer available to the frontend.

**Public-release gate:** Replace refresh-token JSON/Web Storage handling with a `Secure`, `HttpOnly`, `SameSite` cookie or an approved Backend-for-Frontend design. Keep access tokens short-lived and preferably memory-only, preserve rotation and reuse detection, revoke the server-side session during logout, clear the cookie, and add required CSRF and credentialed-request controls. This requires Sol approval and an API contract update before implementation.

**Consequences:** The current internal MVP explicitly trades persistent post-expiry sessions and guaranteed logout revocation after reload for reduced refresh-token exposure. The public-release migration is tracked in the backlog and roadmap.

---

## 001 — Single currency: COP (2026-06-03, accepted)

We support Colombian Pesos only. No FX, no conversion. All monetary fields are stored as integer cents (`BIGINT`).

**Why:** Keeps the MVP small. Multi-currency requires FX rates, rounding policy, and reporting complexity out of scope.

**Consequences:** Display layer formats COP. No conversion anywhere in the stack.

---

## 002 — Modular monolith over microservices (2026-06-03, accepted)

A single FastAPI service with internal module boundaries, not separate services.

**Why:** MVP doesn't justify network overhead, deployment, and observability cost. Module boundaries inside one process give us clean seams to split later.

**Consequences:** One Dockerfile, one deploy unit. Cross-module calls are plain Python imports.

---

## 003 — Dashboard metrics are queries, not tables (2026-06-03, accepted)

Dashboard data is computed on read by aggregating transactions, habits, and savings.

**Why:** Avoids drift between a denormalized dashboard table and the source of truth.

**Consequences:** Dashboard endpoints may be slower at scale. When they are, we add materialized views — not a writable table.

---

## 004 — Repository + Service per module (2026-06-03, accepted)

Every module under `app/modules/<name>/` has `models.py`, `schemas.py`, `repository.py`, `service.py`, `routes.py`.

**Why:** Forces a single direction of dependencies. Easy to test, easy to refactor.

**Consequences:** More files, but each one has one job.

---

## 005 — No raw SQL outside migrations (2026-06-03, accepted)

All queries go through SQLAlchemy 2.0 ORM/Core. Alembic is the only place that emits DDL.

**Why:** Reproducibility, type safety, and migration review.

**Consequences:** When a query is awkward, we improve the schema, not bypass the ORM.

---

## 006 — Frontend talks to backend only through Pinia stores (2026-06-03, accepted)

Components never call `services/` directly. They call store actions.

**Why:** One place to invalidate state, handle loading/error, and add cross-cutting concerns.

**Consequences:** Slight indirection, but consistent data flow.

---

## 007 — Async FastAPI (2026-06-03, accepted)

The API is async end-to-end. SQLAlchemy is used with the async engine.

**Why:** Keeps the door open for non-blocking I/O (notifications, external APIs) without rewriting routes.

**Consequences:** Repositories use `AsyncSession`. Tests use an async test client.

---

## 008 — Refresh-token rotation with reuse detection (2026-06-08, accepted)

Refresh tokens are rotated on every successful `/auth/refresh`. The consumed token is revoked, and a fresh pair (access + refresh) is issued. If a refresh token that is *already revoked* is presented, the entire family of tokens for that user is revoked and `RefreshTokenReuse` is raised.

**Why:** A refresh token presented twice in succession is the canonical signal of theft (or of a buggy client double-sending the request). Rotation alone does not detect this; without reuse detection, a stolen token would remain valid until its `expires_at`. The standard mitigation is to treat any reuse as compromise and force re-authentication.

**How:** The model is a simplified family model. There is no `family_id` column — a "family" is implicitly the set of refresh tokens for one user. The invariant "at most one active refresh token per user at a time" is enforced by `_issue_token_pair`, which always issues a fresh token and revokes the consumed one on the same call. A revoked token that is presented twice is therefore always evidence of compromise, not of a legitimate concurrent client.

**Trade-offs:**

- A user cannot have multiple devices logged in simultaneously and refresh across them. The most recent successful refresh revokes the previous device's token. This is acceptable for the MVP — the API contract describes single-session behaviour, and the frontend only runs in one tab at a time.
- A more flexible design would add a `family_id` (one per login) and treat each family independently. That would allow concurrent sessions on multiple devices, at the cost of one column and slightly more complex detection logic.

**Upgrade path:** When multi-device support is needed, add a `family_id UUID` column to `refresh_tokens` and replace the "all tokens for this user" revocation with "all tokens in the family". The detection trigger stays the same.

**Consequences:**

- The repository exposes `get_by_hash` (returns any row by hash, regardless of revocation) so the service can detect reuse. `get_active_by_hash` is kept for the logout path, which is the only legitimate caller that wants to skip revoked rows.
- The service raises `RefreshTokenReuse` (a `DomainError` with HTTP 401 and `error.code = "refresh_token_reuse_detected"`) on detection. The frontend must handle this by redirecting to login.
- Tests assert: single rotation works; a second rotation attempt with the old token raises `RefreshTokenReuse`; logout-then-refresh raises `RefreshTokenReuse` (a logged-out token is a revoked token, by definition).

---

## 009 — Habits module design (2026-06-17, accepted)

The `habits` module supports two tracking modes in one table: `boolean` (did/didn't) and `numeric` (counted against a target). A single `HabitLogIn` request shape covers both, and the service resolves which fields are required/forbidden against the parent habit's `tracking_mode`.

**Why:** Habits are heterogeneous — "took vitamins" is binary, "walked 10,000 steps" is a count. Modelling them as two separate tables would mean duplicated CRUD, two log endpoints, and a confusing frontend API. A discriminated union is tempting but Pydantic 2 requires the discriminator to be a `Literal` field on every variant, which doesn't fit a uniform "did X with value V" client shape. A single input schema + service-side validation is the smallest surface that works.

**How it works:**

- `Habit.tracking_mode` is `boolean` or `numeric`. `target_value` and `unit` are non-null only for numeric; this is enforced by both a Pydantic schema *and* a service-layer invariant check (`_validate_tracking_shape`). The service is the source of truth so it raises our domain `ValidationError` (HTTP 400 with `error.code = "validation_error"`) regardless of where the call came from.
- `HabitLogIn.logged_value: int | None` is the single optional field. The service rejects a missing value for numeric habits and a present value for boolean habits.
- Logging is **idempotent per day**: the unique constraint `(habit_id, logged_on)` plus `ON CONFLICT DO UPDATE` (Postgres) / SQLite's equivalent makes a second POST on the same day an upsert, not a duplicate. The same `id` is returned.
- `completed` is **stored AND derived on read**. The service writes the result of `_derive_completed(habit, logged_value)` on insert/update, then re-runs the same function on every read (`_recompute_completed_in_place`) so a stale row (e.g. after the user raises `target_value` from 5000 to 10000) never leaks into the API. The stored column is a redundant optimization for dashboard-style reads that need the column directly; the derived value is the source of truth for the API response.
- Streak = number of consecutive *completed* days ending at or after yesterday. `current` resets to 0 if the most recent completed day is older than yesterday. `longest` is the maximum run anywhere in the log. Both are computed in pure Python over a list of completed days pulled from the DB — no window functions, no extra columns.
- `tracking_mode` cannot be changed after creation (no `HabitUpdate.tracking_mode`). Switching modes requires delete + recreate; doing it in place would require migrating every existing log's shape, which isn't worth the complexity for MVP.

**Trade-offs:**

- The single `HabitLogIn` schema means a `logged_value` typo on a boolean habit (or a missing value on a numeric one) is caught by the service, not by Pydantic at request-binding time. The error still surfaces as a clean 400 with our standard error envelope, but it's a 400 from our handler rather than a 422 from FastAPI's validation. We accept this in exchange for a uniform client shape.
- The Python-side streak calc pulls a (potentially long) list of dates from the DB. For a personal-scale app this is fine; for a multi-year history we'd switch to a SQL window function and keep the calc in the database.
- ON CONFLICT DO UPDATE is dialect-specific (Postgres vs SQLite). The repository picks the right insert builder per `session.bind.dialect.name` so tests can run on SQLite while production runs on Postgres.

**Consequences:**

- New module files: `app/modules/habits/{models,schemas,repository,service,routes}.py`, plus migration `20260616_0900_habits.py`.
- Routes (all under `/api/v1/habits`, all require auth): `POST /`, `GET /`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, `POST /{id}/logs`, `DELETE /{id}/logs/{date}`, `GET /{id}/streak`.
- Cross-user access returns 404 (not 403) so the API doesn't leak the existence of other users' habits.
- Delete is hard delete with `ON DELETE CASCADE` on `habit_logs`; no soft-delete column.
- `frequency` is currently a single-value column (`daily`) with a `CHECK` constraint, reserved for future weekly/custom schedules.

---

## 010 - Savings module design (2026-06-17, accepted)

The `savings` module tracks a goal and its manual contributions. Goal progress and completion percentage are computed from the contribution sum on read, while goal `status` is still stored so the API can return a stable shape and the service can keep the row aligned with the derived state.

**Why:** Savings goals are simple aggregates. A separate progress table would duplicate source-of-truth data and create drift risk. Keeping progress derived from contributions preserves a single write path and avoids stale summaries.

**How it works:**

- `SavingGoal` uses the table name `saving_goals` and stores `name`, `description`, `target_amount`, `target_date`, `status`, `created_at`, and `updated_at`.
- `SavingContribution` uses the table name `saving_contributions` and stores `saving_goal_id`, `amount`, `note`, `contribution_date`, `created_at`, and `updated_at`.
- `amount` is strictly positive. `target_amount` is also strictly positive. The service validates both so invalid writes return our domain `ValidationError` envelope.
- `status` is service-managed with the values `active` and `completed`.
- Goal progress is calculated dynamically as the sum of contributions for that goal. The completion percentage is capped at 100.
- Contributions after completion are allowed; the status remains `completed` and the progress percentage stays capped.
- All reads are user-scoped. Cross-user access returns 404 so the API does not reveal whether another user has a goal.

**Consequences:**

- New module files: `app/modules/savings/{models,schemas,repository,service,routes}.py`, plus migration `20260617_0900_savings.py`.
- Routes (all under `/api/v1/savings/goals`, all require auth): `GET /`, `POST /`, `GET /{id}`, `PATCH /{id}`, `DELETE /{id}`, `GET /{id}/contributions`, `POST /{id}/contributions`, `GET /{id}/progress`.
- There are no savings challenges or recurring savings in this sprint.

---

## 011 — Finances module design (2026-06-17, accepted)

The `finances` module models accounts, categories, transactions, and recurring transaction rules. Balances are derived from stored history, and recurring transactions remain declarative rules in this sprint.

**Why:** Finance history must remain auditable. Storing balances would create reconciliation drift and make deletion semantics ambiguous. Keeping recurring transactions as rules only avoids side effects before the scheduler exists.

**How it works:**

- `Account` stores `name`, `type`, `initial_balance`, `created_at`, and `updated_at`. Allowed types are `checking`, `savings`, `cash`, and `credit`.
- `Category` stores `name`, `type`, `created_at`, and `updated_at`. Allowed types are `income` and `expense`.
- `Transaction` stores `account_id`, `category_id`, `type`, `amount`, `description`, `transaction_date`, `created_at`, and `updated_at`. `category_id` is required.
- `RecurringTransaction` stores the same ownership and classification fields plus `frequency`, `start_date`, `end_date`, `last_generated_at`, `is_active`, `created_at`, and `updated_at`.
- `amount` is strictly positive. `initial_balance` is zero or positive.
- Transaction type and category type must match. The service validates this on create and update.
- Account balance is calculated dynamically as `initial_balance + income - expenses`.
- Recurring transactions are rules only. The service does not materialize real transactions in this sprint.
- Deleting an account or category is blocked if dependent transactions or recurring rules exist.
- All reads are user-scoped. Cross-user access returns 404.

**Consequences:**

- New module files: `app/modules/finances/{models,schemas,repository,service,routes}.py`, plus migration `20260617_1200_finances.py`.
- Routes (all under `/api/v1/finances`, all require auth): `GET/POST /accounts`, `GET/PATCH/DELETE /accounts/{id}`, `GET/POST /categories`, `GET/PATCH/DELETE /categories/{id}`, `GET/POST /transactions`, `GET/PATCH/DELETE /transactions/{id}`, and `GET/POST/PATCH/DELETE /recurring`.
- Future dashboard work can reuse the same derived balance and transaction aggregates without new storage columns.

---

## 012 - Dashboard module design (2026-06-17, accepted)

The `dashboard` module is read-only. It composes aggregates from habits, savings, and finances without creating dashboard tables or duplicating source-of-truth data.

**Why:** Dashboard data is presentation-layer synthesis. Persisting it would introduce drift and require invalidation logic that the MVP does not need.

**How it works:**

- `GET /api/v1/dashboard/summary` returns the combined habits, savings, and finances payload.
- `GET /api/v1/dashboard/habits`, `/savings`, and `/finances` return the same section payloads independently.
- `total_active_habits` means total owned habits because habits have no `is_active` flag in this sprint.
- `nearest_goal` means the nearest active goal with a non-null `target_date`; if none exists, the field is `null`.
- `today` and current-month calculations use the server/app current date. No timezone complexity is introduced in this sprint.
- All metrics are derived from existing tables using scoped queries and aggregate functions where reasonable.
- COP only. No floating-point math.

**Consequences:**

- New module files: `app/modules/dashboard/{models,schemas,repository,service,routes}.py`.
- The dashboard layer depends on existing modules for data, but does not write any data itself.
- Future caching can be added around the service layer without changing the response contract.
