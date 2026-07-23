#!/bin/sh
set -e

echo "Running database migrations..."
exec alembic upgrade head
