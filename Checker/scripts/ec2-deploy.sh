#!/usr/bin/env bash
# EC2 deploy: backend + Next.js frontend + nginx (SQLite, 3 containers).
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

PUBLIC_HOST="${PUBLIC_HOST:-}"
sed -i '/^DB_ENGINE=/d; /^SQLITE_PATH=/d; /^REDIS_HOST=/d; /^OTEL_ENABLED=/d; /^CORS_ORIGINS=/d; /^PUBLIC_HOST=/d; /^FRONTEND_URL=/d; /^API_INTERNAL_URL=/d; /^NEXT_PUBLIC_API_URL=/d' .env 2>/dev/null || true
{
  echo "DB_ENGINE=sqlite"
  echo "SQLITE_PATH=/app/data/app.db"
  echo "REDIS_HOST=disabled"
  echo "OTEL_ENABLED=false"
  echo "API_INTERNAL_URL=http://backend:8000"
} >> .env

if [ -n "$PUBLIC_HOST" ]; then
  {
    echo "PUBLIC_HOST=$PUBLIC_HOST"
    echo "FRONTEND_URL=http://$PUBLIC_HOST"
    echo "NEXT_PUBLIC_API_URL=http://$PUBLIC_HOST"
    echo "CORS_ORIGINS=http://$PUBLIC_HOST,http://$PUBLIC_HOST:80,http://localhost:3000"
  } >> .env
fi

echo "==> Building backend + frontend + nginx"
docker compose -f docker-compose.ec2.yml build
docker compose -f docker-compose.ec2.yml up -d --no-build

df -h /
docker compose -f docker-compose.ec2.yml ps
curl -fsS http://127.0.0.1/health && echo " — health OK" || docker compose -f docker-compose.ec2.yml logs --tail=60
