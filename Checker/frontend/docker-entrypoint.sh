#!/bin/sh
# Load runtime configuration exclusively from the mounted .env file.
set -e

ENV_FILE="${ENV_FILE_PATH:-/app/.env}"

if [ -f "$ENV_FILE" ]; then
  tmp_env=$(mktemp)
  tr -d '\r' < "$ENV_FILE" > "$tmp_env"
  set -a
  # shellcheck disable=SC1090
  . "$tmp_env"
  set +a
  rm -f "$tmp_env"
else
  echo "ERROR: .env file not found at $ENV_FILE" >&2
  exit 1
fi

exec "$@"
