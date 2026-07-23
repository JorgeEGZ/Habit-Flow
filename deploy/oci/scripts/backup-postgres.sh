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

mkdir -p "$BACKUP_DIR"
umask 077

timestamp=$(date -u +%Y%m%dT%H%M%SZ)
backup_name="habitflow-$timestamp.dump"
temporary_backup="$BACKUP_DIR/$backup_name.tmp"
backup_file="$BACKUP_DIR/$backup_name"
temporary_checksum="$temporary_backup.sha256"
checksum_file="$backup_file.sha256"

echo "Creating PostgreSQL backup: $backup_name"
compose exec -T postgres pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc > "$temporary_backup"
compose exec -T postgres pg_restore --list "/backups/$backup_name.tmp" >/dev/null
sha256sum "$temporary_backup" > "$temporary_checksum"
mv "$temporary_backup" "$backup_file"
mv "$temporary_checksum" "$checksum_file"

find "$BACKUP_DIR" -maxdepth 1 -type f -name 'habitflow-*.dump' -mtime "+$BACKUP_RETENTION_DAYS" -delete
find "$BACKUP_DIR" -maxdepth 1 -type f -name 'habitflow-*.dump.sha256' -mtime "+$BACKUP_RETENTION_DAYS" -delete

if [ -n "${OCI_OBJECT_STORAGE_NAMESPACE:-}" ] || [ -n "${OCI_OBJECT_STORAGE_BUCKET:-}" ]; then
  require_var OCI_OBJECT_STORAGE_NAMESPACE
  require_var OCI_OBJECT_STORAGE_BUCKET
  require_command oci
  echo "Uploading verified backup to OCI Object Storage."
  oci os object put \
    --namespace "$OCI_OBJECT_STORAGE_NAMESPACE" \
    --bucket-name "$OCI_OBJECT_STORAGE_BUCKET" \
    --name "$backup_name" \
    --file "$backup_file" \
    --force
  oci os object put \
    --namespace "$OCI_OBJECT_STORAGE_NAMESPACE" \
    --bucket-name "$OCI_OBJECT_STORAGE_BUCKET" \
    --name "$backup_name.sha256" \
    --file "$checksum_file" \
    --force
fi

echo "Backup completed: $backup_file"
