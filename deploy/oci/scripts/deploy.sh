#!/bin/sh
set -eu

. "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/common.sh"

require_command docker
require_var BACKEND_ENV_FILE
require_var POSTGRES_ENV_FILE
require_var POSTGRES_DATA_DIR
require_var BACKUP_DIR
require_var CERTBOT_CONF_DIR
require_var CERTBOT_WWW_DIR
require_var NGINX_LOG_DIR
require_var POSTGRES_DB
require_var POSTGRES_USER

[ -f "$BACKEND_ENV_FILE" ] || fail "Backend environment file not found: $BACKEND_ENV_FILE"
[ -f "$POSTGRES_ENV_FILE" ] || fail "PostgreSQL environment file not found: $POSTGRES_ENV_FILE"

for directory in "$POSTGRES_DATA_DIR" "$BACKUP_DIR" "$CERTBOT_CONF_DIR" "$CERTBOT_WWW_DIR" "$NGINX_LOG_DIR"; do
  require_safe_habitflow_dir "$directory"
  mkdir -p "$directory"
done

# The official PostgreSQL image runs as UID/GID 999. A bind-mounted host
# directory must be writable by that user before the first database startup.
docker run --rm --user 0:0 --entrypoint /bin/sh \
  -v "$POSTGRES_DATA_DIR:/var/lib/postgresql/data" \
  postgres:17-alpine \
  -c 'chown -R 999:999 /var/lib/postgresql/data'

database_exists=false
if [ -f "$POSTGRES_DATA_DIR/PG_VERSION" ]; then
  database_exists=true
fi

compose build backend web
compose up -d postgres

attempt=1
while [ "$attempt" -le 30 ]; do
  if compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done

if ! compose exec -T postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
  compose logs --no-color postgres
  fail "PostgreSQL did not become ready"
fi

if [ "$database_exists" = true ]; then
  "$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)/backup-postgres.sh"
fi

compose run --rm backend sh /app/migrate.sh
compose up -d backend web

attempt=1
while [ "$attempt" -le 30 ]; do
  if compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=2)" >/dev/null 2>&1; then
    break
  fi
  attempt=$((attempt + 1))
  sleep 2
done

if ! compose exec -T backend python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health/ready', timeout=2)" >/dev/null 2>&1; then
  compose logs --no-color backend postgres web
  fail "Backend did not become ready"
fi

compose exec -T web nginx -s reload
echo "Deployment completed successfully."
