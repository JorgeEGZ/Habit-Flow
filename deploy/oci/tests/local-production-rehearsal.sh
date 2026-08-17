#!/bin/sh
set -eu

# This rehearsal intentionally uses a disposable Compose project and generated
# data. It validates the production path locally; it never constitutes OCI,
# DNS, TLS, or Object Storage evidence.

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OCI_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$OCI_DIR/../.." && pwd)
COMPOSE_FILE="$OCI_DIR/compose.yml"
DOMAIN="rehearsal.invalid"
# Docker Compose project names must be lowercase. Keep this identifier safe
# for both Compose resources and generated synthetic data.
RUN_ID="$(date -u +%Y%m%dt%H%M%sz)-$$"
PROJECT_NAME="habitflow-rehearsal-$RUN_ID"
TEMP_ROOT=${TMPDIR:-/tmp}
RUN_DIR=$(mktemp -d "$TEMP_ROOT/habitflow-rehearsal.XXXXXX")
COMPOSE_ENV="$RUN_DIR/oci.env"
BACKEND_ENV="$RUN_DIR/backend.env"
RESTORE_BACKEND_ENV="$RUN_DIR/restore-backend.env"
POSTGRES_ENV="$RUN_DIR/postgres.env"
POSTGRES_DATA_DIR="$RUN_DIR/postgres-data"
RESTORE_DATA_DIR="$RUN_DIR/restore-data"
BACKUP_DIR="$RUN_DIR/backups"
CERTBOT_CONF_DIR="$RUN_DIR/certbot-conf"
CERTBOT_WWW_DIR="$RUN_DIR/certbot-www"
NGINX_LOG_DIR="$RUN_DIR/nginx-logs"
RESTORE_DB_CONTAINER="$PROJECT_NAME-restore-postgres"
RESTORE_API_CONTAINER="$PROJECT_NAME-restore-backend"
COMPOSE_STARTED=false

fail() {
  echo "Error: $*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

compose() {
  docker compose \
    --project-name "$PROJECT_NAME" \
    --env-file "$COMPOSE_ENV" \
    -f "$COMPOSE_FILE" \
    "$@"
}

cleanup() {
  status=$?
  trap - EXIT INT TERM

  docker rm -f "$RESTORE_API_CONTAINER" >/dev/null 2>&1 || true
  docker rm -f "$RESTORE_DB_CONTAINER" >/dev/null 2>&1 || true

  if [ "$COMPOSE_STARTED" = true ]; then
    compose down -v --remove-orphans >/dev/null 2>&1 || true
  fi

  case "$RUN_DIR" in
    "$TEMP_ROOT"/habitflow-rehearsal.*)
      # PostgreSQL writes as UID 999. Clear only this validated bind mount as
      # root in a disposable container so the invoking user can remove it.
      docker run --rm --user 0:0 -v "$RUN_DIR:/rehearsal" postgres:17-alpine \
        sh -c 'find /rehearsal -mindepth 1 -maxdepth 1 -exec rm -rf {} +' \
        >/dev/null 2>&1 || true
      rm -rf "$RUN_DIR"
      ;;
    *)
      echo "Refusing to remove an unexpected rehearsal directory: $RUN_DIR" >&2
      status=1
      ;;
  esac

  exit "$status"
}

trap cleanup EXIT INT TERM

for command in docker openssl curl python3 sha256sum; do
  require_command "$command"
done

docker compose version >/dev/null 2>&1 || fail "Docker Compose plugin is required"

umask 077
mkdir -p \
  "$POSTGRES_DATA_DIR" \
  "$RESTORE_DATA_DIR" \
  "$BACKUP_DIR" \
  "$CERTBOT_CONF_DIR/live/$DOMAIN" \
  "$CERTBOT_WWW_DIR" \
  "$NGINX_LOG_DIR"

secret_key=$(openssl rand -hex 48)
postgres_password=$(openssl rand -hex 32)
database_name=habitflow_rehearsal
database_user=habitflow_rehearsal

cat > "$POSTGRES_ENV" <<EOF
POSTGRES_DB=$database_name
POSTGRES_USER=$database_user
POSTGRES_PASSWORD=$postgres_password
EOF

