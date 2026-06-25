"""
SQLAlchemy ORM models for the YAML & Terraform AI Validator platform.

Defines normalized production schema with all required tables:
Users, Roles, Permissions, Projects, Repositories, ValidationHistory,
ValidationResults, AIExplanations, SecurityScans, TerraformModules,
YamlFiles, AuditLogs, Settings, Notifications, ApiKeys, Teams, Invitations,
ActivityFeed.
"""

import enum
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SeverityLevel(str, enum.Enum):
    """Security finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFORMATIONAL = "informational"


class ValidationStatus(str, enum.Enum):
    """Validation run status."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    WARNING = "warning"


class UserRole(str, enum.Enum):
    """RBAC role names."""

    ADMIN = "admin"
    MANAGER = "manager"
    DEVELOPER = "developer"
    VIEWER = "viewer"


# Association table for many-to-many User-Role relationship
class UserRoleAssociation(Base):
    """Links users to their assigned roles."""

    __tablename__ = "user_roles"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)


class RolePermissionAssociation(Base):
    """Links roles to their granted permissions."""

    __tablename__ = "role_permissions"

    role_id: Mapped[int] = mapped_column(ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[int] = mapped_column(
        ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )


class TeamMemberAssociation(Base):
    """Links users to teams with membership metadata."""

    __tablename__ = "team_members"

    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role: Mapped[str] = mapped_column(String(50), default="member")
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class User(Base):
    """
    Platform user account.

    Stores authentication credentials, profile info, MFA settings,
    and email verification status.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[Optional[str]] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    mfa_secret: Mapped[Optional[str]] = mapped_column(String(255))
    github_id: Mapped[Optional[str]] = mapped_column(String(100), unique=True)
    github_access_token: Mapped[Optional[str]] = mapped_column(Text)
    avatar_url: Mapped[Optional[str]] = mapped_column(String(500))
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    roles: Mapped[list["Role"]] = relationship(secondary="user_roles", back_populates="users")
    teams: Mapped[list["Team"]] = relationship(secondary="team_members", back_populates="members")
    projects: Mapped[list["Project"]] = relationship(back_populates="owner")
    api_keys: Mapped[list["ApiKey"]] = relationship(back_populates="user")
    audit_logs: Mapped[list["AuditLog"]] = relationship(back_populates="user")
    notifications: Mapped[list["Notification"]] = relationship(back_populates="user")
    activity_feed: Mapped[list["ActivityFeed"]] = relationship(back_populates="user")


class Role(Base):
    """RBAC role definition (Admin, Manager, Developer, Viewer)."""

    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    users: Mapped[list["User"]] = relationship(secondary="user_roles", back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(
        secondary="role_permissions", back_populates="roles"
    )


class Permission(Base):
    """Granular permission for RBAC (e.g., validation:create, project:delete)."""

    __tablename__ = "permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255))

    roles: Mapped[list["Role"]] = relationship(
        secondary="role_permissions", back_populates="permissions"
    )


class Team(Base):
    """Team/organization unit for multi-tenant collaboration."""

    __tablename__ = "teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    members: Mapped[list["User"]] = relationship(secondary="team_members", back_populates="teams")
    projects: Mapped[list["Project"]] = relationship(back_populates="team")
    invitations: Mapped[list["Invitation"]] = relationship(back_populates="team")


class Invitation(Base):
    """Team invitation sent to email addresses."""

    __tablename__ = "invitations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(50), default="member")
    token: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    invited_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    team: Mapped["Team"] = relationship(back_populates="invitations")


class Project(Base):
    """Validation project grouping repositories and configurations."""

    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    project_type: Mapped[str] = mapped_column(String(50), default="mixed")  # yaml, terraform, mixed
    owner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped["User"] = relationship(back_populates="projects")
    team: Mapped[Optional["Team"]] = relationship(back_populates="projects")
    repositories: Mapped[list["Repository"]] = relationship(back_populates="project")
    validation_history: Mapped[list["ValidationHistory"]] = relationship(back_populates="project")


class Repository(Base):
    """Git repository linked to a project (GitHub integration)."""

    __tablename__ = "repositories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(500), nullable=False)  # org/repo
    github_repo_id: Mapped[Optional[int]] = mapped_column(Integer)
    default_branch: Mapped[str] = mapped_column(String(100), default="main")
    clone_url: Mapped[Optional[str]] = mapped_column(String(500))
    webhook_id: Mapped[Optional[int]] = mapped_column(Integer)
    auto_scan: Mapped[bool] = mapped_column(Boolean, default=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="repositories")
    validation_history: Mapped[list["ValidationHistory"]] = relationship(back_populates="repository")
    yaml_files: Mapped[list["YamlFile"]] = relationship(back_populates="repository")
    terraform_modules: Mapped[list["TerraformModule"]] = relationship(back_populates="repository")


class ValidationHistory(Base):
    """
    Record of each validation run.

    Stores metadata about who ran validation, on which repo/branch/commit,
    and links to detailed results.
    """

    __tablename__ = "validation_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[Optional[int]] = mapped_column(ForeignKey("projects.id"))
    repository_id: Mapped[Optional[int]] = mapped_column(ForeignKey("repositories.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    validation_type: Mapped[str] = mapped_column(String(50), nullable=False)  # yaml, terraform, security
    status: Mapped[ValidationStatus] = mapped_column(
        Enum(ValidationStatus), default=ValidationStatus.PENDING
    )
    branch: Mapped[Optional[str]] = mapped_column(String(255))
    commit_sha: Mapped[Optional[str]] = mapped_column(String(40))
    commit_message: Mapped[Optional[str]] = mapped_column(Text)
    pull_request_number: Mapped[Optional[int]] = mapped_column(Integer)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer)
    error_count: Mapped[int] = mapped_column(Integer, default=0)
    warning_count: Mapped[int] = mapped_column(Integer, default=0)
    security_findings_count: Mapped[int] = mapped_column(Integer, default=0)
    summary: Mapped[Optional[str]] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    project: Mapped["Project"] = relationship(back_populates="validation_history")
    repository: Mapped[Optional["Repository"]] = relationship(back_populates="validation_history")
    results: Mapped[list["ValidationResult"]] = relationship(back_populates="validation")
    ai_explanations: Mapped[list["AIExplanation"]] = relationship(back_populates="validation")
    security_scans: Mapped[list["SecurityScan"]] = relationship(back_populates="validation")


class ValidationResult(Base):
    """Individual validation finding or check result."""

    __tablename__ = "validation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    validation_id: Mapped[int] = mapped_column(
        ForeignKey("validation_history.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    column_number: Mapped[Optional[int]] = mapped_column(Integer)
    rule_id: Mapped[Optional[str]] = mapped_column(String(100))
    severity: Mapped[SeverityLevel] = mapped_column(Enum(SeverityLevel), default=SeverityLevel.INFORMATIONAL)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    original_code: Mapped[Optional[str]] = mapped_column(Text)
    corrected_code: Mapped[Optional[str]] = mapped_column(Text)
    correction_reason: Mapped[Optional[str]] = mapped_column(Text)
    impact: Mapped[Optional[str]] = mapped_column(Text)
    is_fixed: Mapped[bool] = mapped_column(Boolean, default=False)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    validation: Mapped["ValidationHistory"] = relationship(back_populates="results")


class AIExplanation(Base):
    """AI-generated line-by-line code explanation."""

    __tablename__ = "ai_explanations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    validation_id: Mapped[int] = mapped_column(
        ForeignKey("validation_history.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    risk_level: Mapped[SeverityLevel] = mapped_column(
        Enum(SeverityLevel), default=SeverityLevel.INFORMATIONAL
    )
    recommendation: Mapped[Optional[str]] = mapped_column(Text)
    language: Mapped[str] = mapped_column(String(20), default="yaml")
    ai_model: Mapped[Optional[str]] = mapped_column(String(100))
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    validation: Mapped["ValidationHistory"] = relationship(back_populates="ai_explanations")


class SecurityScan(Base):
    """Security scan result from Checkov, tfsec, Trivy, or Semgrep."""

    __tablename__ = "security_scans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    validation_id: Mapped[int] = mapped_column(
        ForeignKey("validation_history.id", ondelete="CASCADE"), nullable=False
    )
    scanner: Mapped[str] = mapped_column(String(50), nullable=False)  # checkov, tfsec, trivy, semgrep
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[SeverityLevel] = mapped_column(Enum(SeverityLevel), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    line_number: Mapped[Optional[int]] = mapped_column(Integer)
    resource: Mapped[Optional[str]] = mapped_column(String(255))
    remediation: Mapped[Optional[str]] = mapped_column(Text)
    cwe_id: Mapped[Optional[str]] = mapped_column(String(20))
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    validation: Mapped["ValidationHistory"] = relationship(back_populates="security_scans")


class TerraformModule(Base):
    """Tracked Terraform module within a repository."""

    __tablename__ = "terraform_modules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    path: Mapped[str] = mapped_column(String(500), nullable=False)
    source: Mapped[Optional[str]] = mapped_column(String(500))
    version: Mapped[Optional[str]] = mapped_column(String(50))
    providers: Mapped[Optional[dict]] = mapped_column(JSON)
    variables: Mapped[Optional[dict]] = mapped_column(JSON)
    outputs: Mapped[Optional[dict]] = mapped_column(JSON)
    resources_count: Mapped[int] = mapped_column(Integer, default=0)
    estimated_cost: Mapped[Optional[float]] = mapped_column()
    dependency_graph: Mapped[Optional[dict]] = mapped_column(JSON)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repository: Mapped["Repository"] = relationship(back_populates="terraform_modules")


class YamlFile(Base):
    """Tracked YAML file within a repository."""

    __tablename__ = "yaml_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    repository_id: Mapped[int] = mapped_column(
        ForeignKey("repositories.id", ondelete="CASCADE"), nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50), default="generic")  # k8s, helm, compose, etc.
    content_hash: Mapped[Optional[str]] = mapped_column(String(64))
    line_count: Mapped[int] = mapped_column(Integer, default=0)
    schema_valid: Mapped[Optional[bool]] = mapped_column(Boolean)
    last_validated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    repository: Mapped["Repository"] = relationship(back_populates="yaml_files")


class AuditLog(Base):
    """Enterprise audit trail for compliance and security."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(ForeignKey("users.id"))
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False)
    resource_id: Mapped[Optional[str]] = mapped_column(String(100))
    ip_address: Mapped[Optional[str]] = mapped_column(String(45))
    user_agent: Mapped[Optional[str]] = mapped_column(String(500))
    details: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs")


