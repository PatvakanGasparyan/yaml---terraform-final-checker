#!/bin/sh
set -e

mkdir -p /app/data
chown -R appuser:appuser /app/data 2>/dev/null || true

if [ ! -s "${ENV_FILE_PATH:-/app/.env}" ]; then
  echo "ERROR: .env file missing or empty at ${ENV_FILE_PATH:-/app/.env}" >&2
  echo "Deploy must mount Checker/.env or download it from S3 before starting the container." >&2
  exit 1
fi

gosu appuser python -m app.core.env_loader || exit 1
exec gosu appuser "$@"