cat > "$BACKEND_ENV" <<EOF
DATABASE_URL=postgresql+asyncpg://$database_user:$postgres_password@postgres:5432/$database_name
SECRET_KEY=$secret_key
ENVIRONMENT=production
DEBUG=false
APP_TIMEZONE=America/Bogota
CORS_ORIGINS=["https://$DOMAIN"]
REFRESH_COOKIE_SECURE=true
REFRESH_COOKIE_SAMESITE=lax
REFRESH_COOKIE_PATH=/api/v1/auth
CSRF_HEADER_NAME=X-CSRF-Protection
CSRF_HEADER_VALUE=1
MIGRATE_ON_START=false
PORT=8000
EOF

cat > "$RESTORE_BACKEND_ENV" <<EOF
DATABASE_URL=postgresql+asyncpg://$database_user:$postgres_password@restore-postgres:5432/$database_name
SECRET_KEY=$secret_key
ENVIRONMENT=production
DEBUG=false
APP_TIMEZONE=America/Bogota
CORS_ORIGINS=["https://$DOMAIN"]
REFRESH_COOKIE_SECURE=true
REFRESH_COOKIE_SAMESITE=lax
REFRESH_COOKIE_PATH=/api/v1/auth
CSRF_HEADER_NAME=X-CSRF-Protection
CSRF_HEADER_VALUE=1
MIGRATE_ON_START=false
PORT=8000
EOF

cat > "$COMPOSE_ENV" <<EOF
DOMAIN=$DOMAIN
VITE_API_URL=/api/v1
POSTGRES_DATA_DIR=$POSTGRES_DATA_DIR
BACKUP_DIR=$BACKUP_DIR
CERTBOT_CONF_DIR=$CERTBOT_CONF_DIR
CERTBOT_WWW_DIR=$CERTBOT_WWW_DIR
NGINX_LOG_DIR=$NGINX_LOG_DIR
BACKEND_ENV_FILE=$BACKEND_ENV
POSTGRES_ENV_FILE=$POSTGRES_ENV
POSTGRES_DB=$database_name
POSTGRES_USER=$database_user
BACKUP_RETENTION_DAYS=0
OFFSITE_BACKUP_REQUIRED=false
EOF

openssl req -x509 -nodes -newkey rsa:2048 \
  -keyout "$CERTBOT_CONF_DIR/live/$DOMAIN/privkey.pem" \
  -out "$CERTBOT_CONF_DIR/live/$DOMAIN/fullchain.pem" \
  -subj "/CN=$DOMAIN" \
  -days 1 >/dev/null 2>&1

chmod 600 "$COMPOSE_ENV" "$BACKEND_ENV" "$RESTORE_BACKEND_ENV" "$POSTGRES_ENV"

echo "Validating OCI Compose configuration for $PROJECT_NAME"
compose config --quiet

echo "Building production backend and frontend images"
compose build backend web

# The image starts in HTTP challenge mode when no certificate volume is mounted.
docker run --rm -e DOMAIN="$DOMAIN" habitflow-web:oci nginx -t >/dev/null

echo "Starting isolated PostgreSQL"
COMPOSE_STARTED=true
compose up -d postgres

attempt=1
while [ "$attempt" -le 30 ]; do
  if compose exec -T postgres pg_isready -U "$database_user" -d "$database_name" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done
compose exec -T postgres pg_isready -U "$database_user" -d "$database_name" >/dev/null 2>&1 \
  || fail "Isolated PostgreSQL did not become ready"

echo "Running one serialized Alembic migration"
compose run --rm backend sh /app/migrate.sh

echo "Starting production backend and Nginx"
compose up -d backend web

https_url="https://$DOMAIN"
curl_https() {
  curl -k --resolve "$DOMAIN:443:127.0.0.1" "$@"
}

attempt=1
while [ "$attempt" -le 30 ]; do
  if curl_https --fail --silent --show-error "$https_url/api/v1/health/ready" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done
curl_https --fail --silent --show-error "$https_url/api/v1/health/ready" >/dev/null \
  || fail "Nginx could not reach the ready backend"

