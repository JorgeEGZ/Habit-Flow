#!/bin/sh
set -e

case "${MIGRATE_ON_START:-true}" in
  true)
    sh /app/migrate.sh
    ;;
  false)
    echo "Skipping database migrations..."
    ;;
  *)
    echo "MIGRATE_ON_START must be true or false." >&2
    exit 1
    ;;
esac

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
