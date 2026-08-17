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

The OCI Nginx edge limits only `POST /api/v1/auth/login`,
`POST /api/v1/auth/register`, and `POST /api/v1/auth/refresh` by the directly
connected client IP. Its initial limits are 5/minute with burst 5, 1/minute
with burst 2, and 30/minute with burst 20. `OPTIONS` requests do not consume
quota. This is an OCI-edge control only: keep transitional Render deployments
read-only or configure equivalent edge protection before making them public.

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
- `OFFSITE_BACKUP_REQUIRED=true`, an OCI Object Storage namespace, and a
  private Object Storage bucket. These are mandatory for a public launch.

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
`pg_restore --list`, and retains seven days locally by default:

```sh
HABITFLOW_OCI_ENV_FILE=/etc/habitflow/oci.env sh deploy/oci/scripts/backup-postgres.sh
```

Schedule this daily and run it before every production migration. With
`OFFSITE_BACKUP_REQUIRED=true`, the command fails when the namespace, bucket,
OCI CLI, instance-principal upload, or remote object verification fails. It
uploads both the dump and its checksum, then verifies that both objects exist.
The script uses `oci --auth instance_principal`; do not store OCI credentials
in environment files.

Create a private bucket with no public access, least-privilege instance
principal policy limited to this backup bucket, encryption-at-rest verified in
OCI, and at least 30 days of off-VM retention. Verify current OCI Free Tier
Object Storage eligibility and capacity in the OCI console. A manual encrypted
download is emergency/bootstrap recovery only, not the ongoing production
backup control. Configure backup-age monitoring outside the application.

No automated restore is included. The proposed launch objectives are RPO 24
hours and RTO 4 hours. Rehearse recovery from an actual remote object in an
isolated, non-production PostgreSQL target: download the dump and checksum,
run `sha256sum -c`, run `pg_restore --list`, restore it, verify `alembic
current` equals `alembic heads`, compare non-sensitive table counts, and run
login plus representative read-only module smoke. Record backup age and total
restore duration in `docs/PRODUCTION_LAUNCH_EVIDENCE.md`; remove the isolated
copy only after a reviewer approves the evidence. A backup not restored this
way is not verified recovery evidence.

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
