# YAML & Terraform AI Validator

Enterprise-grade SaaS platform for validating, analyzing, securing, explaining, fixing, and managing YAML and Terraform configurations.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Python](https://img.shields.io/badge/python-3.12+-green)
![Next.js](https://img.shields.io/badge/next.js-15+-black)
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
- **Multi-language UI** — English, Russian, Armenian

## Screenshots

> Dashboard, validation interface, and security findings views are available after running the application at `http://localhost:3000`.

## Architecture

```
┌─────────────┐                    ┌─────────────┐
│   Frontend  │───────────────────▶│   Backend   │
│  Next.js 15 │                    │   FastAPI   │
└─────────────┘                    └──────┬──────┘
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
- 4GB RAM recommended
- Ports: 3000, 8000, 3307, 6379

### Docker Setup

```bash
# Clone and enter project directory
cd yaml-terraform-validator

# Build and start all services
docker compose build
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

### Production Deployment

```bash
docker compose -f docker-compose.prod.yml up -d
```

The application will be available at:
- **Frontend**: http://0.0.0.0:3000
- **API**: http://0.0.0.0:8000
- **API Docs**: http://0.0.0.0:8000/docs

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

# Frontend development
cd frontend && npm install && npm run dev
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| MySQL connection refused | Wait for health check: `docker compose ps` |
| Backend 500 on startup | Check logs: `docker compose logs backend` |
| Frontend build fails | Run `npm install --legacy-peer-deps` in frontend/ |
| AI analysis not working | Verify `OPENAI_API_KEY` or use Ollama fallback |
| GitHub OAuth fails | Check callback URL matches GitHub app settings |

## FAQ

**Q: Can I run without Docker?**
A: Yes. Install Python 3.12+, Node.js 22+, MySQL 8, Redis. Run backend with `uvicorn app.main:app` and frontend with `npm run dev`.

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
