"""
Pydantic v2 schemas for request/response validation.

Defines all API input/output models with strict typing.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class SeverityLevel(str, Enum):
    """Security/validation severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ValidationStatus(str, Enum):
    """Validation run status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"


class UserRole(str, Enum):
    """RBAC roles."""

    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


# --- Auth Schemas ---


class UserCreate(BaseModel):
    """Registration request payload."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=100)
    password: str = Field(min_length=8, max_length=128)
    full_name: Optional[str] = None
    preferred_language: str = "en"


class UserLogin(BaseModel):
    """Login request payload."""

    email: EmailStr
    password: str
    mfa_token: Optional[str] = None


class TokenResponse(BaseModel):
    """JWT token response after successful authentication."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class UserResponse(BaseModel):
    """Public user profile response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    username: str
    full_name: Optional[str]
    is_active: bool
    is_verified: bool
    mfa_enabled: bool
    avatar_url: Optional[str]
    preferred_language: str
    roles: list[str] = []
    created_at: datetime


class PasswordResetRequest(BaseModel):
    """Password reset email request."""

    email: EmailStr


class PasswordResetConfirm(BaseModel):
    """Password reset confirmation with token."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)


class MFASetupResponse(BaseModel):
    """MFA enrollment response with QR code URI."""

    secret: str
    provisioning_uri: str
    qr_code_base64: Optional[str] = None


class MFAEnableRequest(BaseModel):
    """MFA enable confirmation with TOTP token."""

    token: str


# --- Validation Schemas ---


class ValidationRequest(BaseModel):
    """Request to validate YAML or Terraform content."""

    content: str = Field(description="File content to validate")
    file_path: str = Field(default="unknown.yaml", description="Virtual file path")
    validation_type: str = Field(default="auto", description="yaml, terraform, security, or auto")
    project_id: Optional[int] = None
    repository_id: Optional[int] = None
    branch: Optional[str] = None
    include_ai_analysis: bool = True
    include_security_scan: bool = True
    language: str = "en"


class ValidationFinding(BaseModel):
    """Single validation finding."""

    file_path: str
    line_number: Optional[int] = None
    column_number: Optional[int] = None
    rule_id: Optional[str] = None
    severity: SeverityLevel
    category: str
    message: str
    original_code: Optional[str] = None
    corrected_code: Optional[str] = None
    correction_reason: Optional[str] = None
    impact: Optional[str] = None


class LineExplanation(BaseModel):
    """AI line-by-line explanation."""

    line_number: int
    code: str
    explanation: str
    risk_level: SeverityLevel
    recommendation: Optional[str] = None


class SecurityFinding(BaseModel):
    """Security scan finding."""

    scanner: str
    rule_id: str
    severity: SeverityLevel
    title: str
    description: Optional[str] = None
    file_path: str
    line_number: Optional[int] = None
    resource: Optional[str] = None
    remediation: Optional[str] = None


class ValidationResponse(BaseModel):
    """Complete validation response."""

    validation_id: int
    status: ValidationStatus
    validation_type: str
    duration_ms: int
    error_count: int
    warning_count: int
    security_findings_count: int
    findings: list[ValidationFinding] = []
    security_findings: list[SecurityFinding] = []
    ai_explanations: list[LineExplanation] = []
    corrected_content: Optional[str] = None
    summary: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class ValidationHistoryResponse(BaseModel):
    """Validation history list item."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    validation_type: str
    status: ValidationStatus
    branch: Optional[str]
    commit_sha: Optional[str]
    error_count: int
    warning_count: int
    security_findings_count: int
    duration_ms: Optional[int]
    summary: Optional[str]
    created_at: datetime


class ValidationHistoryFilter(BaseModel):
    """Filter parameters for validation history search."""

    project_id: Optional[int] = None
    repository_id: Optional[int] = None
    status: Optional[ValidationStatus] = None
    validation_type: Optional[str] = None
    branch: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
    search: Optional[str] = None
    sort_by: str = "created_at"
    sort_order: str = "desc"
    page: int = 1
    page_size: int = 20


# --- Project Schemas ---


class ProjectCreate(BaseModel):
    """Create project request."""

    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    project_type: str = "mixed"
    team_id: Optional[int] = None


class ProjectResponse(BaseModel):
    """Project response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    project_type: str
    is_active: bool
    created_at: datetime


class RepositoryCreate(BaseModel):
    """Link GitHub repository to project."""

    full_name: str = Field(description="GitHub org/repo format")
    default_branch: str = "main"
    auto_scan: bool = True


class RepositoryResponse(BaseModel):
    """Repository response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    full_name: str
    default_branch: str
    auto_scan: bool
    last_synced_at: Optional[datetime]


# --- Team Schemas ---


class TeamCreate(BaseModel):
    """Create team request."""

    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None


class TeamResponse(BaseModel):
    """Team response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    description: Optional[str]
    is_active: bool
    member_count: int = 0
    created_at: datetime


class InvitationCreate(BaseModel):
    """Send team invitation."""

    email: EmailStr
    role: str = "member"


# --- API Key Schemas ---


class ApiKeyCreate(BaseModel):
    """Create API key request."""

    name: str = Field(min_length=1, max_length=255)
    scopes: list[str] = []
    expires_in_days: Optional[int] = 365


class ApiKeyResponse(BaseModel):
    """API key response (key shown only once on creation)."""

    id: int
    name: str
    key_prefix: str
    key: Optional[str] = None  # Only returned on creation
    scopes: list[str]
    is_active: bool
    created_at: datetime
    expires_at: Optional[datetime]


# --- Dashboard Schemas ---


class DashboardStats(BaseModel):
    """Dashboard widget statistics."""

    total_scans: int
    failed_validations: int
    successful_validations: int
    security_findings: int
    terraform_projects: int
    yaml_projects: int
    ai_recommendations: int


class TrendDataPoint(BaseModel):
    """Chart data point for trends."""

    date: str
    value: int
    label: Optional[str] = None


class DashboardCharts(BaseModel):
    """Dashboard chart data."""

    validation_trends: list[TrendDataPoint]
    security_trends: list[TrendDataPoint]
    repository_stats: list[TrendDataPoint]
    scan_performance: list[TrendDataPoint]


class ActivityItem(BaseModel):
    """Activity feed item."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    activity_type: str
    title: str
    description: Optional[str]
    user_name: str
    created_at: datetime


class DashboardResponse(BaseModel):
    """Complete dashboard data."""

    stats: DashboardStats
    charts: DashboardCharts
    recent_activity: list[ActivityItem]
    ai_recommendations: list[str]


# --- GitHub Schemas ---


class GitHubOAuthCallback(BaseModel):
    """GitHub OAuth callback payload."""

    code: str
    state: Optional[str] = None


class GitHubWebhookPayload(BaseModel):
    """GitHub webhook event payload (partial)."""

    action: Optional[str] = None
    repository: Optional[dict[str, Any]] = None
    ref: Optional[str] = None
    commits: Optional[list[dict[str, Any]]] = None
    pull_request: Optional[dict[str, Any]] = None


# --- Generic ---


class MessageResponse(BaseModel):
    """Generic message response."""

    message: str
    detail: Optional[str] = None


class PaginatedResponse(BaseModel):
    """Generic paginated list response."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    total_pages: int


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    database: str
    redis: str
    celery: str