class Setting(Base):
    """Platform and user-level settings key-value store."""

    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    key: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    value_type: Mapped[str] = mapped_column(String(20), default="string")
    scope: Mapped[str] = mapped_column(String(50), default="global")  # global, user, team
    scope_id: Mapped[Optional[int]] = mapped_column(Integer)
    description: Mapped[Optional[str]] = mapped_column(String(500))
    is_secret: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (UniqueConstraint("key", "scope", "scope_id", name="uq_settings_key_scope"),)


class Notification(Base):
    """User notification (email, slack, telegram, in-app)."""

    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notification_type: Mapped[str] = mapped_column(String(50), default="info")
    channel: Mapped[str] = mapped_column(String(50), default="in_app")  # email, slack, telegram, webhook
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    link: Mapped[Optional[str]] = mapped_column(String(500))
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="notifications")


class ApiKey(Base):
    """API key for programmatic access with rate limiting."""

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    key_prefix: Mapped[str] = mapped_column(String(20), nullable=False)
    hashed_key: Mapped[str] = mapped_column(String(255), nullable=False)
    scopes: Mapped[Optional[list]] = mapped_column(JSON, default=list)
    rate_limit: Mapped[int] = mapped_column(Integer, default=1000)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="api_keys")


class ActivityFeed(Base):
    """Team activity feed for dashboard widgets."""

    __tablename__ = "activity_feed"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"))
    activity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)
    resource_type: Mapped[Optional[str]] = mapped_column(String(50))
    resource_id: Mapped[Optional[int]] = mapped_column(Integer)
    extra_data: Mapped[Optional[dict]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped["User"] = relationship(back_populates="activity_feed")