compose exec -T web nginx -t >/dev/null

http_headers="$RUN_DIR/http.headers"
curl --silent --show-error --resolve "$DOMAIN:80:127.0.0.1" \
  -D "$http_headers" -o /dev/null "http://$DOMAIN/"
grep -Eqi '^HTTP/[0-9.]+ 301' "$http_headers" || fail "HTTP did not redirect"
grep -Eqi "^location: https://$DOMAIN/?" "$http_headers" || fail "HTTP redirect target is incorrect"

curl_https --fail --silent --show-error "$https_url/" > "$RUN_DIR/index.html"
grep -Fq '<div id="app">' "$RUN_DIR/index.html" || fail "Frontend root was not served"
curl_https --fail --silent --show-error "$https_url/finances/reports" > "$RUN_DIR/deep-link.html"
grep -Fq '<div id="app">' "$RUN_DIR/deep-link.html" || fail "SPA deep link was not served"

sw_headers="$RUN_DIR/sw.headers"
curl_https --fail --silent --show-error -D "$sw_headers" -o /dev/null "$https_url/sw.js"
grep -Eqi '^cache-control: .*no-cache.*no-store.*must-revalidate' "$sw_headers" \
  || fail "Service worker cache policy is incorrect"
grep -Eqi '^service-worker-allowed: /' "$sw_headers" \
  || fail "Service worker scope header is missing"
curl_https --fail --silent --show-error -D "$RUN_DIR/manifest.headers" -o /dev/null "$https_url/manifest.webmanifest"
grep -Eqi '^cache-control: .*no-cache' "$RUN_DIR/manifest.headers" \
  || fail "Manifest cache policy is incorrect"

web_ports=$(docker inspect "$(compose ps -q web)" --format '{{json .NetworkSettings.Ports}}')
backend_ports=$(docker inspect "$(compose ps -q backend)" --format '{{json .NetworkSettings.Ports}}')
postgres_ports=$(docker inspect "$(compose ps -q postgres)" --format '{{json .NetworkSettings.Ports}}')
printf '%s' "$web_ports" | grep -q 'HostPort' || fail "Nginx does not publish a public port"
printf '%s' "$backend_ports" | grep -q 'HostPort' && fail "Backend published a host port"
printf '%s' "$postgres_ports" | grep -q 'HostPort' && fail "PostgreSQL published a host port"

today=$(compose exec -T backend python -c 'from app.core.exports import current_app_date; print(current_app_date().isoformat())')
month=$(printf '%s' "$today" | cut -c1-7)
# The address is synthetic and is never printed or persisted. Use the RFC
# example domain because the API validates deliverable-looking email syntax.
test_email_domain=$(printf '%s' 'example' '.' 'com')
test_email="rehearsal-$RUN_ID@$test_email_domain"
test_password=$(openssl rand -hex 24)
register_body="$RUN_DIR/register.json"
login_body="$RUN_DIR/login.json"
login_headers="$RUN_DIR/login.headers"

echo "Creating generated application data"
curl_https --fail --silent --show-error \
  -X POST "$https_url/api/v1/auth/register" \
  -H 'Content-Type: application/json' \
  --data "{\"email\":\"$test_email\",\"password\":\"$test_password\",\"full_name\":\"Rehearsal user\"}" \
  > "$register_body"
curl_https --fail --silent --show-error \
  -X POST "$https_url/api/v1/auth/login" \
  -H "Origin: $https_url" \
  -H 'X-CSRF-Protection: 1' \
  -H 'Content-Type: application/json' \
  -D "$login_headers" \
  --data "{\"email\":\"$test_email\",\"password\":\"$test_password\"}" \
  > "$login_body"

cookie_line=$(tr -d '\r' < "$login_headers" | grep -i '^set-cookie:' || true)
printf '%s' "$cookie_line" | grep -qi 'httponly' || fail "Refresh cookie is not HttpOnly"
printf '%s' "$cookie_line" | grep -qi 'secure' || fail "Refresh cookie is not Secure"
printf '%s' "$cookie_line" | grep -qi 'samesite=lax' || fail "Refresh cookie SameSite is incorrect"
printf '%s' "$cookie_line" | grep -qi 'path=/api/v1/auth' || fail "Refresh cookie Path is incorrect"
printf '%s' "$cookie_line" | grep -qi 'domain=' && fail "Refresh cookie unexpectedly has Domain"

