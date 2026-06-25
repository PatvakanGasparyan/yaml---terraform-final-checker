# API Reference

Base URL: `http://localhost:8000/api/v1`

Authentication: Bearer token in `Authorization` header, or API key (`ytv_*` format).

## Authentication

### POST /auth/register
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "username": "username",
  "password": "securepass123",
  "full_name": "Full Name",
  "preferred_language": "en"
}
```

**Response:** `201` UserResponse

### POST /auth/login
Authenticate and receive JWT tokens.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "securepass123",
  "mfa_token": "123456"
}
```

**Response:** `200` TokenResponse
```json
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

### GET /auth/me
Get current user profile. Requires authentication.

**Response:** `200` UserResponse

### POST /auth/mfa/setup
Initialize MFA enrollment. Returns QR code URI.

### POST /auth/mfa/enable
Enable MFA with TOTP verification token.

## Validations

### POST /validations/run
Run validation on YAML or Terraform content.

**Request:**
```json
{
  "content": "apiVersion: v1\nkind: Pod\n...",
  "file_path": "deployment.yaml",
  "validation_type": "auto",
  "include_ai_analysis": true,
  "include_security_scan": true,
  "language": "en"
}
```

**Response:** `200` ValidationResponse
```json
{
  "validation_id": 1,
  "status": "warning",
  "validation_type": "yaml",
  "duration_ms": 245,
  "error_count": 0,
  "warning_count": 2,
  "security_findings_count": 1,
  "findings": [
    {
      "file_path": "deployment.yaml",
      "line_number": 8,
      "severity": "critical",
      "category": "kubernetes_security",
      "message": "Container runs as privileged",
      "original_code": "      privileged: true",
      "corrected_code": "      privileged: false",
      "correction_reason": "Privileged containers have full host access",
      "impact": "Security risk"
    }
  ],
  "security_findings": [...],
  "ai_explanations": [
    {
      "line_number": 1,
      "code": "apiVersion: v1",
      "explanation": "Defines the Kubernetes API version",
      "risk_level": "informational",
      "recommendation": null
    }
  ],
  "corrected_content": "...",
  "summary": "2 warning(s), 1 security finding(s)"
}
```

### GET /validations/history
Search validation history with pagination.

**Query Parameters:**
- `project_id` — Filter by project
- `status` — pending, running, success, failed, warning
- `validation_type` — yaml, terraform
- `search` — Text search in summary
- `page` — Page number (default: 1)
- `page_size` — Items per page (default: 20)
- `sort_by` — Sort field (default: created_at)
- `sort_order` — asc or desc

**Response:** `200` PaginatedResponse

### GET /validations/{validation_id}
Get single validation record.

## Dashboard

### GET /dashboard
Get dashboard statistics, charts, and activity.

**Response:** `200` DashboardResponse

## GitHub

### GET /github/oauth/url
Get GitHub OAuth authorization URL.

### POST /github/oauth/callback
Complete OAuth flow with authorization code.

### GET /github/repos
List user's GitHub repositories.

### POST /github/repos/{project_id}
Link repository to project.

### POST /github/webhook
GitHub webhook endpoint (signature verified).

## Health & Monitoring

### GET /health
Health check endpoint.

### GET /metrics
Prometheus metrics (not under /api/v1).

## Error Responses

```json
{
  "detail": "Error message"
}
```

| Status | Description |
|--------|-------------|
| 400 | Bad request / validation error |
| 401 | Not authenticated |
| 403 | Insufficient permissions |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |

## Rate Limits

- Default: 60 requests/minute per IP
- API keys: configurable per key (default 1000/hour)
- Validation endpoint: counted against general limit

## OpenAPI

Interactive documentation available at:
- Swagger UI: `/docs`
- ReDoc: `/redoc`
- OpenAPI JSON: `/openapi.json`
