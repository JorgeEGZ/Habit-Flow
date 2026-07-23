# HabitFlow On OCI Free Tier

This directory deploys HabitFlow on one Oracle Cloud Infrastructure (OCI)
Always Free Ampere VM. It is intentionally separate from the local
`docker-compose.yml` file.

```text
Internet (80/443)
        |
      Nginx web container
        |                 \
  Vue static SPA           FastAPI backend
                                  |
                            PostgreSQL 17
```

Only Nginx publishes ports. The API and database remain on internal Docker
networks. The production frontend is built by `frontend/Dockerfile.prod` and
uses `/api/v1`, so Nginx keeps the frontend and API on the same HTTPS origin.

## Target And Prerequisites

Use an Always Free eligible `VM.Standard.A1.Flex` instance with **2 OCPU and
8 GB RAM**, running Ubuntu 24.04 Minimal ARM64. Always Free eligibility and
Ampere capacity are account and region dependent; verify both in the OCI
console before creating resources.

Before deployment, prepare:

- A reserved public IPv4 address attached to the VM.
- A domain with an `A` record pointing to that address.
- An OCI Network Security Group (NSG) allowing public TCP `80` and `443`.
- UFW rules allowing public `80` and `443`, and allowing SSH `22` only from
  the developer's fixed IP address or VPN range.
- No public NSG/UFW rule for `5432`, `8000`, or `5173`.
- Docker Engine and the Docker Compose plugin installed on the VM.
- A mounted block volume at `/srv/habitflow` when possible. Root-volume use is
  acceptable only for an initial, low-risk deployment with verified backups.

Do not use plain HTTP or an IP-only URL for production. Secure cookie-based
authentication requires HTTPS and a stable domain.

## VM Setup

Install Docker using Docker's current Ubuntu instructions, then allow the
deploy user to use it without an interactive root shell. Reconnect after group
membership changes.

Create persistent directories. The deployment script also ensures PostgreSQL
ownership through a one-shot container, but creating the hierarchy first makes
the mount layout explicit:

```sh
sudo install -d -m 700 -o 999 -g 999 /srv/habitflow/postgres-data
sudo install -d -m 700 /srv/habitflow/backups
sudo install -d -m 755 /srv/habitflow/certbot/conf
sudo install -d -m 755 /srv/habitflow/certbot/www
sudo install -d -m 755 /srv/habitflow/nginx-logs
sudo install -d -m 700 /etc/habitflow
```

Clone this repository to a non-secret deployment directory, for example
`/opt/habitflow`. Do not store credentials in the repository checkout.

## Environment Files

Copy these examples to external files and set restrictive permissions:

```sh
sudo cp deploy/oci/.env.example /etc/habitflow/oci.env
sudo cp deploy/oci/backend.env.example /etc/habitflow/backend.env
sudo cp deploy/oci/postgres.env.example /etc/habitflow/postgres.env
sudo chown root:root /etc/habitflow/*.env
sudo chmod 600 /etc/habitflow/*.env
```

Set the following in `/etc/habitflow/oci.env`:

- `DOMAIN` and `LETSENCRYPT_EMAIL`.
- Persistent paths under `/srv/habitflow`.
- `BACKEND_ENV_FILE` and `POSTGRES_ENV_FILE` pointing to the two external
  files above.
- Optional OCI Object Storage namespace and bucket only when backup upload is
  configured.

Set `DATABASE_URL` in the backend file using the Docker hostname:

```text
postgresql+asyncpg://USER:PASSWORD@postgres:5432/DATABASE
```

The backend file must use `ENVIRONMENT=production`, `DEBUG=false`,
`REFRESH_COOKIE_SECURE=true`, `REFRESH_COOKIE_SAMESITE=lax`,
`MIGRATE_ON_START=false`, and an explicit JSON `CORS_ORIGINS` list containing
only `https://DOMAIN`. Generate a stable high-entropy `SECRET_KEY`; rotating it
invalidates existing signed access tokens.

The PostgreSQL file must use non-development `POSTGRES_DB`, `POSTGRES_USER`,
and `POSTGRES_PASSWORD` values. Keep its values consistent with the backend
`DATABASE_URL`.

Same-site deployment through this Nginx origin is preferred. If frontend and
API are later split across truly cross-site domains, update CORS and use
`REFRESH_COOKIE_SAMESITE=none` while keeping `REFRESH_COOKIE_SECURE=true`.

## Initial HTTPS Certificate

Export the external Compose environment file path in every deployment shell:

```sh
export HABITFLOW_OCI_ENV_FILE=/etc/habitflow/oci.env
```

Confirm DNS resolves to the VM and ports `80` and `443` are reachable. Then
issue the first certificate:

```sh
cd /opt/habitflow
sh deploy/oci/scripts/init-certbot.sh
```

