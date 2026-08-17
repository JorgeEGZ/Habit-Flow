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

Migrations run automatically when the backend starts. See
[DEPLOYMENT.md](DEPLOYMENT.md) for cloud-neutral production deployment,
serialized release migrations, environment settings, health checks, and
cutover guidance. The Oracle Cloud Free Tier single-VM Nginx option is
documented in [deploy/oci/README.md](deploy/oci/README.md).
The production release audit and operator checklist are available in
[docs/PRODUCTION_READINESS.md](docs/PRODUCTION_READINESS.md) and
[docs/PRODUCTION_CHECKLIST.md](docs/PRODUCTION_CHECKLIST.md). Record final
infrastructure evidence with the redacted
[docs/PRODUCTION_LAUNCH_EVIDENCE.md](docs/PRODUCTION_LAUNCH_EVIDENCE.md)
template.

## Continuous Integration

GitHub Actions runs required `backend`, `frontend`, `e2e`, and `pwa` checks for
pull requests to `main` and pushes to `main`. The backend job runs Alembic
against PostgreSQL; the existing backend test suite keeps its isolated SQLite
fixtures. A supplementary `deployment` job validates OCI Nginx rate limits,
backup enforcement mocks, Compose placeholders, and POSIX shell syntax. Keep
the four named checks as branch-protection requirements; repository settings
must be verified separately.

Remote read-only smoke tests are intentionally manual/deferred. A future
cloud-neutral workflow will require `BASE_URL`, `E2E_EMAIL`, and
`E2E_PASSWORD` as repository or environment secrets; do not commit these
values. Render remains a supported transitional deployment target.