access_token=$(python3 -c 'import json, sys; print(json.load(sys.stdin)["access_token"])' < "$login_body")
auth_header="Authorization: Bearer $access_token"

curl_https --fail --silent --show-error \
  -X POST "$https_url/api/v1/habits" \
  -H "$auth_header" -H 'Content-Type: application/json' \
  --data '{"title":"Rehearsal habit","tracking_mode":"boolean","frequency":"daily"}' \
  > "$RUN_DIR/habit.json"
curl_https --fail --silent --show-error \
  -X POST "$https_url/api/v1/savings/goals" \
  -H "$auth_header" -H 'Content-Type: application/json' \
  --data '{"name":"Rehearsal goal","target_amount":50000}' \
  > "$RUN_DIR/goal.json"
curl_https --fail --silent --show-error \
  -X POST "$https_url/api/v1/finances/accounts" \
  -H "$auth_header" -H 'Content-Type: application/json' \
  --data '{"name":"Rehearsal account","type":"checking","initial_balance":0}' \
  > "$RUN_DIR/account.json"
curl_https --fail --silent --show-error \
  -X POST "$https_url/api/v1/finances/categories" \
  -H "$auth_header" -H 'Content-Type: application/json' \
  --data '{"name":"Rehearsal category","type":"expense"}' \
  > "$RUN_DIR/category.json"

account_id=$(python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])' < "$RUN_DIR/account.json")
category_id=$(python3 -c 'import json, sys; print(json.load(sys.stdin)["id"])' < "$RUN_DIR/category.json")
curl_https --fail --silent --show-error \
  -X POST "$https_url/api/v1/finances/transactions" \
  -H "$auth_header" -H 'Content-Type: application/json' \
  --data "{\"account_id\":\"$account_id\",\"category_id\":\"$category_id\",\"type\":\"expense\",\"amount\":10000,\"description\":\"Rehearsal movement\",\"transaction_date\":\"$today\"}" \
  > "$RUN_DIR/transaction.json"

for path in /api/v1/habits /api/v1/savings/goals /api/v1/finances/accounts /api/v1/finances/transactions; do
  curl_https --fail --silent --show-error -H "$auth_header" "$https_url$path" >/dev/null
done

backup_started=$(date +%s)
backup_name="habitflow-rehearsal-$RUN_ID.dump"
temporary_dump="$BACKUP_DIR/$backup_name.tmp"
backup_file="$BACKUP_DIR/$backup_name"
checksum_file="$backup_file.sha256"
compose exec -T postgres pg_dump -U "$database_user" -d "$database_name" -Fc > "$temporary_dump"
mv "$temporary_dump" "$backup_file"
(
  cd "$BACKUP_DIR"
  sha256sum "$backup_name" > "$backup_name.sha256"
  sha256sum -c "$backup_name.sha256" >/dev/null
)
docker run --rm -v "$BACKUP_DIR:/backup:ro" postgres:17-alpine \
  pg_restore --list "/backup/$backup_name" >/dev/null
backup_finished=$(date +%s)

source_container=$(compose ps -q postgres)
restore_network=$(docker inspect "$source_container" --format '{{range $name, $_ := .NetworkSettings.Networks}}{{printf "%s\n" $name}}{{end}}' | grep 'data_internal$' | head -n 1)
[ -n "$restore_network" ] || fail "Could not locate the isolated data network"

docker run -d --name "$RESTORE_DB_CONTAINER" \
  --network "$restore_network" \
  --network-alias restore-postgres \
  -e "POSTGRES_DB=$database_name" \
  -e "POSTGRES_USER=$database_user" \
  -e "POSTGRES_PASSWORD=$postgres_password" \
  -v "$RESTORE_DATA_DIR:/var/lib/postgresql/data" \
  -v "$BACKUP_DIR:/restore:ro" \
  postgres:17-alpine >/dev/null

