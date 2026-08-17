# OCI Provisioning Checklist

This checklist prepares a single-VM HabitFlow deployment. It contains no
production identifiers or credentials. Record redacted evidence outside the
repository and copy only approved status summaries into the launch evidence.

## VM And Storage

- [ ] Confirm current Always Free eligibility and Ampere capacity in the OCI
  console.
- [ ] Create an ARM64 Ubuntu 24.04 Minimal instance sized for the documented
  two OCPU and eight GB target.
- [ ] Attach a reserved public IPv4 address.
- [ ] Create an SSH key and restrict administrative access to the operator
  source range or VPN.
- [ ] Attach and mount persistent storage at `/srv/habitflow` when available.
- [ ] Verify `aarch64`, time synchronization, free disk space, and restart
  behavior.
- [ ] Install Docker Engine and the Docker Compose plugin from their supported
  Ubuntu instructions.
- [ ] Create `/srv/habitflow` data, backup, certificate, webroot, and log
  directories with the ownership described in `deploy/oci/README.md`.

## Network And Firewall

- [ ] Attach an NSG allowing public TCP 80 and 443 only.
- [ ] Restrict TCP 22 to the administrator source range.
- [ ] Configure equivalent UFW rules on the VM.
- [ ] Confirm 5432, 8000, and 5173 are not allowed by either NSG or UFW.
- [ ] Reserve external port-scan evidence for the final launch record.

## Secrets And Environment Files

- [ ] Generate a stable random `SECRET_KEY` with at least 32 bytes.
- [ ] Generate a separate high-entropy PostgreSQL password that is safe for a
  connection URL or encode it correctly.
- [ ] Create `/etc/habitflow/oci.env`, `/etc/habitflow/backend.env`, and
  `/etc/habitflow/postgres.env` from tracked examples.
- [ ] Keep the files outside the checkout, owned by the deployment
  administrator, and mode `600`.
- [ ] Set production backend values: `ENVIRONMENT=production`, `DEBUG=false`,
  `MIGRATE_ON_START=false`, secure refresh cookies, exact HTTPS CORS origins,
  and the Docker-internal `postgres:5432` URL.
- [ ] Set non-development PostgreSQL database, user, and password values.
- [ ] Set `OFFSITE_BACKUP_REQUIRED=true` without adding OCI credential
  variables.
- [ ] Create dedicated remote-smoke credentials outside the repository.

## Object Storage

- [ ] Create a private bucket with public access disabled and encryption at
  rest verified.
- [ ] Configure an instance-principal dynamic group and least-privilege policy
  limited to dump and checksum objects in the intended bucket.
- [ ] Do not create or store OCI API keys on the VM.
- [ ] Configure daily backup execution, seven-day local retention, and
  thirty-day off-VM retention.
- [ ] Verify one dump and checksum upload, remote object metadata, and backup
  age within the 24-hour RPO.
- [ ] Restore one real remote backup to an isolated PostgreSQL target and
  record an RTO of four hours or less.

## Domain, DNS, And TLS

- [ ] Create only the intended A record to the reserved IPv4 address.
- [ ] Do not create an AAAA record unless IPv6 is explicitly configured.
- [ ] Use a low DNS TTL during cutover and verify authoritative resolution.
- [ ] Set the exact frontend HTTPS origin in `CORS_ORIGINS`.
- [ ] Run the Certbot webroot flow only after DNS and public TCP 80 are ready.
- [ ] Verify redirect, certificate hostname, chain, expiry, TLS 1.2, and TLS
  1.3 from an external network.
- [ ] Verify secure refresh-cookie attributes, no cookie Domain attribute,
  trusted CORS, rejected untrusted Origin, and rejected missing CSRF header.
- [ ] Verify SPA deep links and PWA service-worker control over HTTPS.

## GitHub And Launch Controls

- [ ] Require pull requests and current branch before merge to `main`.
- [ ] Require `backend`, `frontend`, `e2e`, and `pwa` checks.
- [ ] Require conversation resolution.
- [ ] Block force pushes and branch deletion.
- [ ] Restrict and document emergency bypass.
- [ ] Keep the supplementary `deployment` job informative; it does not replace
  the four required checks.
- [ ] Run `npm audit` and `npm audit --omit=dev`; record any remaining high
  advisories with owner, mitigation, due date, and explicit risk acceptance.

## First Deployment

- [ ] Run the local production rehearsal from a disposable Docker environment.
- [ ] Run the serialized OCI deploy script with the external environment file.
- [ ] Confirm a required pre-migration backup succeeds before migration.
- [ ] Verify HTTPS live and ready endpoints.
- [ ] Verify final-domain rate limits using invalid synthetic requests.
- [ ] Run dedicated-account remote read-only smoke.
- [ ] Complete `PRODUCTION_LAUNCH_EVIDENCE.md` with reviewed redacted results.

Do not enable HSTS, strict host rejection, rootless backend containers, or new
monitoring controls as part of this provisioning checklist. They require their
own reviewed work after final-domain validation.
