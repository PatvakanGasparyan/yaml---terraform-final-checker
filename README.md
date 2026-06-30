# YAML & Terraform AI Validator

Enterprise-grade SaaS platform for validating, analyzing, securing, explaining, fixing, and managing YAML and Terraform configurations.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.12+-green)
![FastAPI](https://img.shields.io/badge/FastAPI-API-green)
![License](https://img.shields.io/badge/license-MIT-blue)

## Project Overview

YAML & Terraform AI Validator is a modern cloud-native web platform designed for DevOps teams and enterprises. It provides comprehensive validation, security scanning, AI-powered code explanation, and GitHub integration for infrastructure-as-code workflows.

## Features

- **YAML Validation** — Syntax, schema, Kubernetes, Helm, Docker Compose, GitHub Actions, GitLab CI
- **Terraform Validation** — validate, fmt, plan analysis, provider checks, dependency graphs, cost estimation
- **Security Scanning** — Checkov, tfsec, Trivy, Semgrep integration with severity classification
- **AI Analysis** — Line-by-line explanations, risk analysis, auto-generated fixes (OpenAI, Azure, Ollama)
- **GitHub Integration** — OAuth, webhooks, PR/commit validation, automatic scans
- **Enterprise Features** — RBAC, teams, MFA, API keys, audit logs, SSO-ready
- **Multi-language API** — English, Russian, Armenian (i18n-ready backend)

## API

> Open **Swagger UI** at `http://localhost:8000/docs` after starting the server.

## Architecture

```
                         ┌─────────────┐
                         │   FastAPI   │
                         │   Backend   │
                         └──────┬──────┘
                                │
                         ┌──────┴──────┐
                         ▼             ▼
                    ┌──────┐     ┌──────────┐
                    │ MySQL│     │  Redis   │
                    └──────┘     └────┬─────┘
                                      │
                               ┌──────┴──────┐
                               │Celery Worker│
                               └─────────────┘
```

Optional: `docker compose --profile proxy up -d` adds nginx on port 80.

See [docs/architecture.md](docs/architecture.md) for detailed diagrams.

## Quick Start

### Prerequisites

- Docker & Docker Compose v2+
- 4GB RAM minimum (8GB recommended for Docker builds)
- EC2 minimal: **8 GB disk** | Full stack: **16 GB disk**
- Ports: **8000** (API), 3307, 6379 (full stack only)

### Docker Setup

```bash
cd Checker
copy .env.example .env    # Windows
# cp .env.example .env    # Linux/Mac

docker compose build
docker compose up -d
```

**EC2 minimal (recommended for small servers):** 1 container, SQLite, **8 GB disk OK**

```bash
cd Checker
docker compose -f docker-compose.ec2.yml up -d --build
```

API at `http://YOUR_IP/docs` (port 80 mapped to 8000).

Uses **SQLite** (no MySQL) and **no Redis/Celery**.

**Full stack (local dev / large server):**

```bash
cd Checker
docker compose up -d --build
```

3 containers: mysql + redis + backend.

### Production Deployment

```bash
docker compose -f docker-compose.prod.yml up -d
```

The application will be available at:
- **Website (EC2)**: `http://YOUR_EC2_IP/` (port **80**)
- **API docs**: `http://YOUR_EC2_IP/docs`
- **Health**: `http://YOUR_EC2_IP/health`

### EC2 not working? Checklist

1. **AWS Security Group** — open inbound **TCP 80** (and 22 for SSH)
2. **Use your public IP**, not `localhost` or `0.0.0.0`
3. **GitHub secret `EC2_HOST`** = your public IP (e.g. `51.21.100.50`)
4. On server run:
   ```bash
   cd ~/yaml-validator/Checker
   sudo docker compose -f docker-compose.ec2.yml ps
   sudo docker compose -f docker-compose.ec2.yml logs backend --tail=50
   curl http://127.0.0.1/health
   ```
5. Free disk if build failed: `sudo docker system prune -af`

## Environment Variables

Copy `.env.example` to `.env` and configure:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing key | (change in production) |
| `MYSQL_PASSWORD` | Database password | `validator_secret` |
| `OPENAI_API_KEY` | OpenAI API key for AI analysis | (optional) |
| `GITHUB_CLIENT_ID` | GitHub OAuth client ID | (optional) |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth secret | (optional) |

## MySQL Setup

MySQL 8.0 is automatically configured via Docker Compose. The database `yaml_terraform_validator` is created on first startup with user `validator`.

Manual connection:
```bash
mysql -h localhost -P 3306 -u validator -p yaml_terraform_validator
```

## GitHub Setup

1. Create a GitHub OAuth App at https://github.com/settings/developers
2. Set callback URL to `http://0.0.0.0:3000/api/auth/github/callback`
3. Add `GITHUB_CLIENT_ID` and `GITHUB_CLIENT_SECRET` to `.env`
4. Configure webhook URL: `http://your-domain/api/v1/github/webhook`

## OpenAI Setup

For AI-powered analysis, configure one of:

```env
# OpenAI
AI_PROVIDER=openai
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o-mini

# Azure OpenAI
AI_PROVIDER=azure
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_DEPLOYMENT=gpt-4o

# Ollama (local)
AI_PROVIDER=ollama
OLLAMA_BASE_URL=http://ollama:11434
OLLAMA_MODEL=llama3.2
```

Without AI configuration, the platform uses a rule-based fallback engine.

## API Documentation

- **Swagger UI**: http://0.0.0.0:8000/docs
- **ReDoc**: http://0.0.0.0:8000/redoc
- **OpenAPI JSON**: http://0.0.0.0:8000/openapi.json

See [docs/api-reference.md](docs/api-reference.md) for complete API reference.

### Quick API Example

```bash
# Register
curl -X POST http://0.0.0.0:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"user","password":"securepass123"}'

# Login
curl -X POST http://0.0.0.0:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"securepass123"}'

# Validate YAML
curl -X POST http://0.0.0.0:8000/api/v1/validations/run \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"content":"apiVersion: v1\nkind: Pod","file_path":"pod.yaml"}'
```

## Development

```bash
# Development mode with hot reload
docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d

# Run backend tests
cd backend && pip install -r requirements-dev.txt && pytest tests/ -v

# Run linting
cd backend && black app/ && ruff check app/
```

## GitHub CI/CD

Workflow: `.github/workflows/ci-cd.yml`

- **test** — ruff + pytest on every push/PR
- **deploy** — SSH to EC2, build 1 Python container, health check `/health` + `/docs`

Required secrets: `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`, `IAM_ACCESS_KEY`, `IAM_SECRET_KEY`

## Troubleshooting

| Issue | Solution |
|-------|----------|
| MySQL connection refused | Wait for health check: `docker compose ps` |
| Backend 500 on startup | Check logs: `docker compose logs backend` |
| AI analysis not working | Verify `OPENAI_API_KEY` or use Ollama fallback |
| GitHub OAuth fails | Check callback URL matches GitHub app settings |

## FAQ

**Q: Can I run without Docker?**
A: Yes. Install Python 3.12+, MySQL 8 (optional), Redis (optional). Run `uvicorn app.main:app --reload` from `Checker/backend`.

**Q: Is AI analysis required?**
A: No. The platform includes a rule-based fallback that works without any AI provider.

**Q: What file types are supported?**
A: `.yaml`, `.yml`, `.tf`, `.tfvars`, `.hcl`, `.json`

## Documentation

- [Architecture](docs/architecture.md)
- [System Design](docs/system-design.md)
- [Deployment Guide](docs/deployment-guide.md)
- [Security Guide](docs/security-guide.md)
- [API Reference](docs/api-reference.md)

## Contribution Guide

1. Fork the repository
2. Create a feature branch
3. Run tests: `cd backend && pytest`
4. Run linting: `black app/ && ruff check app/`
5. Submit a pull request

## License

MIT License — see LICENSE file for details.
