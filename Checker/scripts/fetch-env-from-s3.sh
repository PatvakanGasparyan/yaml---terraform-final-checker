#!/usr/bin/env bash
# Download .env from S3 before docker compose starts.
# Requires bootstrap.env (or instance env) with ENV_S3_BUCKET and ENV_S3_KEY.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

if [ -f bootstrap.env ]; then
  set -a
  # shellcheck disable=SC1091
  source bootstrap.env
  set +a
fi

if [ -z "${ENV_S3_BUCKET:-}" ]; then
  echo "ENV_S3_BUCKET is not set. Skipping S3 download (using local .env if present)."
  exit 0
fi

ENV_FILE_PATH="${ENV_FILE_PATH:-$PROJECT_ROOT/.env}"
export ENV_FILE_PATH

echo "Fetching .env from s3://${ENV_S3_BUCKET}/${ENV_S3_KEY:-.env}"

if command -v aws >/dev/null 2>&1; then
  aws s3 cp "s3://${ENV_S3_BUCKET}/${ENV_S3_KEY:-.env}" "$ENV_FILE_PATH"
elif [ -d backend/app ]; then
  python -m app.core.env_loader
else
  echo "ERROR: aws CLI not found and backend module unavailable." >&2
  exit 1
fi

chmod 600 "$ENV_FILE_PATH"
echo "Saved .env to $ENV_FILE_PATH"
