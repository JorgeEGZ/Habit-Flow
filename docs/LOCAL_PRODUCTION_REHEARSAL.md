# Local Production Rehearsal

This runbook validates the OCI deployment path locally with an isolated Docker
project. It is preparation evidence only. It does not prove OCI, DNS, public
TLS, Object Storage, firewall, branch-protection, or remote-smoke controls.

## Prerequisites

- Linux or WSL with a working Docker Engine and Docker Compose plugin.
- `curl`, `openssl`, `python3`, and `sha256sum` available in the POSIX shell.
- Docker host ports 80 and 443 available for the duration of the rehearsal.
- Enough local disk space to build both production images and hold two
  disposable PostgreSQL data directories.

Do not run this from a shell connected to a production Docker daemon. The
script creates and removes only a project named `habitflow-rehearsal-*` and a
temporary directory named `habitflow-rehearsal.*` below `TMPDIR` or `/tmp`.

## Run

From the repository root:

```sh
sh deploy/oci/tests/local-production-rehearsal.sh
```

The script creates temporary `oci.env`, `backend.env`, and `postgres.env`
files with mode `600`. It generates a self-signed certificate for the reserved
local-only name `rehearsal.invalid`; it does not contact a certificate
authority.

The expected final output includes:

```text
Local production rehearsal passed.
Backup duration: ... seconds.
Restore duration: ... seconds.
```

Capture only the result, durations, revision, and operator initials in the
release record. Do not retain generated environment files, credentials, login
responses, cookies, tokens, or synthetic user identifiers.

## What It Verifies

- OCI Compose accepts generated external environment files.
- Backend and production frontend images build locally.
- The web image validates its initial HTTP challenge configuration and the
  composed stack validates its HTTPS configuration.
- PostgreSQL starts before one explicit `alembic upgrade head` command.
- Backend startup uses `MIGRATE_ON_START=false`.
- Nginx serves the SPA, preserves deep links, proxies `/api/`, and exposes the
  health endpoint through HTTPS.
- The service-worker and manifest cache headers are not immutable.
- Only the web service publishes host ports.
- A generated user, habit, savings goal, account, category, and transaction
  are created through the API.
- A real custom-format `pg_dump`, final-name checksum, `pg_restore --list`,
  isolated restore, Alembic head check, non-sensitive table-count comparison,
  login, and representative read-only API checks pass.
- The existing OCI Nginx rate-limit smoke and required off-VM backup mock pass.

## Cleanup And Failure Handling

Cleanup runs on success, failure, and interruption. It removes only the
validated temporary project, the two named restore containers, and the
validated temporary directory. If a cleanup guard refuses a path, investigate
instead of deleting anything manually.

For a failed stack startup, retain only redacted service logs long enough to
diagnose the issue, then rerun with a new temporary project. Never point the
rehearsal at the normal local Compose database or an OCI host.

## Troubleshooting

- If port 80 or 443 is occupied, stop the conflicting local service or run the
  rehearsal on a disposable Linux host. Do not alter the production Compose
  port mapping for this rehearsal.
- If Docker cannot bind a WSL path, run from the Linux filesystem rather than
  a mounted Windows path.
- If image builds cannot pull base images, restore registry access and rerun;
  do not replace pinned images with unreviewed alternatives.
- If ARM64 validation is available, separately run a Buildx build for
  `linux/arm64`. A successful native x86 build does not prove OCI ARM runtime
  compatibility.

## Evidence Boundary

Record a successful rehearsal as local preparation in
`PRODUCTION_READINESS.md`. Keep PR-001, PR-002, and PR-003 open until a final
OCI deployment supplies the required remote backup, restore, domain, TLS,
cookie, firewall, rate-limit, remote-smoke, and branch-protection evidence.
