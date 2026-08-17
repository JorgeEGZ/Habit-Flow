# HabitFlow Production Readiness Report

**Audit date:** 2026-08-16
**Audited source revision:** `76f99cd` before Sprint 3.1 changes
**Scope:** repository configuration, deployment artifacts, CI, automated tests,
and documentation. No production infrastructure, secrets, DNS records, cloud
objects, or customer data were accessed.

## Executive Decision

**Status: NO-GO for a public production release.**

Sprint 3.1 implements and automatically verifies OCI Nginx authentication
limits and required off-VM backup enforcement. It does not prove that a final
OCI target is deployed, that an Object Storage backup exists, that a restore
has succeeded, or that GitHub branch protection is active. Those evidence
items remain P0 release blockers. P1 items from Sprint 3.0 also require
resolution or explicit risk acceptance before a final public GO decision.

## Assumptions And Topology

- The OCI topology is one ARM64 VM with Nginx as the only public service,
  FastAPI and PostgreSQL on internal Docker networks, and persistent paths
  under `/srv/habitflow`.
- The preferred browser topology is a same-site custom domain with
  `REFRESH_COOKIE_SECURE=true` and `REFRESH_COOKIE_SAMESITE=lax`.
- OCI Nginx controls apply only where that configuration is deployed.
  Transitional Render must remain read-only or use equivalent edge controls
  before public exposure.
- Source inspection and local automation cannot prove final DNS, TLS, cloud
  firewall, private bucket configuration, restore success, monitoring, or
  GitHub repository settings.

## Existing Controls

| Area | Repository control | Status |
| --- | --- | --- |
| Runtime configuration | Non-development settings reject placeholder and short secrets; credentialed CORS requires explicit origins; insecure refresh-cookie combinations are rejected. | Automatically verified |
| Authentication | Access tokens are memory-only; refresh tokens are host-only HttpOnly cookies; login, refresh, and logout require allowed Origin and CSRF checks. | Existing control |
| Auth abuse control | OCI Nginx limits login to 5/minute burst 5, register to 1/minute burst 2, and refresh to 30/minute burst 20 per direct client IP. OPTIONS is excluded. | Implemented and smoke-tested; deployment pending |
| Health | `/health/live` avoids PostgreSQL; `/health/ready` returns 503 when PostgreSQL is unavailable. | Automatically verified |
| Database | Alembic has one linear head; OCI deployment runs one explicit migration before app startup. | Automatically verified |
| Backups | The OCI script validates final-name checksums and custom dumps; required off-VM mode uploads and heads both dump and checksum with instance-principal authentication. | Implemented and mock-tested; real evidence pending |
| OCI network | Only Nginx publishes 80/443; PostgreSQL is internal to the data network; backend uses readiness health checks. | Configuration verified; external scan pending |
| PWA | Service worker bypasses `/api/` and uses a static offline page rather than cached user data. | Existing test coverage |
| Exports | CSV/XLSX responses use `private, no-store`, user-scoped queries, deterministic filenames, and formula-like cell sanitization. | Existing test coverage |
| CI | `backend`, `frontend`, `e2e`, and `pwa` are the required branch-protection checks. A supplementary deployment smoke job validates OCI artifacts. | Workflow verified; GitHub settings pending |

## Finding Matrix

