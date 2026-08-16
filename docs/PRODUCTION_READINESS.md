# HabitFlow Production Readiness Report

**Audit date:** 2026-08-16  
**Audited source revision:** `1e09ba6` before Sprint 3.0 hardening changes  
**Scope:** repository configuration, deployment artifacts, CI, automated tests,
and documentation. No production infrastructure, secrets, DNS records, or
customer data were accessed during this audit.

## Executive Decision

**Status: NO-GO for a public production release.**

The repository has strong application-level controls: explicit credentialed
CORS origins, HttpOnly refresh-cookie transport, CSRF checks, refresh-token
rotation and reuse detection, readiness checks, serialized OCI migrations,
private export responses, and an online-first PWA that does not cache API
responses. These controls are necessary but do not prove production readiness.

Release remains blocked until the required manual evidence in
`PRODUCTION_CHECKLIST.md` is complete. In particular, HabitFlow needs a tested
authentication abuse control, an off-VM backup target, a successful restore
rehearsal, final TLS/cookie verification, and protected required CI checks.

## Assumptions And Topology

- The cloud-neutral topology is a static frontend, FastAPI container, and
  PostgreSQL database.
- The OCI option uses one ARM64 VM with Nginx as the only public service,
  FastAPI and PostgreSQL on internal Docker networks, and persistent paths
  under `/srv/habitflow`.
- Render remains transitional. It uses the same container contract but must
  use a serialized migration strategy when more than one backend replica runs.
- The preferred browser topology is a same-site custom domain with
  `REFRESH_COOKIE_SECURE=true` and `REFRESH_COOKIE_SAMESITE=lax`.
- Source inspection cannot prove final DNS, TLS, cloud firewall, secrets,
  backups, branch protection, monitoring, or restore capability.

## Existing Controls

| Area | Verified repository control |
| --- | --- |
| Runtime configuration | Non-development settings reject empty, placeholder, and short secrets; credentialed CORS requires explicit origins; insecure refresh-cookie combinations are rejected. |
| Authentication | Access tokens are memory-only; refresh tokens are host-only HttpOnly cookies; login, refresh, and logout require allowed Origin and CSRF header validation. |
| Session protection | Refresh tokens rotate, reuse revokes user tokens, and password changes revoke active refresh tokens. |
| Health | `/health/live` avoids PostgreSQL; `/health/ready` returns 503 when PostgreSQL is unavailable. |
| Database | Async SQLAlchemy uses `pool_pre_ping`; Alembic has one linear migration head; OCI deployment runs one explicit migration before app startup. |
| OCI network | Only Nginx publishes 80/443; PostgreSQL is internal to the data network; backend uses readiness health checks. |
| PWA | Service worker is production-only, bypasses `/api/`, and uses a static offline page rather than cached user data. |
| Exports | CSV/XLSX responses use `private, no-store`, user-scoped queries, deterministic filenames, and formula-like cell sanitization. |
| CI | `backend`, `frontend`, `e2e`, and `pwa` jobs cover migrations, build, real local E2E, and production-build PWA behavior. |

## Finding Matrix

| ID | Severity | Evidence | Impact | Remediation | Blocker | Verification | Owner / status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PR-001 | P0 | No repository evidence proves a final domain, TLS certificate, secure production cookie attributes, firewall rules, or branch protection settings. | A correct codebase can still be deployed insecurely. | Complete the manual pre-deploy and post-deploy checks. | Yes | Manual evidence | Release owner / open |
| PR-002 | P0 | No auth rate limiting exists in backend or OCI Nginx configuration. | Public login, registration, and refresh endpoints are susceptible to brute force and abuse. | Design and implement an edge or API rate-limit policy with monitoring and false-positive handling. | Yes | Automated plus manual | Sol / open |
| PR-003 | P0 | OCI off-VM backup upload is optional and no restore rehearsal evidence is versioned. | A VM, volume, or operator failure may cause unrecoverable data loss. | Configure private off-VM backups and rehearse a full isolated restore. Define RPO/RTO. | Yes | Manual evidence | Release owner / open |
| PR-004 | P1 | CI E2E waited for legacy `/api/v1/health`, which can return HTTP 200 while its database field is `unreachable`. | E2E could start before backend dependencies are ready. | Changed CI to wait for `/api/v1/health/ready`. | No after fix | CI E2E | Terra / fixed |
| PR-005 | P1 | Backup checksum was written before the dump rename and referenced the temporary filename. | Later checksum validation could fail despite a valid backup. | Generate and validate checksum after the final dump filename exists. | No after fix | Backup smoke and restore rehearsal | Terra / fixed |
| PR-006 | P1 | OCI backend container currently runs as root; no hardened runtime user is defined. | A container compromise has a larger local blast radius. | Validate a non-root backend image across local Compose, Render, OCI, migrations, and bind mounts before changing it. | Yes before public launch | Build and deployment test | Sol / open |
| PR-007 | P1 | Nginx lacks HSTS and explicit unknown-host handling; backend lacks TrustedHost middleware. | HTTPS downgrade and Host-header hardening are incomplete. | Add host rejection and HSTS only after final domains and HTTPS behavior are tested. | Yes before public launch | External TLS and host-header test | Sol / open |
| PR-008 | P1 | No verified alerting for readiness, disk, certificate expiry, backup age, database health, or 5xx errors. | Failures may be detected too late for recovery. | Configure an external uptime monitor and VM/database alert thresholds. | Yes before public launch | Manual alert test | Release owner / open |
| PR-009 | P2 | ADR 013 described the retired in-memory refresh-token transport as current behavior. | Operators may configure sessions incorrectly. | Marked ADR 013 superseded by the HttpOnly-cookie decision. | No | Documentation review | Terra / fixed |
| PR-010 | P2 | README omitted the required `pwa` CI check. | Branch protection can be configured incompletely. | Updated README and require all four checks in GitHub settings. | No | Manual GitHub review | Terra / partial |
| PR-011 | P2 | ADR numbering is historically duplicated for 013 and 014 after later sprints. | ADR references can be ambiguous. | Do not renumber accepted historical records; add unique title/date references and fix numbering policy in a future documentation cleanup. | No | Documentation review | Luna / open |
| PR-012 | P2 | Images and GitHub Actions use maintained tags/major versions rather than immutable digests; no dependency advisory process is documented. | Supply-chain changes can be less reproducible. | Enable Dependabot or an equivalent advisory process and evaluate digest pinning separately. | No | Repository settings review | Sol / open |
| PR-013 | P2 | Refresh-token rows are revoked but have no retention cleanup policy. | Database growth and retention exposure increase over time. | Define retention and a safe cleanup job after operational metrics exist. | No | Future migration/service design | Sol / deferred |
| PR-014 | P1 | `npm audit --omit=dev` reports high-severity advisories for transitive `postcss@8.5.15` and `nanoid@3.3.12` in the production frontend build dependency closure. | A compromised or crafted build input could affect build reliability or disclose build-machine files through the PostCSS advisory. | Upgrade or constrain the affected locked dependency chain in a separately approved security patch, then rerun build and PWA checks. | Yes unless a documented security exception is accepted | npm audit and CI build | Sol / open |
| PR-015 | P3 | Centralized logs, correlation IDs, strict CSP, multi-VM HA, managed secrets, PITR, and remote smoke CI are deferred. | Diagnosis and resilience remain limited for larger-scale usage. | Track separately after core release controls are in place. | No | Future roadmap | Product / deferred |

