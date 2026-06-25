# Security Guide

## Authentication

### JWT Tokens
- Access tokens expire in 30 minutes (configurable)
- Refresh tokens expire in 7 days
- HS256 algorithm with configurable secret key
- **Production**: Generate secret with `openssl rand -hex 32`

### Multi-Factor Authentication (MFA)
- TOTP-based (Google Authenticator compatible)
- Optional per-user enrollment
- Required on login when enabled

### API Keys
- Format: `ytv_<prefix>_<secret>`
- Bcrypt hashed storage (only prefix stored in plain text)
- Configurable scopes and rate limits
- Expiration support

## Authorization (RBAC)

| Role | Permissions |
|------|------------|
| Admin | Full platform access, user management, settings |
| Manager | Team/project management, invite members |
| Developer | Create/run validations, manage own projects |
| Viewer | Read-only access to validations and reports |

## Security Scanning

### Detected Threats
- Hardcoded API keys, secrets, tokens, passwords
- Private keys in configuration files
- Open network rules (0.0.0.0/0)
- Public S3 buckets and storage
- Privileged containers
- Root container execution
- Disabled encryption
- Insecure HTTP endpoints

### Severity Classification
- **Critical** — Immediate action required (exposed secrets, public resources)
- **High** — Significant risk (open ingress, privileged containers)
- **Medium** — Should be addressed (missing type declarations, HTTP endpoints)
- **Low** — Best practice violations (trailing whitespace, missing descriptions)
- **Informational** — Information only

## Rate Limiting

- Default: 60 requests/minute per IP
- Configurable via `RATE_LIMIT_PER_MINUTE`
- API keys have per-key rate limits

## Data Protection

- Passwords hashed with bcrypt
- API keys hashed with bcrypt
- GitHub tokens stored encrypted in database
- Settings marked as secret are not exposed in API responses
- CORS restricted to configured origins

## Audit Logging

All sensitive actions are logged:
- User login/logout
- Validation runs
- Project/repository changes
- Team membership changes
- API key creation/revocation
- Settings modifications

Audit log fields: user, action, resource, IP address, user agent, timestamp

## Network Security

- Nginx reverse proxy with request size limits (50MB)
- Internal Docker network for service communication
- Database and Redis not exposed externally in production
- Webhook signature verification (HMAC-SHA256)

## Backup Security

- Automated daily backups at 2 AM UTC
- Backup files stored in Docker volume
- Restore requires database credentials
- 90-day retention for validation history

## Production Checklist

- [ ] Change `SECRET_KEY` to cryptographically random value
- [ ] Change MySQL root and user passwords
- [ ] Configure SSL/TLS certificates
- [ ] Set `DEBUG=false`
- [ ] Configure CORS for production domain only
- [ ] Enable MFA for admin accounts
- [ ] Configure GitHub webhook secret
- [ ] Set up monitoring alerts in Grafana
- [ ] Review and restrict API key scopes
- [ ] Enable audit log monitoring
- [ ] Configure backup verification schedule

## Vulnerability Reporting

Report security vulnerabilities to: security@yaml-validator.local

Do not disclose publicly until patched.

## Compliance

The platform supports enterprise compliance requirements:
- Audit trail for SOC 2
- RBAC for access control policies
- Data retention policies
- Encryption at rest (MySQL) and in transit (TLS)
- SSO/LDAP integration points (extensible)
