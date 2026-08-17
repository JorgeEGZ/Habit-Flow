#!/bin/sh
set -eu

. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/common.sh"

require_command docker
require_command sha256sum
require_var BACKUP_DIR
require_var POSTGRES_DB
require_var POSTGRES_USER
require_var BACKUP_RETENTION_DAYS
require_safe_habitflow_dir "$BACKUP_DIR"

case "$BACKUP_RETENTION_DAYS" in
  ''|*[!0-9]*) fail "BACKUP_RETENTION_DAYS must be a non-negative integer" ;;
esac
case "${OFFSITE_BACKUP_REQUIRED:-false}" in
  true|false) ;;
  *) fail "OFFSITE_BACKUP_REQUIRED must be true or false" ;;
esac

mkdir -p "$BACKUP_DIR"
umask 077

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_name="habitflow-$timestamp.dump"
temporary_backup="$BACKUP_DIR/$backup_name.tmp"
backup_file="$BACKUP_DIR/$backup_name"
checksum_file="$backup_file.sha256"

echo "Creating PostgreSQL backup: $backup_name"
compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$temporary_backup"
compose exec -T postgres pg_restore --list "/backups/$backup_name.tmp" >/dev/null
mv "$temporary_backup" "$backup_file"

# Generate and validate the checksum after the final filename exists. This
# keeps the checksum portable for later verification from BACKUP_DIR.
(
  cd "$BACKUP_DIR"
  sha256sum "$backup_name" > "$backup_name.sha256"
  sha256sum -c "$backup_name.sha256"
)

find "$BACKUP_DIR" -maxdepth 1 -type f -name 'habitflow-*.dump' -mtime "+$BACKUP_RETENTION_DAYS" -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'habitflow-*.dump.sha256' -mtime "+$BACKUP_RETENTION_DAYS" -delete

offsite_requested=false
if [ "${OFFSITE_BACKUP_REQUIRED:-false}" = true ] \
  || [ -n "${OCI_OBJECT_STORAGE_NAMESPACE:-}" ] \
  || [ -n "${OCI_OBJECT_STORAGE_BUCKET:-}" ]; then
  offsite_requested=true
fi

if [ "$offsite_requested" = true ]; then
  require_var OCI_OBJECT_STORAGE_NAMESPACE
  require_var OCI_OBJECT_STORAGE_BUCKET
  require_command oci
  echo "Uploading verified backup to OCI Object Storage with instance-principal authentication."
  oci --auth instance_principal os object put \
    --namespace "$OCI_OBJECT_STORAGE_NAMESPACE" \
    --bucket-name "$OCI_OBJECT_STORAGE_BUCKET" \
    --name "$backup_name" \
    --file "$backup_file" \
    --force
  oci --auth instance_principal os object put \
    --namespace "$OCI_OBJECT_STORAGE_NAMESPACE" \
    --bucket-name "$OCI_OBJECT_STORAGE_BUCKET" \
    --name "$backup_name.sha256" \
    --file "$checksum_file" \
    --force
  oci --auth instance_principal os object head \
    --namespace "$OCI_OBJECT_STORAGE_NAMESPACE" \
    --bucket-name "$OCI_OBJECT_STORAGE_BUCKET" \
    --name "$backup_name" >/dev/null
  oci --auth instance_principal os object head \
    --namespace "$OCI_OBJECT_STORAGE_NAMESPACE" \
    --bucket-name "$OCI_OBJECT_STORAGE_BUCKET" \
    --name "$backup_name.sha256" >/dev/null
  echo "Verified remote dump and checksum objects."
fi

echo "Backup completed: $backup_file"
