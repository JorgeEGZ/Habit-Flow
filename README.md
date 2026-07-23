# HabitFlow

HabitFlow is a personal productivity and finance web app built with FastAPI, Vue 3, PostgreSQL, and Docker.

## Features

- Authentication
- Dashboard overview
- Daily habit tracking
- Habit management
- Savings goals
- Contribution history
- Personal finance tracking
- Accounts and categories
- Recurring transaction rules
- Responsive dark UI

## Tech Stack

Backend:
- FastAPI
- SQLAlchemy 2.0
- PostgreSQL
- Alembic
- JWT

Frontend:
- Vue 3
- Vite
- Pinia
- Vue Router
- PrimeVue
- Axios

Infrastructure:
- Docker
- Docker Compose

## Getting Started

### Backend

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
```

The Docker backend connects to PostgreSQL internally with
postgresql+asyncpg://habitflow:habitflow@postgres:5432/habitflow.

HabitFlow publishes PostgreSQL to host port 5433 to avoid conflicting with
other local containers or a host PostgreSQL installation. When running FastAPI
directly on the host, set backend/.env with:

    DATABASE_URL=postgresql+asyncpg://habitflow:habitflow@localhost:5433/habitflow

Verify the local API after Compose starts:

    curl http://localhost:8000/api/v1/health

## Continuous Integration

GitHub Actions runs required backend, frontend-build, and local Playwright
checks for pull requests to `main` and pushes to `main`. The backend job runs
Alembic against PostgreSQL; the existing backend test suite keeps its isolated
SQLite fixtures.

Render read-only smoke tests are intentionally manual/deferred. A future
workflow will require `RENDER_BASE_URL`, `E2E_EMAIL`, and `E2E_PASSWORD` as
repository or environment secrets; do not commit these values.
