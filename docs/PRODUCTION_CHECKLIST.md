# HabitFlow Production Checklist

Complete this checklist for every new production environment and release.
Record command output, timestamps, and operator initials in the release ticket.
Never paste secrets, cookies, access tokens, refresh tokens, database URLs, or
private IP addresses into the ticket.

## Release Metadata

| Field | Value |
| --- | --- |
| Release version / commit | |
| Deployment target | |
| Operator | |
| Reviewers | |
| Planned window | |
| Rollback revision | |
| RPO | |
| RTO | |
| Primary incident contact | |
| Backup/recovery contact | |

## Pre-Deploy

- [ ] The target domain and HTTPS certificate plan are approved.
- [ ] A reserved public IP, DNS record, and final frontend origin are known.
- [ ] `CORS_ORIGINS` contains only exact HTTPS frontend origins.
- [ ] `ENVIRONMENT=production` and `DEBUG=false` are set.
- [ ] `SECRET_KEY` is stable, random, and at least 32 bytes.
- [ ] `REFRESH_COOKIE_SECURE=true` is set.
- [ ] `REFRESH_COOKIE_SAMESITE=lax` is used for same-site deployment, or the
  cross-site exception has been reviewed.
- [ ] External environment files are outside the repository and mode `600`.
- [ ] PostgreSQL password is unique and non-development.
- [ ] `DATABASE_URL` uses `postgresql+asyncpg` and the correct internal host.
- [ ] Auth abuse protection is active for login, registration, and refresh.
- [ ] Required GitHub checks are protected: `backend`, `frontend`, `e2e`, and
  `pwa`.
- [ ] Release notes list migrations, known risks, and rollback revision.

## Infrastructure And Network

- [ ] Only 80 and 443 are public.
- [ ] SSH is restricted to the operator IP or VPN range.
- [ ] Ports 5432, 8000, and 5173 are not publicly reachable.
- [ ] OCI Nginx is the only public Compose service.
- [ ] PostgreSQL is on the internal data network only.
- [ ] Persistent PostgreSQL, certificate, backup, and log paths exist.
- [ ] Disk capacity covers database growth, backups, images, and logs.
- [ ] Nginx configuration validates before deployment.
- [ ] Certbot renewal is scheduled and its logs are monitored.
- [ ] HSTS and unknown-host protection have been verified against the final
  domain before enabling them.

## Backup And Restore

- [ ] A backup completed before migration.
- [ ] `pg_restore --list` succeeds for the backup.
- [ ] `sha256sum -c` succeeds from the backup directory.
- [ ] A private off-VM copy exists and its age meets the agreed RPO.
- [ ] Backup retention is configured and monitored.
- [ ] A recent backup was restored into an isolated PostgreSQL instance.
- [ ] Restored schema reports `alembic current` equal to `alembic heads`.
- [ ] Login and representative habits, savings, and finance workflows passed
  against the restored environment.
- [ ] Restore duration meets the agreed RTO.

## Migration And Deploy

- [ ] Migration commands run once through the release process.
- [ ] Production backend has `MIGRATE_ON_START=false`.
- [ ] Existing database backup completed before `alembic upgrade head`.
- [ ] Migration completed successfully and `alembic current` equals head.
- [ ] Backend image and production frontend image were built from the selected
  revision.
- [ ] Backend readiness succeeds before Nginx is considered healthy.
- [ ] Application rollback revision is schema-compatible with the deployed
  schema, or the rollback plan has been reviewed.

## Health And Security Verification

- [ ] `GET /api/v1/health/live` returns success.
- [ ] `GET /api/v1/health/ready` returns success.
- [ ] Readiness fails appropriately when tested against an unavailable
  database in a non-production environment.
- [ ] Login response sets the expected HttpOnly, Secure, SameSite, and Path
  cookie attributes.
- [ ] Refresh after a page reload succeeds.
- [ ] Logout clears the refresh cookie and blocks protected navigation.
- [ ] Password change revokes sessions and requires a new login.
- [ ] An untrusted Origin and missing CSRF header are rejected for cookie-auth
  operations.
- [ ] Browser network tools show no credentials in local/session storage.
- [ ] Production errors do not expose stack traces, SQL, or secrets.

## Frontend, PWA, And Exports

- [ ] Frontend was built with the final `VITE_API_URL` value.
- [ ] SPA deep links return `index.html` and render correctly.
- [ ] `sw.js` is served without immutable caching.
- [ ] Cache Storage contains no `/api/` responses.
- [ ] Offline navigation displays the static Spanish offline page, not stale
  user data.
- [ ] PWA update prompt works without automatically reloading a form.
- [ ] CSV/XLSX downloads require authentication and are user-scoped.
- [ ] Export responses include `Cache-Control: private, no-store`.
- [ ] CSV/XLSX samples open correctly and formula-like user text is inert.

## Post-Deploy Smoke And Monitoring

- [ ] Dedicated-account remote read-only smoke tests pass.
- [ ] Dashboard, habits, savings, finances, budgets, reports, and exports load.
- [ ] External uptime monitoring checks liveness and readiness.
- [ ] Alerts exist for readiness failure, disk exhaustion, certificate expiry,
  backup age/failure, PostgreSQL health, and elevated 5xx errors.
- [ ] Docker logs rotate and no credentials appear in sampled logs.
- [ ] Certificate renewal has completed or a dry run has passed.
- [ ] Release monitoring window and owner are recorded.

## Rollback And Incident Response

- [ ] The previous application image or Git revision is available.
- [ ] Rollback does not assume Alembic downgrade.
- [ ] Writes can be paused before a database recovery action.
- [ ] The current data volume is preserved before restoring any backup.
- [ ] Database restoration is first performed in isolation when time permits.
- [ ] DNS rollback and communication steps are documented.
- [ ] Incident owner, recovery owner, and decision authority are known.
