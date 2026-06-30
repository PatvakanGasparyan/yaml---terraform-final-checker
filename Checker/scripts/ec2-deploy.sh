#!/usr/bin/env bash
# EC2 ultra-minimal deploy: SQLite + 2 containers only.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo "==> Disk before cleanup"
df -h /

docker compose -f docker-compose.ec2.yml down --remove-orphans 2>/dev/null || true
docker builder prune -af 2>/dev/null || true
docker image prune -af 2>/dev/null || true

echo "==> Fetching .env from S3"
bash "$SCRIPT_DIR/fetch-env-from-s3.sh"

grep -q '^DB_ENGINE=' .env 2>/dev/null || echo "DB_ENGINE=sqlite" >> .env
grep -q '^SQLITE_PATH=' .env 2>/dev/null || echo "SQLITE_PATH=/app/data/app.db" >> .env
grep -q '^REDIS_HOST=' .env 2>/dev/null || echo "REDIS_HOST=disabled" >> .env

echo "==> Building backend + frontend"
docker compose -f docker-compose.ec2.yml build backend frontend
docker compose -f docker-compose.ec2.yml up -d --no-build

df -h /
docker compose -f docker-compose.ec2.yml ps
