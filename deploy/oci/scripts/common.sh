#!/bin/sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
OCI_DIR=$(CDPATH= cd -- "$SCRIPT_DIR/.." && pwd)
REPO_ROOT=$(CDPATH= cd -- "$OCI_DIR/../.." && pwd)
COMPOSE_FILE="$OCI_DIR/compose.yml"
ENV_FILE=${HABITFLOW_OCI_ENV_FILE:-"$OCI_DIR/.env"}

fail() {
  echo "Error: $*" >&2
  exit 1
}

if [ ! -f "$ENV_FILE" ]; then
  fail "OCI environment file not found: $ENV_FILE"
fi

# This file is root-owned deployment configuration, not an application env file.
# It must contain shell-compatible KEY=value entries from .env.example.
. "$ENV_FILE"

compose() {
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

require_var() {
  name=$1
  eval "value=\${$name:-}"
  [ -n "$value" ] || fail "$name must be set in $ENV_FILE"
}

require_safe_habitflow_dir() {
  path=$1
  case "$path" in
    /srv/habitflow/*) ;;
    *) fail "Refusing a path outside /srv/habitflow: $path" ;;
  esac
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}