attempt=1
while [ "$attempt" -le 30 ]; do
  if docker exec "$RESTORE_DB_CONTAINER" pg_isready -U "$database_user" -d "$database_name" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done
docker exec "$RESTORE_DB_CONTAINER" pg_isready -U "$database_user" -d "$database_name" >/dev/null 2>&1 \
  || fail "Restore PostgreSQL did not become ready"

restore_started=$(date +%s)
docker exec "$RESTORE_DB_CONTAINER" pg_restore \
  -U "$database_user" -d "$database_name" --clean --if-exists --exit-on-error \
  "/restore/$backup_name" >/dev/null

table_names=$(compose exec -T postgres psql -U "$database_user" -d "$database_name" -At \
  -c "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
source_counts=$(
  for table_name in $table_names; do
    count=$(compose exec -T postgres psql -U "$database_user" -d "$database_name" -At \
      -c "SELECT count(*) FROM \"$table_name\"")
    printf '%s:%s\n' "$table_name" "$count"
  done
)
restore_counts=$(
  for table_name in $table_names; do
    count=$(docker exec "$RESTORE_DB_CONTAINER" psql -U "$database_user" -d "$database_name" -At \
      -c "SELECT count(*) FROM \"$table_name\"")
    printf '%s:%s\n' "$table_name" "$count"
  done
)
[ "$source_counts" = "$restore_counts" ] || fail "Source and restore table counts differ"

restore_head=$(docker run --rm --network "$restore_network" --env-file "$RESTORE_BACKEND_ENV" \
  habitflow-backend:oci sh -c 'alembic heads' | awk 'NR == 1 { print $1 }')
restore_current=$(docker run --rm --network "$restore_network" --env-file "$RESTORE_BACKEND_ENV" \
  habitflow-backend:oci sh -c 'alembic current' | awk 'NR == 1 { print $1 }')
[ -n "$restore_head" ] && [ "$restore_head" = "$restore_current" ] \
  || fail "Restored Alembic current does not match heads"

docker run -d --name "$RESTORE_API_CONTAINER" \
  --network "$restore_network" \
  --network-alias restore-backend \
  --env-file "$RESTORE_BACKEND_ENV" \
  habitflow-backend:oci >/dev/null

attempt=1
while [ "$attempt" -le 30 ]; do
  if docker exec "$RESTORE_API_CONTAINER" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=2)" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done
docker exec "$RESTORE_API_CONTAINER" python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=2)" >/dev/null \
  || fail "Restored backend did not become ready"

restore_login_status=$(docker run --rm --network "$restore_network" curlimages/curl:8.12.1 \
  -sS -o /dev/null -w '%{http_code}' \
  -X POST 'http://restore-backend:8000/api/v1/auth/login' \
  -H "Origin: $https_url" \
  -H 'X-CSRF-Protection: 1' \
  -H 'Content-Type: application/json' \
  --data "{\"email\":\"$test_email\",\"password\":\"$test_password\"}")
[ "$restore_login_status" = 200 ] || fail "Restored login verification failed"

for path in /api/v1/habits /api/v1/savings/goals /api/v1/finances/accounts; do
  read_status=$(docker run --rm --network "$restore_network" curlimages/curl:8.12.1 \
    -sS -o /dev/null -w '%{http_code}' \
    -H "$auth_header" "http://restore-backend:8000$path")
  [ "$read_status" = 200 ] || fail "Restored read-only verification failed for $path"
done
restore_finished=$(date +%s)

echo "Running isolated OCI rate-limit and backup-enforcement smoke tests"
sh "$OCI_DIR/tests/nginx-rate-limit-smoke.sh"
sh "$OCI_DIR/tests/backup-postgres-smoke.sh"

postgres_version=$(docker exec "$RESTORE_DB_CONTAINER" postgres --version | tr -d '\n')
echo "Local production rehearsal passed."
echo "Backup duration: $((backup_finished - backup_started)) seconds."
echo "Restore duration: $((restore_finished - restore_started)) seconds."
echo "Restored PostgreSQL: $postgres_version"
echo "This local rehearsal does not verify OCI Object Storage, final DNS, public TLS, firewall, or remote smoke evidence."