The script starts Nginx with an HTTP-only configuration, uses the webroot
challenge, then recreates Nginx with the HTTPS configuration. It refuses to
replace an existing certificate. For an issuance rehearsal, set
`CERTBOT_STAGING=true`; set it back to `false` before requesting the live
certificate.

Renew certificates with a cron job running as the deploy user:

```cron
17 3 * * * cd /opt/habitflow && HABITFLOW_OCI_ENV_FILE=/etc/habitflow/oci.env sh deploy/oci/scripts/renew-certbot.sh >> /var/log/habitflow-certbot.log 2>&1
```

The renewal script is safe to run daily and reloads Nginx only after Certbot
finishes. A systemd timer is an equivalent alternative.

## Deploy And Migrate

Run an initial deployment or a repeatable application release with:

```sh
cd /opt/habitflow
HABITFLOW_OCI_ENV_FILE=/etc/habitflow/oci.env sh deploy/oci/scripts/deploy.sh
```

The script validates inputs, builds the API and static frontend images, starts
PostgreSQL, waits for `pg_isready`, creates a verified backup when an existing
database is present, and runs exactly one migration command:

```sh
docker compose -f deploy/oci/compose.yml run --rm backend sh /app/migrate.sh
```

It then starts FastAPI and Nginx and waits for `/api/v1/health/ready` inside
the backend container. Production API startup has `MIGRATE_ON_START=false`, so
only this serialized release step applies migrations.

Nginx serves the Vue SPA with a fallback to `index.html`, proxies `/api/`
without stripping that path, and serves ACME challenges. It adds compression,
cache controls for versioned static assets, and baseline browser security
headers. It deliberately does not enable a strict CSP until it is tested
against the application and PrimeVue.

## Backups And Restore Rehearsal

`backup-postgres.sh` creates a custom-format `pg_dump` under
`/srv/habitflow/backups`, writes a SHA-256 checksum, validates the dump with
`pg_restore --list`, and retains seven days by default:

```sh
HABITFLOW_OCI_ENV_FILE=/etc/habitflow/oci.env sh deploy/oci/scripts/backup-postgres.sh
```

Schedule this daily. The script deletes only matching backup files inside the
validated `BACKUP_DIR`. It can upload verified dumps when both
`OCI_OBJECT_STORAGE_NAMESPACE` and `OCI_OBJECT_STORAGE_BUCKET` are set and
the OCI CLI is available. Prefer OCI instance-principal authorization over
credentials stored on the VM.

No automated restore is included. Rehearse recovery periodically by restoring
one backup into an isolated PostgreSQL instance, checking `alembic current`,
and exercising login plus a representative finance workflow. A backup that has
not been restored is not a verified recovery plan.

## Monitoring, Rollback, And Render Migration

Use these checks after every deployment:

```sh
curl -fsS https://YOUR_DOMAIN/api/v1/health/live
curl -fsS https://YOUR_DOMAIN/api/v1/health/ready
BASE_URL=https://YOUR_DOMAIN E2E_EMAIL=... E2E_PASSWORD=... npm --prefix frontend run test:e2e:remote
```

Watch Docker logs, disk usage, PostgreSQL health, certificate renewal logs,
and OCI instance metrics. Configure an external uptime monitor for the ready
endpoint and alert on low disk space before backups or PostgreSQL data fill the
volume.

For an application rollback, redeploy the previous Git revision and run the
same script only when its code is compatible with the current schema. Alembic
downgrades are not an automatic rollback mechanism. For a database incident,
stop writes, preserve the current data volume, restore a verified backup into
an isolated instance first, and document the recovery decision before cutover.

To migrate from transitional Render deployment:

1. Rehearse a Render PostgreSQL export and OCI import on non-production data.
2. Verify the OCI backend migration head and all health checks.
3. Build the frontend with `VITE_API_URL=/api/v1` and issue the certificate.
4. Put the old deployment in maintenance/read-only mode, take one final backup,
   restore it on OCI, and run the serialized migration step.
5. Execute remote read-only smoke tests against OCI.
6. Switch DNS, monitor closely, and keep Render available read-only until the
   rollback window ends.

Host-only refresh cookies do not migrate across hostnames. Users should expect
to sign in again after DNS/API hostname changes.

## Free Tier Limits And Deferred Work

OCI Ampere capacity can be unavailable in a selected region and Always Free
instances can be reclaimed when idle. One VM is also a single point of failure
for Nginx, API, PostgreSQL, and backups stored locally. Off-VM backup storage,
restore rehearsals, a custom domain, and a basic uptime monitor are minimum
operational controls.

Deferred for this solo-developer deployment: multi-VM high availability,
managed PostgreSQL, automated OCI provisioning, managed secrets, centralized
logging, automated remote smoke CI, and a tested strict Content-Security-
Policy.