## Low-Risk Hardening Applied

- CI now waits for the database-aware readiness endpoint instead of the
  backward-compatible health endpoint.
- The OCI backup script writes and verifies a checksum for the final dump
  filename, so `sha256sum -c` works from the backup directory.
- Production-settings tests now cover known placeholder secrets and short
  secrets.
- ADR 013 now states that ADR 014 superseded its session transport model.
- README now lists `backend`, `frontend`, `e2e`, and `pwa` as required checks.

## Validation Evidence

Sprint 3.0 records command results after implementation. Commands must run
without secrets and outputs must not include production environment values.

| Check | Required result | Audit result |
| --- | --- | --- |
| Backend tests | Complete suite passes | Passed: 246 tests. One non-fatal Windows pytest-cache permission warning. |
| Frontend build | `npm.cmd run build` passes | Passed. |
| Local E2E | `npm.cmd run test:e2e:local` passes | Passed: 11 Chromium tests. |
| PWA E2E | `npm.cmd run test:e2e:pwa` passes | Passed: 3 Chromium tests. The Windows sandbox blocked Vite child-process access; rerun with local elevated filesystem access passed. |
| Local Compose | `docker compose config` succeeds | Passed. Docker emitted a local client-config permission warning. |
| OCI Compose | Placeholder validation succeeds | Passed using tracked placeholder env files and no real credentials. |
| Shell syntax | OCI scripts pass `sh -n` | Passed in a read-only Alpine Linux container. |
| Migration graph | One Alembic head and fresh upgrade succeeds | Passed: one head (`20260723_0900`); idempotent upgrade passed on the existing local database; a fresh isolated `habitflow_audit` PostgreSQL database upgraded through every revision and reported the same head. |
| Health endpoints | Liveness and readiness succeed | Passed locally: live returned API status; ready returned API and database status. |
| Production frontend image | Static artifact has no development API URL or placeholders | Passed: `frontend/Dockerfile.prod` built with `/api/v1`; image scan found no localhost API URL or secret placeholder. |
| Dependency audit | No unreviewed production advisories | Failed: two high-severity build dependency advisories; tracked as PR-014. |
| Backup checksum | Final dump checksum validates | Passed locally: a custom-format PostgreSQL dump opened with `pg_restore --list`, was renamed, checksummed, and validated with `sha256sum -c`. Full OCI backup retention, off-VM upload, and restore rehearsal remain manual. |
| CI YAML syntax | Workflow parses successfully | Passed with the local YAML parser. |
| Text encoding | Modified files contain no mojibake signatures | Passed. |
| Diff integrity | `git diff --check` passes | Passed. |

## Required Follow-Up Issues

1. Define and implement auth abuse protection before public exposure.
2. Run an isolated restore rehearsal from a verified off-VM backup.
3. Configure final-domain HSTS, unknown-host rejection, and host validation.
4. Validate and adopt a non-root backend runtime user if deployment tests pass.
5. Configure uptime, certificate, disk, backup-age, database, and 5xx alerts.
6. Establish dependency advisory handling and image/action pinning policy.
7. Establish refresh-token retention and cleanup policy.

## Deferred Work

The following are intentionally outside Sprint 3.0: high availability,
managed PostgreSQL, point-in-time recovery, Terraform, a managed secret store,
centralized logs, strict CSP, correlation IDs, automatic remote smoke CI, and
large-export streaming.

## Release Gate

Do not create a public production tag until PR-001 through PR-003, PR-006
through PR-008, and PR-014 have evidence of completion or a formally accepted
release exception. PR-004, PR-005, PR-009, and the README portion of PR-010
are addressed by this sprint.
