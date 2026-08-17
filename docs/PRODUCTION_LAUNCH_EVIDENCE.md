# HabitFlow Production Launch Evidence

This template records evidence from a real production target. It is not proof
until the operator fills it with reviewed, redacted command results. Do not add
credentials, cookies, access or refresh tokens, user emails, signed URLs,
database URLs, public IP addresses, object contents, or personal finance data.

## Release Metadata

| Field | Evidence |
| --- | --- |
| Date and time (UTC) | `PENDING` |
| Operator | `PENDING` |
| Reviewer | `PENDING` |
| Source revision | `PENDING` |
| Deployment target | `PENDING` |
| RPO objective | 24 hours |
| RTO objective | 4 hours |

## Sprint 3.1.1 Evidence Collection Attempt

| Field | Evidence |
| --- | --- |
| Attempt date | 2026-08-16 |
| Source revision | `45c65f2cebc9b5b741bec85c10f723ee5aad555d` |
| Repository worktree | Clean at the recorded revision |
| Versioned CI workflow | Declares `backend`, `frontend`, `e2e`, and `pwa` jobs. This is not proof of their remote check-run conclusions. |
| Remote CI check-run lookup | `PENDING`: GitHub Actions was unreachable from this operator environment. |
| OCI CLI and production environment | `PENDING`: no OCI CLI, final domain, remote-smoke credentials, or external OCI environment file was available to this operator. |
| Evidence conclusion | `NO-GO`: no final-target P0 evidence was collected during this attempt. |

The rows below remain operational evidence fields. Replace `PENDING` only with
reviewed, redacted results from the final target. Do not record secret values,
identifiers, raw headers, or personal data.

## Off-VM Backup And Restore Rehearsal

| Field | Evidence |
| --- | --- |
| Private Object Storage policy reviewed | `PENDING` |
| Encryption at rest verified | `PENDING` |
| Remote object name (redacted identifier) | `PENDING` |
| Backup age at rehearsal | `PENDING` |
| SHA-256 verification result | `PENDING` |
| `pg_restore --list` result | `PENDING` |
| PostgreSQL version | `PENDING` |
| Alembic version | `PENDING` |
| `alembic heads` / `alembic current` match | `PENDING` |
| Non-sensitive table-count comparison | `PENDING` |
| Login smoke result | `PENDING` |
| Read-only habits, savings, and finance smoke result | `PENDING` |
| Total restore duration | `PENDING` |
| RPO objective met | `PENDING` |
| RTO objective met | `PENDING` |
| Isolated restored target removed after review | `PENDING` |

## OCI Authentication Rate Limits

| Evidence | Result |
| --- | --- |
| Final Nginx configuration contains the three exact auth locations | `PENDING` |
| Login limit reaches 429 after the configured accepted burst | `PENDING` |
| Register limit reaches 429 after the configured accepted burst | `PENDING` |
| Refresh limit reaches 429 after the configured accepted burst | `PENDING` |
| Repeated OPTIONS requests do not consume an auth quota | `PENDING` |
| Health and unrelated business routes remain unaffected | `PENDING` |
| Redacted warning-level Nginx rate-limit log reference | `PENDING` |

## Final Domain, TLS, Cookies, And Network

| Evidence | Result |
| --- | --- |
| DNS A record resolves to the reserved OCI IP | `PENDING` |
| No unintended AAAA record | `PENDING` |
| HTTP redirects to the exact HTTPS domain | `PENDING` |
| Certificate hostname, chain, and expiry verified | `PENDING` |
| TLS 1.2 and TLS 1.3 verified | `PENDING` |
| HTTPS live and ready endpoints verified | `PENDING` |
| SPA deep link and PWA control over HTTPS verified | `PENDING` |
| Refresh cookie: Secure, HttpOnly, SameSite=Lax, Path=/api/v1/auth | `PENDING` |
| No unintended cookie Domain attribute | `PENDING` |
| Trusted CORS origin with credentials verified | `PENDING` |
| Untrusted Origin rejected | `PENDING` |
| Missing CSRF header rejected | `PENDING` |
| External scan: 80/443 open | `PENDING` |
| External scan: SSH restricted | `PENDING` |
| External scan: 5432/8000/5173 closed | `PENDING` |

## GitHub Branch Protection

| Requirement | Evidence |
| --- | --- |
| Pull requests required for `main` | `PENDING` |
| Branch must be current before merge | `PENDING` |
| Required checks: backend, frontend, e2e, pwa | `PENDING` |
| Conversation resolution required | `PENDING` |
| Force pushes and branch deletion blocked | `PENDING` |
| Emergency bypass restricted and documented | `PENDING` |
| Screenshot or redacted `gh api` output attached to release record | `PENDING` |

## Remote Read-Only Smoke

| Field | Evidence |
| --- | --- |
| Dedicated non-personal account confirmed | `PENDING` |
| Command result: `npm --prefix frontend run test:e2e:remote` | `PENDING` |
| Dashboard, profile, habits, savings, and finance navigation | `PENDING` |
| Raw report or artifact location | `PENDING`: retain privately and record only a redacted reference or digest here. |

## Evidence Review And Redaction

| Field | Evidence |
| --- | --- |
| Raw evidence retained outside the repository | `PENDING` |
| Redacted reference or digest recorded | `PENDING` |
| Reviewer confirmed no secrets, identifiers, personal data, cookies, tokens, or signed URLs | `PENDING` |

## Sign-Off

| Field | Evidence |
| --- | --- |
| Remaining P0 findings | `PENDING` |
| Remaining P1 risk acceptance or Sprint 3.2 plan | `PENDING` |
| Release decision | `PENDING` |
| Decision authority | `PENDING` |
