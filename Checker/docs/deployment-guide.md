# Deployment Guide

## Docker Compose (Recommended)

### Development

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d
```

### Production

```bash
# Set production secrets
cp .env.example .env
# Edit .env with production values

docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Commands

```bash
docker compose build          # Build all images
docker compose up -d          # Start all services
docker compose down           # Stop all services
docker compose logs -f        # Follow logs
docker compose restart        # Restart all services
docker compose ps             # Check service status
```

## AWS Deployment

### ECS Fargate

1. Push images to ECR
2. Create ECS task definitions for backend, frontend, worker
3. Configure RDS MySQL and ElastiCache Redis
4. Set up ALB with target groups
5. Configure Route 53 DNS

### EKS (Kubernetes)

```bash
kubectl apply -f infrastructure/kubernetes/
helm install ytv infrastructure/helm/ytv-platform/
```

Environment variables for AWS:
```env
MYSQL_HOST=your-rds-endpoint.region.rds.amazonaws.com
REDIS_HOST=your-elasticache-endpoint
```

## Azure Deployment

### Azure Container Apps

1. Push images to Azure Container Registry
2. Deploy container apps for each service
3. Configure Azure Database for MySQL
4. Configure Azure Cache for Redis

### AKS

Use Helm chart with Azure-specific values:
```yaml
mysql:
  host: your-mysql.mysql.database.azure.com
redis:
  host: your-redis.redis.cache.windows.net
```

## Google Cloud Deployment

### Cloud Run + Cloud SQL

1. Build and push to Artifact Registry
2. Deploy Cloud Run services
3. Connect to Cloud SQL MySQL via proxy
4. Use Memorystore for Redis

## DigitalOcean

### App Platform

Deploy using `infrastructure/digitalocean/app.yaml`:
- Managed MySQL database
- Managed Redis
- Container components for backend/frontend/worker

## Hetzner

### Docker on VPS

```bash
# On Hetzner Cloud VPS (Ubuntu 22.04)
apt update && apt install -y docker.io docker-compose-v2
git clone <repo-url>
cd yaml-terraform-validator
docker compose up -d
```

Configure firewall:
```bash
ufw allow 80/tcp
ufw allow 443/tcp
ufw enable
```

## Kubernetes (Generic)

```bash
# Create namespace
kubectl create namespace ytv-platform

# Apply manifests
kubectl apply -f infrastructure/kubernetes/ -n ytv-platform

# Or use Helm
helm install ytv infrastructure/helm/ytv-platform/ \
  --namespace ytv-platform \
  --set mysql.host=mysql-service \
  --set redis.host=redis-service
```

## SSL/TLS

For production, configure SSL in nginx:

1. Obtain certificates (Let's Encrypt recommended)
2. Place in `docker/nginx/ssl/`
3. Use `docker/nginx/nginx.prod.conf`
4. Run with production compose file

## Database Migrations

```bash
# Run Alembic migrations
docker compose exec backend alembic upgrade head

# Create new migration
docker compose exec backend alembic revision --autogenerate -m "description"
```

## Monitoring Setup

After deployment, access:
- Grafana: http://your-domain:3001 (configure dashboards)
- Prometheus: http://your-domain:9090
- API Metrics: http://your-domain/metrics

## Health Checks

```bash
curl http://localhost:8000/health
# {"status":"healthy","version":"1.0.0","database":"healthy","redis":"healthy"}
```

## Rollback Procedure

```bash
# Stop current deployment
docker compose down

# Restore database if needed
./scripts/restore.sh /backups/backup_YYYYMMDD_HHMMSS.sql

# Deploy previous version
git checkout <previous-tag>
docker compose up -d
```