| ID | Severity | Evidence | Impact | Remediation | Blocking status | Verification | Owner / status |
| --- | --- | --- | --- | --- | --- | --- | --- |
| PR-001 | P0 | No evidence records a final domain, TLS certificate, production cookie attributes, CORS/CSRF behavior, firewall scan, or GitHub branch-protection settings. | A correct repository can still be deployed insecurely. | Complete the final-domain and branch-protection sections of `PRODUCTION_LAUNCH_EVIDENCE.md`. | Blocking: pending manual evidence | Manual evidence | Release owner / open |
| PR-002 | P0 | OCI Nginx previously had no authentication abuse protection. | Login, registration, and refresh could be brute-forced. | OCI edge limits are implemented and tested. Deploy them, verify Nginx configuration and 429 behavior on the final domain. | Blocking until final-target evidence | Automated smoke plus manual target evidence | Terra / implemented, pending verification |
| PR-003 | P0 | Off-VM backup upload was optional and no restore rehearsal evidence existed. | VM, volume, or operator failures could cause unrecoverable data loss. | Required mode now fails closed; configure a private OCI bucket, run a real remote backup, and complete an isolated restore rehearsal. | Blocking: pending manual evidence | Mock smoke plus real Object Storage and restore evidence | Release owner / implemented controls, pending verification |
| PR-004 | P1 | CI E2E once waited for legacy `/api/v1/health`. | E2E could start before dependencies were ready. | CI now waits for `/api/v1/health/ready`. | Addressed | CI E2E | Terra / fixed |
| PR-005 | P1 | Backup checksum previously referenced a temporary dump name. | Later checksum validation could fail. | The final dump filename is now checksummed and verified. | Addressed | Backup smoke | Terra / fixed |
| PR-006 | P1 | OCI backend container runs as root. | A container compromise has a larger local blast radius. | Validate a non-root backend image across local Compose, Render, OCI, migrations, and bind mounts. | Deferred to Sprint 3.2 | Build and deployment test | Sol / open |
| PR-007 | P1 | Nginx lacks HSTS and explicit unknown-host handling; backend lacks TrustedHost middleware. | HTTPS downgrade and Host-header hardening are incomplete. | Add after final domains and HTTPS behavior are verified. | Deferred to Sprint 3.2 | External TLS and host-header test | Sol / open |
| PR-008 | P1 | No verified alerts for readiness, disk, certificate expiry, backup age, database health, or 5xx errors. | Failures may be detected too late. | Configure and test external monitors and alert thresholds. | Deferred to Sprint 3.2 | Manual alert test | Release owner / open |
| PR-014 | P1 | `npm audit --omit=dev` reported high advisories for transitive `postcss` and `nanoid`. | Build-time supply-chain risk remains. | Apply a separately approved dependency security patch or accept the risk formally. | Deferred to Sprint 3.2 / risk decision | Audit and CI build | Sol / open |

## Sprint 3.1 Automated Evidence

| Check | Result |
| --- | --- |
| OCI Nginx rate-limit syntax and smoke | Passed locally with fresh Nginx zones: each configured burst reached a mock upstream, the first excess returned 429, OPTIONS was excluded, and an unrelated API route remained unthrottled. |
| Required off-VM backup enforcement mock | Passed locally: custom dump/checksum upload and remote head verification were simulated through instance-principal OCI calls; missing namespace failed closed. |
| OCI Compose placeholder configuration | Passed using only tracked example environment files. |
| OCI POSIX shell syntax | Passed for deployment and smoke scripts through WSL. |
| Complete backend suite | Passed: 246 tests. One non-fatal Windows pytest-cache permission warning. |
| Frontend build | Passed. |
| Local E2E and PWA E2E | Passed: 12 local Chromium tests and 3 PWA Chromium tests. |
| Diff integrity, mojibake, and secret scan | Passed: `git diff --check`, targeted encoding scan, and tracked deployment/source secret-identifier scan found no issues. |

## Required Manual Evidence

1. A private OCI Object Storage backup containing both a dump and checksum,
   created through the intended instance principal and within the 24-hour RPO.
2. An isolated restore from that remote backup meeting the 4-hour RTO, with
   checksum, dump listing, Alembic head, non-sensitive count, login, and
   read-only smoke evidence.
3. Final DNS, TLS, HTTPS health, cookie, CORS, CSRF, SPA/PWA, and external
   port-scan evidence.
4. GitHub branch-protection evidence requiring `backend`, `frontend`, `e2e`,
   and `pwa` before `main` merges.
5. A Sprint 3.2 disposition for PR-006 through PR-008 and PR-014, or formal
   acceptance by the release decision authority.

## Release Gate

Do not create a public production tag while PR-001 through PR-003 lack manual
evidence. P0 controls can be described as implemented only after automation
passes; they are not operationally cleared until the corresponding final-target
evidence is recorded. A final GO also requires P1 resolution or explicit risk
acceptance.
