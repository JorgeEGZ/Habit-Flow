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

## Sign-Off

| Field | Evidence |
| --- | --- |
| Remaining P0 findings | `PENDING` |
| Remaining P1 risk acceptance or Sprint 3.2 plan | `PENDING` |
| Release decision | `PENDING` |
| Decision authority | `PENDING` |
