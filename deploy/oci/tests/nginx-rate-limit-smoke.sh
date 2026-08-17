#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
REPO_ROOT=$(CDPATH= cd -- "$SCRIPT_DIR/../../.." && pwd)
NGINX_DIR="$REPO_ROOT/deploy/oci/nginx"
TEMP_DIR=$(mktemp -d)
NETWORK="habitflow-rate-limit-$$"
UPSTREAM="habitflow-rate-upstream-$$"
CLIENT="habitflow-rate-client-$$"

cleanup() {
  docker rm -f "$CLIENT" >/dev/null 2>&1 || true
  docker rm -f "$UPSTREAM" >/dev/null 2>&1 || true
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
  rm -rf "$TEMP_DIR"
}
trap cleanup EXIT INT TERM

require_command() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Required command not found: $1" >&2
    exit 1
  }
}

require_command docker

grep -Fq 'location = /api/v1/auth/login {' "$NGINX_DIR/conf.d/habitflow.conf.template"
grep -Fq 'limit_req zone=auth_login burst=5 nodelay;' "$NGINX_DIR/conf.d/habitflow.conf.template"
grep -Fq 'location = /api/v1/auth/register {' "$NGINX_DIR/conf.d/habitflow.conf.template"
grep -Fq 'limit_req zone=auth_register burst=2 nodelay;' "$NGINX_DIR/conf.d/habitflow.conf.template"
grep -Fq 'location = /api/v1/auth/refresh {' "$NGINX_DIR/conf.d/habitflow.conf.template"
grep -Fq 'limit_req zone=auth_refresh burst=20 nodelay;' "$NGINX_DIR/conf.d/habitflow.conf.template"

mkdir -p "$TEMP_DIR/conf.d" "$TEMP_DIR/includes"
cp "$NGINX_DIR/nginx.conf" "$TEMP_DIR/nginx.conf"
cp "$NGINX_DIR/conf.d/includes/api-proxy.conf" "$TEMP_DIR/includes/api-proxy.conf"

cat > "$TEMP_DIR/conf.d/rate-limit.conf" <<'EOF'
server {
    listen 8080;
    server_name _;

    location = /api/v1/auth/login {
        limit_req zone=auth_login burst=5 nodelay;
        include /etc/nginx/habitflow-includes/api-proxy.conf;
    }

    location = /api/v1/auth/register {
        limit_req zone=auth_register burst=2 nodelay;
        include /etc/nginx/habitflow-includes/api-proxy.conf;
    }

    location = /api/v1/auth/refresh {
        limit_req zone=auth_refresh burst=20 nodelay;
        include /etc/nginx/habitflow-includes/api-proxy.conf;
    }

    location /api/ {
        include /etc/nginx/habitflow-includes/api-proxy.conf;
    }
}
EOF

cat > "$TEMP_DIR/upstream.conf" <<'EOF'
events {}
http {
    server {
        listen 8000;
        location / {
            return 204;
        }
    }
}
EOF

docker network create "$NETWORK" >/dev/null
docker run -d --rm --name "$UPSTREAM" --network "$NETWORK" --network-alias backend \
  -v "$TEMP_DIR/upstream.conf:/etc/nginx/nginx.conf:ro" \
  nginx:1.27-alpine >/dev/null
docker run -d --rm --name "$CLIENT" --network "$NETWORK" --entrypoint sh \
  curlimages/curl:8.12.1 -c 'while :; do sleep 3600; done' >/dev/null

status() {
  method=$1
  path=$2
  docker exec "$CLIENT" curl \
    -sS -o /dev/null -w '%{http_code}' -X "$method" "http://edge:8080$path"
}

assert_status() {
  expected=$1
  method=$2
  path=$3
  actual=$(status "$method" "$path")
  [ "$actual" = "$expected" ] || {
    echo "Expected $method $path to return $expected, got $actual." >&2
    exit 1
  }
}

request_sequence() {
  method=$1
  path=$2
  request_count=$3
  docker exec "$CLIENT" sh -c '
    attempt=1
    while [ "$attempt" -le "$1" ]; do
      curl -sS -o /dev/null -w "%{http_code} " -X "$2" "http://edge:8080$3"
      attempt=$((attempt + 1))
    done
  ' sh "$request_count" "$method" "$path"
}

assert_sequence() {
  expected_status=$1
  method=$2
  path=$3
  request_count=$4
  responses=$(request_sequence "$method" "$path" "$request_count")

  for response in $responses; do
    [ "$response" = "$expected_status" ] || {
      echo "Expected every $method $path response to be $expected_status, got $responses." >&2
      exit 1
    }
  done
}

run_case() {
  path=$1
  accepted_requests=$2
  edge="habitflow-rate-edge-$$"

  # A fresh Nginx process gives every endpoint case a fresh shared-memory zone.
  docker run -d --rm --name "$edge" --network "$NETWORK" --network-alias edge \
    -v "$TEMP_DIR/nginx.conf:/etc/nginx/nginx.conf:ro" \
    -v "$TEMP_DIR/conf.d:/etc/nginx/conf.d:ro" \
    -v "$TEMP_DIR/includes:/etc/nginx/habitflow-includes:ro" \
    nginx:1.27-alpine >/dev/null

  docker exec "$edge" nginx -t >/dev/null

  assert_sequence 204 OPTIONS "$path" 4
  assert_sequence 204 POST "$path" "$accepted_requests"
  assert_sequence 429 POST "$path" 1

  # This request runs after the auth limit has been exhausted, proving that
  # generic API routes do not share an authentication quota.
  assert_status 204 GET /api/v1/health/ready
  docker rm -f "$edge" >/dev/null
}

# Nginx accepts the initial request plus the configured nodelay burst.
run_case /api/v1/auth/login 6
run_case /api/v1/auth/register 3
run_case /api/v1/auth/refresh 21

echo "OCI Nginx authentication rate-limit smoke passed."
