#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
TEMP_DIR=$(mktemp -d)
TEST_DIR="$TEMP_DIR/scripts"
TEST_ROOT="$TEMP_DIR/srv/habitflow"
REMOTE_DIR="$TEMP_DIR/object-storage"

cleanup() {
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT INT TERM

mkdir -p "$TEST_DIR" "$TEST_ROOT/backups" "$REMOTE_DIR" "$TEMP_DIR/bin"
cp "$REPO_ROOT/deploy/oci/scripts/backup-postgres.sh" "$TEST_DIR/backup-postgres.sh"
cp "$REPO_ROOT/deploy/oci/scripts/common.sh" "$TEST_DIR/common.sh"
sed -i "s|/srv/habitflow/\\*|$TEST_ROOT/\\*|" "$TEST_DIR/common.sh"

cat > "$TEMP_DIR/bin/docker" <<'EOF'
#!/usr/bin/env sh
case " $* " in
  *" pg_dump "*) printf 'mock custom PostgreSQL dump' ;;
  *) exit 0 ;;
esac
EOF

cat > "$TEMP_DIR/bin/oci" <<'EOF'
#!/usr/bin/env sh
set -eu

name=''
file=''
action=''
for argument in "$@"; do
  case "$argument" in
    put|head) action="$argument" ;;
  esac
done

while [ "$#" -gt 0 ]; do
  case "$1" in
    --name) name=$2; shift 2 ;;
    --file) file=$2; shift 2 ;;
    *) shift ;;
  esac
done

case "$action" in
  put) cp "$file" "$REMOTE_DIR/$name" ;;
  head) test -f "$REMOTE_DIR/$name" ;;
  *) exit 1 ;;
esac
EOF
chmod +x "$TEMP_DIR/bin/docker" "$TEMP_DIR/bin/oci"

cat > "$TEMP_DIR/oci.env" <<EOF
BACKUP_DIR=$TEST_ROOT/backups
POSTGRES_DB=habitflow_test
POSTGRES_USER=habitflow_test
BACKUP_RETENTION_DAYS=7
OFFSITE_BACKUP_REQUIRED=true
OCI_OBJECT_STORAGE_NAMESPACE=test-namespace
OCI_OBJECT_STORAGE_BUCKET=test-private-bucket
EOF

PATH="$TEMP_DIR/bin:$PATH" REMOTE_DIR="$REMOTE_DIR" \
  HABITFLOW_OCI_ENV_FILE="$TEMP_DIR/oci.env" sh "$TEST_DIR/backup-postgres.sh"

dump_count=$(find "$REMOTE_DIR" -maxdepth 1 -type f -name 'habitflow-*.dump' | wc -l | tr -d ' ')
checksum_count=$(find "$REMOTE_DIR" -maxdepth 1 -type f -name 'habitflow-*.dump.sha256' | wc -l | tr -d ' ')
[ "$dump_count" = 1 ]
[ "$checksum_count" = 1 ]

dump_file=$(find "$TEST_ROOT/backups" -maxdepth 1 -type f -name 'habitflow-*.dump' -print -quit)
checksum_file="$dump_file.sha256"
(cd "$TEST_ROOT/backups" && sha256sum -c "$(basename "$checksum_file")" >/dev/null)

cat > "$TEMP_DIR/missing-namespace.env" <<EOF
BACKUP_DIR=$TEST_ROOT/backups
POSTGRES_DB=habitflow_test
POSTGRES_USER=habitflow_test
BACKUP_RETENTION_DAYS=7
OFFSITE_BACKUP_REQUIRED=true
OCI_OBJECT_STORAGE_NAMESPACE=
OCI_OBJECT_STORAGE_BUCKET=test-private-bucket
EOF

if PATH="$TEMP_DIR/bin:$PATH" REMOTE_DIR="$REMOTE_DIR" \
  HABITFLOW_OCI_ENV_FILE="$TEMP_DIR/missing-namespace.env" sh "$TEST_DIR/backup-postgres.sh" >/dev/null 2>&1; then
  echo "Required off-VM backup unexpectedly accepted a missing namespace." >&2
  exit 1
fi

echo "OCI backup enforcement smoke passed."
