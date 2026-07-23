# HabitFlow Deployment Guide

HabitFlow is cloud-neutral. The recommended production topology uses a static
frontend host, a FastAPI container platform, and managed PostgreSQL.

```text
Static frontend/CDN -> HTTPS -> FastAPI container -> managed PostgreSQL
```

Prefer custom domains under the same registrable domain, for example
`app.example.com` and `api.example.com`. The frontend and backend can deploy
independently as long as the frontend is built with the correct API URL.

For a cost-conscious single-VM Oracle Cloud Free Tier deployment that serves
the static SPA and API from one Nginx origin and runs PostgreSQL locally, see
[the OCI Nginx deployment guide](deploy/oci/README.md). That guide is an
optional production topology, not a replacement for the cloud-neutral contract
in this document.

## Production Components

### Frontend

Build the frontend with:

```bash
cd frontend
npm ci
npm run build
```

Publish `frontend/dist` to a static host. Configure the host to return
`index.html` for unknown application routes so Vue Router can handle SPA
navigation. `VITE_API_URL` is a build-time value and must include `/api/v1`.
A new frontend build is required when the API origin changes.

`frontend/Dockerfile` runs the Vite development server and is intended for
local development. It is not the recommended production frontend server.

### Backend

Build and run `backend/Dockerfile` on a container platform. The image starts
`backend/start.sh` through `sh`, so it does not depend on the executable bit
of a bind-mounted script.

The process listens on `PORT`, defaulting to `8000`. The platform should route
HTTPS traffic to that container port and use the readiness endpoint below.

### PostgreSQL

Use managed PostgreSQL with TLS, automated backups, point-in-time recovery,
and a connection limit appropriate for the planned backend replica count. The
application does not require PostgreSQL extensions.

Provider URLs often use `postgres://` or `postgresql://`. Configure
`DATABASE_URL` with SQLAlchemy's async driver form instead:

```text
postgresql+asyncpg://USER:PASSWORD@HOST:PORT/DATABASE
```

Validate the provider's TLS parameters with asyncpg before cutover. The same
`DATABASE_URL` must be available to both the release migration and the API.

## Environment Contract

| Variable | Host local | Docker Compose | CI | Production |
| --- | --- | --- | --- | --- |
| `DATABASE_URL` | `localhost:5433` | `postgres:5432` | `localhost:5432` | Managed PostgreSQL TLS URL |
| `SECRET_KEY` | Development value | Development value | CI-only value | Stable secret, at least 32 bytes |
| `ENVIRONMENT` | `development` | `development` | `development` | `production` |
| `DEBUG` | `false` | `false` | `false` | `false` |
| `APP_TIMEZONE` | `America/Bogota` | Same | Same | Explicit IANA timezone |
| `CORS_ORIGINS` | Local frontend origin | Local frontend origin | Local frontend origin | Exact HTTPS frontend origins |
| `REFRESH_COOKIE_SECURE` | `false` | `false` | `false` | `true` |
| `REFRESH_COOKIE_SAMESITE` | `lax` | `lax` | `lax` | `lax` for same-site, `none` for cross-site |
| `PORT` | `8000` | `8000` | `8000` | Provider port or `8000` |
| `MIGRATE_ON_START` | `true` | `true` | `true` | `false` with a release migration |
| `VITE_API_URL` | Local API origin | Local API origin | Local API origin | Public API origin ending in `/api/v1` |

The backend validates that credentialed CORS origins are explicit. Set
`CORS_ORIGINS` as a JSON list containing only frontend origins, with no
wildcard and no path component.

Refresh tokens are host-only HttpOnly cookies. Production requires
`REFRESH_COOKIE_SECURE=true`. Use `SameSite=lax` when frontend and API are
same-site subdomains. Use `SameSite=none` only when the frontend and API are
truly cross-site; it requires `Secure=true` and can be affected by browser
third-party-cookie policies.

`SECRET_KEY` is security-sensitive and must remain stable through a database
migration if existing signed tokens should remain valid. Never commit it.

## Migrations And Startup

`backend/migrate.sh` runs `alembic upgrade head` and fails fast. The default
startup behavior remains migration-on-start:

```text
MIGRATE_ON_START=true
```

This preserves local Docker Compose and transitional Render behavior. For a
multi-replica production deployment, run exactly one serialized release job:

```bash
sh /app/migrate.sh
```

Then deploy API replicas with:

```text
MIGRATE_ON_START=false
```

Do not let multiple API replicas apply migrations concurrently.

## Health Checks

| Endpoint | Purpose | Database query |
| --- | --- | --- |
| `/api/v1/health` | Backward-compatible health endpoint | Yes |
| `/api/v1/health/live` | Liveness: API process can serve requests | No |
| `/api/v1/health/ready` | Readiness: API can reach PostgreSQL | Yes |

Use `/api/v1/health/live` for liveness and `/api/v1/health/ready` for
readiness or startup checks. Readiness returns HTTP 503 when PostgreSQL is
unavailable.

## Migration Checklist

1. Choose the target container platform, static host, managed PostgreSQL and
   custom domains.
2. Provision PostgreSQL, backups, point-in-time recovery, TLS and migration
   permissions.
3. Rehearse `pg_dump` and restore into a non-production database.
4. Verify `alembic current` matches `alembic heads` after restore.
5. Deploy the backend against the restored database and run readiness checks.
6. Build the frontend with the target `VITE_API_URL` and configure SPA
   fallback.
7. Configure exact CORS origins and production cookie settings.
8. Lower DNS TTL before the production cutover.
9. Pause writes on the old deployment, take the final backup and restore it.
10. Run one release migration, deploy API replicas, then verify health and
    critical user journeys.
11. Switch DNS and monitor errors, authentication and database connections.
12. Keep the old deployment available but read-only until rollback risk has
    passed.

Do not allow the old and new databases to accept writes after the final copy.
Changing the API hostname cannot migrate existing host-only refresh cookies,
so users may need to sign in again after cutover.

## Smoke Testing

Local writable smoke tests run against localhost only:

```bash
cd frontend
npm run test:e2e:local
```

Cloud-agnostic remote smoke tests are read-only and require a dedicated test
account:

```bash
BASE_URL=https://app.example.com E2E_EMAIL=... E2E_PASSWORD=... npm run test:e2e:remote
```

Do not run remote smoke tests against a personal account. A provider-neutral
remote GitHub Actions workflow is intentionally deferred until the target
cloud and its secret-management model are chosen.

## Transitional Render Note

Render remains supported during migration because it uses the same backend
container contract. The previous Render-specific smoke-test terminology is
kept as a backwards-compatible npm alias only. No new deployment work should
depend on Render-specific configuration.
