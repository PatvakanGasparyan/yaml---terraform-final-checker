# YAML & Terraform AI Validator

[![Version](https://img.shields.io/badge/version-1.0.0-blue.svg)](https://github.com/PatvakanGasparyan/yaml---terraform-final-checker)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?logo=next.js&logoColor=white)](https://nextjs.org/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker&logoColor=white)](https://docs.docker.com/compose/)
[![Tailwind CSS](https://img.shields.io/badge/Tailwind_CSS-3-38B2AC?logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

Enterprise-grade platform for validating, securing, and analyzing **YAML** and **Terraform** infrastructure-as-code. Includes a professional web frontend, REST API, optional AI analysis, and production-ready Docker deployment.

---

## Introduction

**YAML & Terraform AI Validator** (YTV) helps DevOps and platform teams catch misconfigurations before they reach production. Users paste or upload configurations through a clean web UI—or integrate directly via API—and receive structured validation results, security findings, and optional AI-powered explanations.

The platform is modular: run the full stack locally with Docker Compose, deploy a lightweight **EC2 bundle** (frontend + API + nginx), or scale the API tier independently for enterprise integrations.

---

## Features

| Area | Capabilities |
|------|----------------|
| **Validation** | YAML syntax, Kubernetes, Docker Compose, CI/CD manifests; Terraform/HCL analysis |
| **Security** | Policy-style findings with severity levels (critical → informational) |
| **AI analysis** | Optional line-by-line explanations via OpenAI, Azure OpenAI, or Ollama |
| **Web UI** | React/Next.js validator workspace with upload, templates, and results panel |
| **API** | RESTful FastAPI backend with OpenAPI/Swagger documentation |
| **Auth & RBAC** | JWT authentication, roles, MFA (TOTP), guest access for public validation |
| **GitHub** | OAuth, webhooks, repository linking (optional) |
| **Observability** | Health checks, Prometheus metrics, optional OpenTelemetry |

---

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 15, React 19, TypeScript, Tailwind CSS, TanStack Query |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic v2 |
| **Database** | SQLite (EC2 minimal) or MySQL 8 (full stack) |
| **Cache / workers** | Redis + Celery (optional, full stack) |
| **Reverse proxy** | nginx (production EC2 compose) |
| **Containerization** | Docker, Docker Compose v2 |
| **CI/CD** | GitHub Actions (lint, test, build, deploy) |

---

## Architecture

Production EC2 deployment runs **three containers** behind nginx on port **80**:

```
                    ┌─────────────────────────────────────┐
                    │           nginx :80                 │
                    │  /  → frontend   /api/ → backend    │
                    └──────────┬──────────────┬───────────┘
                               │              │
                    ┌──────────▼──┐    ┌──────▼──────┐
                    │  Next.js UI │    │   FastAPI   │
                    │  :3000      │    │   :8000     │
                    └─────────────┘    └──────┬──────┘
                                              │
                                       ┌──────▼──────┐
                                       │   SQLite    │
                                       │  (volume)   │
                                       └─────────────┘
```

**Full local stack** (`docker-compose.yml`): MySQL, Redis, backend, optional Celery worker, optional nginx proxy profile.

Detailed diagrams: [docs/architecture.md](Checker/docs/architecture.md)

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) & Docker Compose v2+
- 4 GB RAM minimum (8 GB recommended for frontend builds)
- Port **80** (EC2 stack) or **8000** (API-only local)

### EC2 / production stack (recommended)

```bash
cd Checker
cp .env.example .env    # Linux/macOS
# copy .env.example .env   # Windows

docker compose -f docker-compose.ec2.yml up -d --build
```

| URL | Description |
|-----|-------------|
| `http://localhost/` | Landing page |
| `http://localhost/validate` | Validator workspace |
| `http://localhost/docs` | Swagger API docs |
| `http://localhost/health` | Health check |

### Full development stack

```bash
cd Checker
docker compose up -d --build
```

API: `http://localhost:8000` · MySQL: `localhost:3307` · Redis: `localhost:6379`

### Backend tests

```bash
cd Checker/backend
pip install -r requirements-dev.txt
pytest tests/ -q
```

---

## Frontend

The web UI is a **Next.js** application in `Checker/frontend/`.

### Key routes

| Route | Purpose |
|-------|---------|
| `/` | Landing page |
| `/validate` | Primary validator (input, **Validate** button, results) |
| `/validations` | Validator + validation history |
| `/yaml-editor` | YAML-focused editor |
| `/dashboard` | Metrics and activity |

### Validation flow

1. User enters YAML or Terraform in the input panel (or uploads a file).
2. Clicks **Validate** → `POST /api/v1/validations/run`.
3. Results panel shows errors, warnings, security findings, and AI analysis tabs.

The browser calls the API via the **same origin** (`/api/v1/...`) through nginx, so CORS is not required in production. For local `next dev` on port 3000, configure `CORS_ORIGINS` in `.env`.

### Local frontend development

```bash
cd Checker/frontend
npm install
npm run dev
```

Set in `.env`:

```env
NEXT_PUBLIC_API_URL=http://localhost:8000
API_INTERNAL_URL=http://localhost:8000
CORS_ORIGINS=http://localhost:3000
```

---

## CLI

Professional command-line interface (`ytv`) for CI/CD pipelines:

```bash
cd Checker/backend
pip install -r requirements.txt

# Validate
ytv validate -f main.tf

# Deep scan with security + AI
ytv scan -f deploy.yaml --ai

# Auto-fix mode (--fix)
ytv fix -f config.yaml -o config.fixed.yaml

# Export SARIF for GitHub Code Scanning
ytv report -f main.tf --format sarif -O report.sarif

# Environment check
ytv doctor
ytv version
```

| Command | Description |
|---------|-------------|
| `validate` | Syntax and policy validation |
| `scan` | Full scan with security + optional AI |
| `fix` | Auto-fix and write corrected file |
| `report` | Export JSON, YAML, Markdown, HTML, SARIF, JUnit |
| `explain` | AI line-by-line explanations |
| `doctor` | Check config and external tools |

---

## Backend architecture (layers)

```
app/
├── core/           # config, database, security, limiter, env_loader
├── ai/             # OpenAI client (retries, timeout, streaming) + analyzer
├── validators/     # yaml_validator, terraform_validator
├── security/       # scanner (Checkov, tfsec, Trivy, Semgrep, static)
├── services/       # validation_service, auth_service, dashboard_service
├── api/            # FastAPI routes (v1)
├── cli/            # ytv command-line interface
├── reporting/      # JSON, YAML, Markdown, HTML, SARIF, JUnit
├── cache/          # Validation result LRU cache
├── plugins/        # Extensible validator plugin registry
├── logging/        # Structured logging setup
├── models/         # SQLAlchemy ORM
└── workers/        # Celery tasks (optional, requires Redis)
```

---

## API Documentation

Interactive documentation is available when the backend is running:

| Endpoint | Description |
|----------|-------------|
| `/docs` | Swagger UI |
| `/redoc` | ReDoc |
| `/openapi.json` | OpenAPI 3 schema |

### Core validation endpoint

```http
POST /api/v1/validations/run
Content-Type: application/json

{
  "content": "apiVersion: v1\nkind: Pod\nmetadata:\n  name: demo",
  "file_path": "pod.yaml",
  "validation_type": "auto",
  "include_ai_analysis": true,
  "include_security_scan": true
}
```

Guest access is supported—no login required for validation.

Additional examples: [docs/api-reference.md](Checker/docs/api-reference.md)

---

## Deployment

### Docker Compose files

| File | Use case |
|------|----------|
| `docker-compose.ec2.yml` | Production: frontend + backend + nginx + SQLite |
| `docker-compose.yml` | Full stack: MySQL, Redis, backend |
| `docker-compose.prod.yml` | Production overrides |
| `docker-compose.dev.yml` | Hot-reload development |

### Environment variables

Copy `Checker/.env.example` to `Checker/.env`:

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | JWT signing secret | *(change in production)* |
| `DB_ENGINE` | `sqlite` or `mysql` | `sqlite` |
| `CORS_ORIGINS` | Allowed browser origins (comma-separated) | EC2 public URL |
| `OPENAI_API_KEY` | AI provider key | *(optional)* |
| `API_INTERNAL_URL` | Backend URL for Next.js SSR | `http://backend:8000` |
| `NEXT_PUBLIC_API_URL` | Public API URL for browser | Your host |

### AWS EC2 checklist

1. Security group: inbound **TCP 80** (HTTP) and **22** (SSH).
2. Deploy with `docker compose -f docker-compose.ec2.yml up -d`.
3. Verify: `curl http://127.0.0.1/health`.

See [docs/deployment-guide.md](Checker/docs/deployment-guide.md) for extended instructions.

---

## Project structure

```
Checker/
├── backend/          # FastAPI application
├── frontend/         # Next.js web UI
├── docker/nginx/     # Reverse proxy configuration
├── scripts/          # Deploy & bootstrap scripts
├── docs/             # Architecture, security, API guides
└── docker-compose.ec2.yml
```

---

## Documentation

- [Architecture](Checker/docs/architecture.md)
- [System design](Checker/docs/system-design.md)
- [Deployment guide](Checker/docs/deployment-guide.md)
- [Security guide](Checker/docs/security-guide.md)
- [API reference](Checker/docs/api-reference.md)

---

## Contributing

1. Fork the repository and create a feature branch.
2. Run tests: `cd Checker/backend && pytest`
3. Run lint: `cd Checker/backend && ruff check app/`
4. Submit a pull request with a clear description.

---

## License

This project is licensed under the **MIT License** — see the [LICENSE](Checker/LICENSE) file for details.
