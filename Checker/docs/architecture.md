# Architecture Documentation

## System Overview

The YAML & Terraform AI Validator is a microservices-based SaaS platform built with a modern tech stack optimized for cloud-native deployment.

## Frontend Architecture

```
frontend/
├── src/app/              # Next.js 15 App Router pages
│   ├── (auth)/           # Authentication pages
│   ├── (dashboard)/      # Protected dashboard pages
│   └── layout.tsx        # Root layout with providers
├── src/components/
│   ├── ui/               # ShadCN UI components
│   ├── layout/           # Layout components (sidebar, header)
│   ├── dashboard/        # Dashboard widgets
│   └── validation/       # Validation UI components
├── src/lib/              # API client, utilities
├── src/store/            # Zustand state management
└── public/locales/       # i18n translations (en, ru, hy)
```

**Key Technologies:**
- Next.js 15 with App Router and React Server Components
- React 19 with TypeScript
- Tailwind CSS + ShadCN UI for design system
- Framer Motion for animations
- Zustand for client state, React Query for server state
- next-themes for dark/light mode

## Backend Architecture

```
backend/app/
├── main.py               # FastAPI application entry
├── core/                 # Config, database, security
├── models/               # SQLAlchemy ORM models (18 tables)
├── schemas/              # Pydantic v2 request/response models
├── api/v1/               # REST API route handlers
├── services/             # Business logic layer
├── validators/           # YAML & Terraform engines
├── security/             # Security scanning engine
├── ai/                   # AI analysis engine
└── workers/              # Celery async tasks
```

**Request Flow:**
1. Client → Nginx → FastAPI
2. JWT/API Key authentication via dependency injection
3. Rate limiting via SlowAPI
4. Route handler → Service layer → Validator/Scanner/AI
5. Results persisted to MySQL via SQLAlchemy async
6. Background tasks queued to Celery via Redis

## Database Architecture

18 normalized tables with proper foreign key relationships:

```
Users ←→ Roles ←→ Permissions (RBAC)
Users ←→ Teams ←→ Projects ←→ Repositories
Projects ←→ ValidationHistory ←→ ValidationResults
ValidationHistory ←→ AIExplanations
ValidationHistory ←→ SecurityScans
Repositories ←→ YamlFiles, TerraformModules
Users ←→ ApiKeys, Notifications, AuditLogs, ActivityFeed
Settings (global/user/team scoped)
Invitations (team membership)
```

## Validation Engine

### YAML Engine
- PyYAML syntax validation
- Duplicate key detection (custom loader)
- Auto-detection: Kubernetes, Helm, Docker Compose, GHA, GitLab CI
- Best practices: tabs, trailing whitespace, indentation
- Schema validation via jsonschema

### Terraform Engine
- Static HCL analysis (resources, modules, variables, providers)
- Secret detection (passwords, API keys)
- Security checks (public S3, open SG)
- CLI integration: `terraform validate`, `terraform fmt`
- Dependency graph generation
- Cost estimation heuristics

## Security Engine

Multi-scanner architecture with fallback:
1. **Static patterns** — Always available (secrets, misconfigurations)
2. **Checkov** — IaC security scanner
3. **tfsec** — Terraform-specific security
4. **Trivy** — Container and config scanning
5. **Semgrep** — Static analysis rules

Severity levels: Critical → High → Medium → Low → Informational

## AI Engine

OpenAI-compatible architecture supporting:
- OpenAI GPT models
- Azure OpenAI deployments
- Ollama local models
- Rule-based fallback (no API required)

Capabilities: line explanations, risk analysis, fix generation, cost optimization suggestions.

## GitHub Integration

- OAuth 2.0 login flow
- Repository listing and linking
- Webhook processing (push, pull_request events)
- Automatic validation on code changes
- Celery task queue for async webhook processing

## Docker Infrastructure

11 services in docker-compose.yml:
- frontend, backend, worker, scheduler
- mysql, redis, nginx
- prometheus, grafana, loki, otel-collector

## CI/CD Pipeline

GitHub Actions / GitLab CI / Jenkins with stages:
1. Lint (black, ruff, bandit, eslint)
2. Test (pytest, jest)
3. Security Scan (bandit, semgrep)
4. Build (docker compose build)
5. Deploy (production)

## Monitoring Stack

- **Prometheus** — Metrics collection from `/metrics` endpoint
- **Grafana** — Dashboards and visualization
- **Loki** — Log aggregation
- **OpenTelemetry** — Distributed tracing via OTLP collector

## Kubernetes Deployment

See `infrastructure/kubernetes/` and `infrastructure/helm/` for K8s manifests and Helm charts supporting AWS, Azure, GCP, DigitalOcean, and Hetzner.
