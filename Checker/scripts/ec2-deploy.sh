#!/usr/bin/env bash
# EC2 deployment: fetch .env from S3, then build and start all services.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Fetching .env from S3"
bash "$SCRIPT_DIR/fetch-env-from-s3.sh"

if [ ! -f .env ]; then
  echo "ERROR: .env file missing after S3 fetch." >&2
  exit 1
fi

echo "==> Loading configuration from .env"
set -a
# shellcheck disable=SC1091
source .env
set +a

COMPOSE_FILES=(-f docker-compose.yml)
if [ -f docker-compose.prod.yml ]; then
  COMPOSE_FILES+=(-f docker-compose.prod.yml)
fi

echo "==> Building images"
docker compose "${COMPOSE_FILES[@]}" build \
  --build-arg "API_INTERNAL_URL=${API_INTERNAL_URL:-http://backend:8000}" \
  --build-arg "NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://localhost:8000}"

echo "==> Starting services"
docker compose "${COMPOSE_FILES[@]}" up -d

echo "==> Deployment complete"
docker compose "${COMPOSE_FILES[@]}" ps
