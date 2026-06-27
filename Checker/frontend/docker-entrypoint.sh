#!/bin/sh
# Load runtime configuration exclusively from the mounted .env file.
set -e

ENV_FILE="${ENV_FILE_PATH:-/app/.env}"

if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  . "$ENV_FILE"
  set +a
else
  echo "ERROR: .env file not found at $ENV_FILE" >&2
  exit 1
fi

exec "$@"
