-- =============================================================================
-- YAML & Terraform AI Validator — MySQL 8.0+ Schema
-- =============================================================================
-- Database: yaml_terraform_validator
-- Charset:  utf8mb4 (full Unicode support: EN, RU, HY)
--
-- Usage (Docker):
--   docker compose exec mysql mysql -u root -proot_secret < /docker-entrypoint-initdb.d/schema.sql
--
-- Usage (local):
--   mysql -u root -p < scripts/mysql-schema.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS yaml_terraform_validator
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE yaml_terraform_validator;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ---------------------------------------------------------------------------
-- Drop tables (reverse dependency order)
-- ---------------------------------------------------------------------------
DROP TABLE IF EXISTS activity_feed;
DROP TABLE IF EXISTS api_keys;
DROP TABLE IF EXISTS notifications;
DROP TABLE IF EXISTS settings;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS yaml_files;
DROP TABLE IF EXISTS terraform_modules;
DROP TABLE IF EXISTS security_scans;
DROP TABLE IF EXISTS ai_explanations;
DROP TABLE IF EXISTS validation_results;
DROP TABLE IF EXISTS validation_history;
DROP TABLE IF EXISTS repositories;
DROP TABLE IF EXISTS projects;
DROP TABLE IF EXISTS invitations;
DROP TABLE IF EXISTS team_members;
DROP TABLE IF EXISTS teams;
DROP TABLE IF EXISTS role_permissions;
DROP TABLE IF EXISTS user_roles;
DROP TABLE IF EXISTS permissions;
DROP TABLE IF EXISTS roles;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- ---------------------------------------------------------------------------
-- users — platform accounts (optional auth; guest used for public access)
-- ---------------------------------------------------------------------------
CREATE TABLE users (
    id                  INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email               VARCHAR(255) NOT NULL,
    username            VARCHAR(100) NOT NULL,
    hashed_password     VARCHAR(255) NOT NULL,
    full_name           VARCHAR(255) NULL,
    is_active           TINYINT(1) NOT NULL DEFAULT 1,
    is_verified         TINYINT(1) NOT NULL DEFAULT 0,
    is_superuser        TINYINT(1) NOT NULL DEFAULT 0,
    mfa_enabled         TINYINT(1) NOT NULL DEFAULT 0,
    mfa_secret          VARCHAR(255) NULL,
    github_id           VARCHAR(100) NULL,
    github_access_token TEXT NULL,
    avatar_url          VARCHAR(500) NULL,
    preferred_language  VARCHAR(10) NOT NULL DEFAULT 'en',
    last_login          DATETIME(6) NULL,
    created_at          DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at          DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_users_email (email),
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_github_id (github_id),
    KEY idx_users_email (email),
    KEY idx_users_username (username)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- roles — RBAC roles
-- ---------------------------------------------------------------------------
CREATE TABLE roles (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(50) NOT NULL,
    description VARCHAR(255) NULL,
    created_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_roles_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- permissions — granular RBAC permissions
-- ---------------------------------------------------------------------------
CREATE TABLE permissions (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(100) NOT NULL,
    resource    VARCHAR(50) NOT NULL,
    action      VARCHAR(50) NOT NULL,
    description VARCHAR(255) NULL,

    UNIQUE KEY uq_permissions_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- user_roles — many-to-many: users ↔ roles
-- ---------------------------------------------------------------------------
CREATE TABLE user_roles (
    user_id INT UNSIGNED NOT NULL,
    role_id INT UNSIGNED NOT NULL,

    PRIMARY KEY (user_id, role_id),
    KEY idx_user_roles_role_id (role_id),
    CONSTRAINT fk_user_roles_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_user_roles_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- role_permissions — many-to-many: roles ↔ permissions
-- ---------------------------------------------------------------------------
CREATE TABLE role_permissions (
    role_id       INT UNSIGNED NOT NULL,
    permission_id INT UNSIGNED NOT NULL,

    PRIMARY KEY (role_id, permission_id),
    KEY idx_role_permissions_permission_id (permission_id),
    CONSTRAINT fk_role_permissions_role FOREIGN KEY (role_id) REFERENCES roles(id) ON DELETE CASCADE,
    CONSTRAINT fk_role_permissions_permission FOREIGN KEY (permission_id) REFERENCES permissions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- teams — organization / multi-tenant units
-- ---------------------------------------------------------------------------
CREATE TABLE teams (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) NOT NULL,
    description TEXT NULL,
    owner_id    INT UNSIGNED NOT NULL,
    is_active   TINYINT(1) NOT NULL DEFAULT 1,
    created_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_teams_slug (slug),
    KEY idx_teams_slug (slug),
    KEY idx_teams_owner_id (owner_id),
    CONSTRAINT fk_teams_owner FOREIGN KEY (owner_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- team_members — many-to-many: teams ↔ users
-- ---------------------------------------------------------------------------
CREATE TABLE team_members (
    team_id    INT UNSIGNED NOT NULL,
    user_id    INT UNSIGNED NOT NULL,
    role       VARCHAR(50) NOT NULL DEFAULT 'member',
    joined_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    PRIMARY KEY (team_id, user_id),
    KEY idx_team_members_user_id (user_id),
    CONSTRAINT fk_team_members_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    CONSTRAINT fk_team_members_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- invitations — team invite tokens
-- ---------------------------------------------------------------------------
CREATE TABLE invitations (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    team_id       INT UNSIGNED NOT NULL,
    email         VARCHAR(255) NOT NULL,
    role          VARCHAR(50) NOT NULL DEFAULT 'member',
    token         VARCHAR(255) NOT NULL,
    invited_by_id INT UNSIGNED NOT NULL,
    accepted      TINYINT(1) NOT NULL DEFAULT 0,
    expires_at    DATETIME(6) NOT NULL,
    created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_invitations_token (token),
    KEY idx_invitations_team_id (team_id),
    KEY idx_invitations_invited_by (invited_by_id),
    CONSTRAINT fk_invitations_team FOREIGN KEY (team_id) REFERENCES teams(id) ON DELETE CASCADE,
    CONSTRAINT fk_invitations_invited_by FOREIGN KEY (invited_by_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- projects — validation project groups
-- ---------------------------------------------------------------------------
CREATE TABLE projects (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    name         VARCHAR(255) NOT NULL,
    slug         VARCHAR(100) NOT NULL,
    description  TEXT NULL,
    project_type VARCHAR(50) NOT NULL DEFAULT 'mixed' COMMENT 'yaml | terraform | mixed',
    owner_id     INT UNSIGNED NOT NULL,
    team_id      INT UNSIGNED NULL,
    is_active    TINYINT(1) NOT NULL DEFAULT 1,
    settings     JSON NULL,
    created_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    KEY idx_projects_slug (slug),
    KEY idx_projects_owner_id (owner_id),
    KEY idx_projects_team_id (team_id),
    CONSTRAINT fk_projects_owner FOREIGN KEY (owner_id) REFERENCES users(id),
    CONSTRAINT fk_projects_team FOREIGN KEY (team_id) REFERENCES teams(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- repositories — GitHub-linked repos
-- ---------------------------------------------------------------------------
CREATE TABLE repositories (
    id              INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    project_id      INT UNSIGNED NOT NULL,
    name            VARCHAR(255) NOT NULL,
    full_name       VARCHAR(500) NOT NULL COMMENT 'org/repo',
    github_repo_id  INT NULL,
    default_branch  VARCHAR(100) NOT NULL DEFAULT 'main',
    clone_url       VARCHAR(500) NULL,
    webhook_id      INT NULL,
    auto_scan       TINYINT(1) NOT NULL DEFAULT 1,
    last_synced_at  DATETIME(6) NULL,
    created_at      DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_repositories_project_id (project_id),
    KEY idx_repositories_full_name (full_name(191)),
    CONSTRAINT fk_repositories_project FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- validation_history — each validation run
-- ---------------------------------------------------------------------------
CREATE TABLE validation_history (
    id                      INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    project_id              INT UNSIGNED NULL COMMENT 'NULL for anonymous/public validations',
    repository_id           INT UNSIGNED NULL,
    user_id                 INT UNSIGNED NOT NULL,
    validation_type         VARCHAR(50) NOT NULL COMMENT 'yaml | terraform | security | auto',
    status                  ENUM('pending','running','success','failed','warning') NOT NULL DEFAULT 'pending',
    branch                  VARCHAR(255) NULL,
    commit_sha              VARCHAR(40) NULL,
    commit_message          TEXT NULL,
    pull_request_number     INT NULL,
    duration_ms             INT NULL,
    error_count             INT NOT NULL DEFAULT 0,
    warning_count           INT NOT NULL DEFAULT 0,
    security_findings_count INT NOT NULL DEFAULT 0,
    summary                 TEXT NULL,
    created_at              DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_validation_history_user_id (user_id),
    KEY idx_validation_history_project_id (project_id),
    KEY idx_validation_history_repository_id (repository_id),
    KEY idx_validation_history_status (status),
    KEY idx_validation_history_created_at (created_at),
    KEY idx_validation_history_type (validation_type),
    CONSTRAINT fk_validation_history_project FOREIGN KEY (project_id) REFERENCES projects(id),
    CONSTRAINT fk_validation_history_repository FOREIGN KEY (repository_id) REFERENCES repositories(id),
    CONSTRAINT fk_validation_history_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- validation_results — individual findings per run
-- ---------------------------------------------------------------------------
CREATE TABLE validation_results (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    validation_id     INT UNSIGNED NOT NULL,
    file_path         VARCHAR(500) NOT NULL,
    line_number       INT NULL,
    column_number     INT NULL,
    rule_id           VARCHAR(100) NULL,
    severity          ENUM('critical','high','medium','low','informational') NOT NULL DEFAULT 'informational',
    category          VARCHAR(100) NOT NULL,
    message           TEXT NOT NULL,
    original_code     TEXT NULL,
    corrected_code    TEXT NULL,
    correction_reason TEXT NULL,
    impact            TEXT NULL,
    is_fixed          TINYINT(1) NOT NULL DEFAULT 0,
    extra_data        JSON NULL,
    created_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_validation_results_validation_id (validation_id),
    KEY idx_validation_results_severity (severity),
    KEY idx_validation_results_category (category),
    CONSTRAINT fk_validation_results_validation FOREIGN KEY (validation_id) REFERENCES validation_history(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- ai_explanations — line-by-line AI analysis
-- ---------------------------------------------------------------------------
CREATE TABLE ai_explanations (
    id             INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    validation_id  INT UNSIGNED NOT NULL,
    file_path      VARCHAR(500) NOT NULL,
    line_number    INT NOT NULL,
    code           TEXT NOT NULL,
    explanation    TEXT NOT NULL,
    risk_level     ENUM('critical','high','medium','low','informational') NOT NULL DEFAULT 'informational',
    recommendation TEXT NULL,
    language       VARCHAR(20) NOT NULL DEFAULT 'yaml',
    ai_model       VARCHAR(100) NULL,
    tokens_used    INT NULL,
    created_at     DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_ai_explanations_validation_id (validation_id),
    KEY idx_ai_explanations_line (validation_id, line_number),
    CONSTRAINT fk_ai_explanations_validation FOREIGN KEY (validation_id) REFERENCES validation_history(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- security_scans — Checkov, tfsec, Trivy, Semgrep results
-- ---------------------------------------------------------------------------
CREATE TABLE security_scans (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    validation_id INT UNSIGNED NOT NULL,
    scanner       VARCHAR(50) NOT NULL COMMENT 'checkov | tfsec | trivy | semgrep | static_patterns',
    rule_id       VARCHAR(100) NOT NULL,
    severity      ENUM('critical','high','medium','low','informational') NOT NULL,
    title         VARCHAR(500) NOT NULL,
    description   TEXT NULL,
    file_path     VARCHAR(500) NOT NULL,
    line_number   INT NULL,
    resource      VARCHAR(255) NULL,
    remediation   TEXT NULL,
    cwe_id        VARCHAR(20) NULL,
    extra_data    JSON NULL,
    created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_security_scans_validation_id (validation_id),
    KEY idx_security_scans_severity (severity),
    KEY idx_security_scans_scanner (scanner),
    CONSTRAINT fk_security_scans_validation FOREIGN KEY (validation_id) REFERENCES validation_history(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- terraform_modules — tracked TF modules in repos
-- ---------------------------------------------------------------------------
CREATE TABLE terraform_modules (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    repository_id     INT UNSIGNED NOT NULL,
    name              VARCHAR(255) NOT NULL,
    path              VARCHAR(500) NOT NULL,
    source            VARCHAR(500) NULL,
    version           VARCHAR(50) NULL,
    providers         JSON NULL,
    variables         JSON NULL,
    outputs           JSON NULL,
    resources_count   INT NOT NULL DEFAULT 0,
    estimated_cost    DOUBLE NULL,
    dependency_graph  JSON NULL,
    last_validated_at DATETIME(6) NULL,
    created_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_terraform_modules_repository_id (repository_id),
    CONSTRAINT fk_terraform_modules_repository FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- yaml_files — tracked YAML files in repos
-- ---------------------------------------------------------------------------
CREATE TABLE yaml_files (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    repository_id     INT UNSIGNED NOT NULL,
    file_path         VARCHAR(500) NOT NULL,
    file_type         VARCHAR(50) NOT NULL DEFAULT 'generic' COMMENT 'k8s | helm | compose | gha | gitlab_ci',
    content_hash      VARCHAR(64) NULL COMMENT 'SHA-256 hex',
    line_count        INT NOT NULL DEFAULT 0,
    schema_valid      TINYINT(1) NULL,
    last_validated_at DATETIME(6) NULL,
    created_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_yaml_files_repository_id (repository_id),
    KEY idx_yaml_files_file_type (file_type),
    CONSTRAINT fk_yaml_files_repository FOREIGN KEY (repository_id) REFERENCES repositories(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- audit_logs — enterprise audit trail
-- ---------------------------------------------------------------------------
CREATE TABLE audit_logs (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id       INT UNSIGNED NULL,
    action        VARCHAR(100) NOT NULL,
    resource_type VARCHAR(50) NOT NULL,
    resource_id   VARCHAR(100) NULL,
    ip_address    VARCHAR(45) NULL,
    user_agent    VARCHAR(500) NULL,
    details       JSON NULL,
    created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_audit_logs_user_id (user_id),
    KEY idx_audit_logs_action (action),
    KEY idx_audit_logs_created_at (created_at),
    CONSTRAINT fk_audit_logs_user FOREIGN KEY (user_id) REFERENCES users(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- settings — key-value configuration (global / user / team scope)
-- ---------------------------------------------------------------------------
CREATE TABLE settings (
    id          INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    `key`       VARCHAR(255) NOT NULL,
    value       TEXT NOT NULL,
    value_type  VARCHAR(20) NOT NULL DEFAULT 'string',
    scope       VARCHAR(50) NOT NULL DEFAULT 'global' COMMENT 'global | user | team',
    scope_id    INT UNSIGNED NULL,
    description VARCHAR(500) NULL,
    is_secret   TINYINT(1) NOT NULL DEFAULT 0,
    created_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    updated_at  DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),

    UNIQUE KEY uq_settings_key_scope (`key`, scope, scope_id),
    KEY idx_settings_scope (scope, scope_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- notifications — email, slack, telegram, in-app
-- ---------------------------------------------------------------------------
CREATE TABLE notifications (
    id                INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id           INT UNSIGNED NOT NULL,
    title             VARCHAR(255) NOT NULL,
    message           TEXT NOT NULL,
    notification_type VARCHAR(50) NOT NULL DEFAULT 'info',
    channel           VARCHAR(50) NOT NULL DEFAULT 'in_app' COMMENT 'email | slack | telegram | webhook | in_app',
    is_read           TINYINT(1) NOT NULL DEFAULT 0,
    link              VARCHAR(500) NULL,
    extra_data        JSON NULL,
    sent_at           DATETIME(6) NULL,
    created_at        DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_notifications_user_id (user_id),
    KEY idx_notifications_is_read (user_id, is_read),
    CONSTRAINT fk_notifications_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- api_keys — programmatic API access
-- ---------------------------------------------------------------------------
CREATE TABLE api_keys (
    id           INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id      INT UNSIGNED NOT NULL,
    name         VARCHAR(255) NOT NULL,
    key_prefix   VARCHAR(20) NOT NULL,
    hashed_key   VARCHAR(255) NOT NULL,
    scopes       JSON NULL,
    rate_limit   INT NOT NULL DEFAULT 1000,
    last_used_at DATETIME(6) NULL,
    expires_at   DATETIME(6) NULL,
    is_active    TINYINT(1) NOT NULL DEFAULT 1,
    created_at   DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_api_keys_user_id (user_id),
    KEY idx_api_keys_prefix (key_prefix),
    CONSTRAINT fk_api_keys_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ---------------------------------------------------------------------------
-- activity_feed — dashboard team activity widget
-- ---------------------------------------------------------------------------
CREATE TABLE activity_feed (
    id            INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    user_id       INT UNSIGNED NOT NULL,
    team_id       INT UNSIGNED NULL,
    activity_type VARCHAR(50) NOT NULL,
    title         VARCHAR(255) NOT NULL,
    description   TEXT NULL,
    resource_type VARCHAR(50) NULL,
    resource_id   INT UNSIGNED NULL,
    extra_data    JSON NULL,
    created_at    DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),

    KEY idx_activity_feed_user_id (user_id),
    KEY idx_activity_feed_team_id (team_id),
    KEY idx_activity_feed_created_at (created_at),
    CONSTRAINT fk_activity_feed_user FOREIGN KEY (user_id) REFERENCES users(id),
    CONSTRAINT fk_activity_feed_team FOREIGN KEY (team_id) REFERENCES teams(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- =============================================================================
-- SEED DATA
-- =============================================================================

-- Default RBAC roles
INSERT INTO roles (name, description) VALUES
    ('admin',     'Full platform access'),
    ('manager',   'Team and project management'),
    ('developer', 'Create and run validations'),
    ('viewer',    'Read-only access');

-- Default permissions
INSERT INTO permissions (name, resource, action, description) VALUES
    ('validation:create', 'validation', 'create', 'Run validations'),
    ('validation:read',     'validation', 'read',   'View validation results'),
    ('validation:delete',   'validation', 'delete', 'Delete validation history'),
    ('project:create',      'project',    'create', 'Create projects'),
    ('project:read',        'project',    'read',   'View projects'),
    ('project:update',      'project',    'update', 'Update projects'),
    ('project:delete',      'project',    'delete', 'Delete projects'),
    ('team:manage',         'team',       'manage', 'Manage team members'),
    ('user:manage',         'user',       'manage', 'Manage users'),
    ('settings:manage',     'settings',   'manage', 'Manage platform settings');

-- Admin gets all permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r CROSS JOIN permissions p WHERE r.name = 'admin';

-- Developer permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
WHERE r.name = 'developer'
  AND p.name IN ('validation:create','validation:read','project:create','project:read','project:update');

-- Viewer permissions
INSERT INTO role_permissions (role_id, permission_id)
SELECT r.id, p.id FROM roles r JOIN permissions p
WHERE r.name = 'viewer'
  AND p.name IN ('validation:read','project:read');

-- Guest user for public (no-login) access
-- Password hash is bcrypt placeholder; not used for public access
INSERT INTO users (email, username, hashed_password, full_name, is_active, is_verified, preferred_language)
VALUES (
    'guest@local',
    'guest',
    '$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4.G2oX4.G2oX4.G2o',
    'Guest',
    1,
    1,
    'en'
);

-- Assign developer role to guest
INSERT INTO user_roles (user_id, role_id)
SELECT u.id, r.id FROM users u JOIN roles r ON r.name = 'developer' WHERE u.username = 'guest';

-- Global platform settings
INSERT INTO settings (`key`, value, value_type, scope, description) VALUES
    ('app.name',              'YAML & Terraform AI Validator', 'string', 'global', 'Application display name'),
    ('validation.max_size_mb','50',                            'integer','global', 'Max upload size in MB'),
    ('ai.enabled',            'true',                          'boolean','global', 'Enable AI analysis'),
    ('security.scan_enabled', 'true',                          'boolean','global', 'Enable security scanning'),
    ('retention.days',        '90',                            'integer','global', 'Validation history retention days');

-- =============================================================================
-- USEFUL QUERIES (examples)
-- =============================================================================

-- Recent validations with error counts:
-- SELECT vh.id, vh.validation_type, vh.status, vh.error_count, vh.created_at, u.username
-- FROM validation_history vh
-- JOIN users u ON u.id = vh.user_id
-- ORDER BY vh.created_at DESC LIMIT 20;

-- Critical security findings:
-- SELECT ss.title, ss.file_path, ss.line_number, ss.scanner, vh.created_at
-- FROM security_scans ss
-- JOIN validation_history vh ON vh.id = ss.validation_id
-- WHERE ss.severity = 'critical'
-- ORDER BY ss.created_at DESC;

-- Validation stats per day:
-- SELECT DATE(created_at) AS day, COUNT(*) AS total,
--        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) AS failed
-- FROM validation_history
-- GROUP BY DATE(created_at)
-- ORDER BY day DESC;
