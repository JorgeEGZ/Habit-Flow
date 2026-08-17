# HabitFlow Production Checklist

Complete this checklist for every production environment and release. Record
redacted command output, timestamps, and operator initials in
`PRODUCTION_LAUNCH_EVIDENCE.md` or the release ticket. Never paste secrets,
cookies, tokens, database URLs, signed URLs, public IP addresses, or personal
finance data into evidence.

## Release Metadata

| Field | Value |
| --- | --- |
| Release version / commit | |
| Deployment target | |
| Operator / reviewer | |
| Planned window | |
| Rollback revision | |
| RPO objective | 24 hours |
| RTO objective | 4 hours |
| Primary incident contact | |
| Backup and recovery contact | |

## Pre-Deploy

- [ ] The target domain, reserved OCI IP, and HTTPS certificate plan are approved.
- [ ] `CORS_ORIGINS` contains only exact HTTPS frontend origins.
- [ ] `ENVIRONMENT=production`, `DEBUG=false`, a random stable 32-byte-plus
  `SECRET_KEY`, `REFRESH_COOKIE_SECURE=true`, and same-site
  `REFRESH_COOKIE_SAMESITE=lax` are configured.
- [ ] External environment files are outside the repository with mode `600`.
- [ ] `OFFSITE_BACKUP_REQUIRED=true` and a private Object Storage namespace and
  bucket are configured without OCI credential variables.
- [ ] The instance principal has least-privilege write/head access only to the
  intended private bucket, and bucket encryption at rest is verified.
- [ ] Auth limits are active at OCI Nginx for login, registration, and refresh.
- [ ] Required GitHub checks are configured as `backend`, `frontend`, `e2e`,
  and `pwa`; the supplementary deployment smoke is not a substitute for them.

## Backup, Restore, And Migration

- [ ] A pre-migration backup succeeds before `alembic upgrade head`.
- [ ] `pg_restore --list` and `sha256sum -c` succeed for the final dump name.
- [ ] Both dump and checksum objects exist in private Object Storage.
- [ ] Daily backups, seven-day local retention, 30-day off-VM retention, and
  backup-age monitoring are configured.
- [ ] A real remote backup was restored into an isolated non-production target.
- [ ] The rehearsal verified checksum, dump listing, PostgreSQL/Alembic versions,
  `alembic current` equal to `alembic heads`, and non-sensitive table counts.
- [ ] Login and representative read-only habits, savings, and finance smoke
  passed against the restored environment.
- [ ] Restore duration and backup age meet the 4-hour RTO and 24-hour RPO.
- [ ] Production uses `MIGRATE_ON_START=false`; the release process runs the
  serialized migration command once.

## Final Domain, TLS, Cookies, And Network

- [ ] DNS A resolves to the reserved OCI IP and no unintended AAAA record exists.
- [ ] HTTP redirects to the exact HTTPS domain; certificate hostname, chain,
  expiry, TLS 1.2, and TLS 1.3 are verified.
- [ ] HTTPS `GET /api/v1/health/live` and `/api/v1/health/ready` succeed.
- [ ] SPA deep links and PWA service-worker control work over HTTPS.
- [ ] The refresh cookie is Secure, HttpOnly, SameSite=Lax, and
  Path=`/api/v1/auth`, with no unintended Domain attribute.
- [ ] A trusted Origin with credentials works; an untrusted Origin and a
  missing CSRF header are rejected.
- [ ] External scans show 80/443 open, SSH restricted, and 5432/8000/5173 closed.
- [ ] OCI NSG and UFW evidence is recorded. Do not enable HSTS or strict host
  rejection until final-domain HTTPS validation and separate approval are complete.

## GitHub Branch Protection

- [ ] Pull requests are required for `main`.
- [ ] The branch must be current before merge.
- [ ] `backend`, `frontend`, `e2e`, and `pwa` are required checks.
- [ ] Conversation resolution is required.
- [ ] Force pushes and branch deletion are blocked.
- [ ] Emergency bypass is restricted and documented.
- [ ] Screenshot or redacted `gh api` output is attached to the release record.

## Post-Deploy Verification And Rollback

- [ ] Dedicated-account remote read-only smoke passes.
- [ ] Dashboard, habits, savings, finances, budgets, reports, and exports load.
- [ ] CSV/XLSX responses remain authenticated, user-scoped, `private, no-store`,
  and formula-like user cells are inert.
- [ ] Disk, readiness, certificate expiry, backup age/failure, PostgreSQL health,
  and elevated 5xx alerts are verified.
- [ ] The previous image or revision is available and schema-compatible.
- [ ] Rollback never assumes an Alembic downgrade; writes are paused before a
  database recovery action and the current volume is preserved.
