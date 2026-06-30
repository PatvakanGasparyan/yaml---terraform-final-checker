"""
Application configuration module.

All configuration is loaded exclusively from the .env file.
On EC2 the file is fetched from S3 before startup (see app.core.env_loader).
"""

from functools import lru_cache
from typing import Literal

from pydantic import Field, computed_field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

from app.core.env_loader import ensure_env_file

ENV_FILE_PATH = ensure_env_file()


class Settings(BaseSettings):
    """
    Central configuration class for the YAML & Terraform AI Validator platform.

    Values are read only from the .env file — not from the process environment.
    """

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE_PATH),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Load settings from .env file only (ignore os.environ)."""
        return (dotenv_settings, init_settings)

    # Application metadata
    APP_NAME: str = "YAML & Terraform AI Validator"
    APP_VERSION: str = "1.0.0"
    APP_ENV: Literal["development", "staging", "production"] = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4

    # Security - JWT
    SECRET_KEY: str = Field(
        default="change-me-in-production-use-openssl-rand-hex-32",
        description="JWT signing secret key",
    )
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Database
    DB_ENGINE: Literal["sqlite", "mysql"] = "mysql"
    SQLITE_PATH: str = "/app/data/app.db"
    MYSQL_HOST: str = "mysql"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "validator"
    MYSQL_PASSWORD: str = "validator_secret"
    MYSQL_DATABASE: str = "yaml_terraform_validator"
    DATABASE_POOL_SIZE: int = 20
    DATABASE_MAX_OVERFLOW: int = 10

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL(self) -> str:
        """Build async database URL for SQLAlchemy."""
        if self.DB_ENGINE == "sqlite":
            path = self.SQLITE_PATH
            if path.startswith("/"):
                return f"sqlite+aiosqlite:///{path}"
            return f"sqlite+aiosqlite:///{path}"
        return (
            f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """Build sync MySQL connection URL for Alembic migrations."""
        return (
            f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DATABASE}"
        )

    # Redis & Celery
    REDIS_HOST: str = "redis"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0

    @computed_field  # type: ignore[prop-decorator]
    @property
    def redis_enabled(self) -> bool:
        """Redis is optional (disabled for minimal EC2 deploy)."""
        return bool(self.REDIS_HOST and self.REDIS_HOST not in ("disabled", "none", "skip"))

    CELERY_BROKER_URL: str = ""
    CELERY_RESULT_BACKEND: str = ""

    def model_post_init(self, __context: object) -> None:
        """Set Celery URLs from Redis when Redis is enabled."""
        if not self.redis_enabled:
            return
        redis_url = f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"
        if not self.CELERY_BROKER_URL:
            object.__setattr__(self, "CELERY_BROKER_URL", redis_url)
        if not self.CELERY_RESULT_BACKEND:
            object.__setattr__(self, "CELERY_RESULT_BACKEND", redis_url)

    # AI / LLM Configuration
    AI_PROVIDER: Literal["openai", "azure", "ollama", "local"] = "openai"
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    AZURE_OPENAI_ENDPOINT: str = ""
    AZURE_OPENAI_API_KEY: str = ""
    AZURE_OPENAI_DEPLOYMENT: str = "gpt-4o"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_MODEL: str = "llama3.3"
    AI_TEMPERATURE: float = 0.2
    AI_MAX_TOKENS: int = 8192
    AI_TOP_P: float = 0.95
    AI_SYSTEM_PROMPT: str = ""

    # GitHub OAuth
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_CALLBACK_URL: str = "http://localhost:3000/api/auth/github/callback"
    GITHUB_WEBHOOK_SECRET: str = "github-webhook-secret-change-me"

    # Email
    SMTP_HOST: str = "mailhog"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "noreply@yaml-validator.local"
    EMAIL_ENABLED: bool = False

    # Notifications
    SLACK_WEBHOOK_URL: str = ""
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_CHAT_ID: str = ""

    # Rate limiting
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_BURST: int = 100

    # CORS
    CORS_ORIGINS: str = "http://localhost:3000,http://frontend:3000"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # OpenTelemetry
    OTEL_ENABLED: bool = False
    OTEL_SERVICE_NAME: str = "yaml-terraform-validator-api"
    OTEL_EXPORTER_ENDPOINT: str = "http://otel-collector:4317"

    # Frontend URL
    FRONTEND_URL: str = "http://localhost:3000"

    # File upload limits
    MAX_UPLOAD_SIZE_MB: int = 50
    ALLOWED_EXTENSIONS: str = ".yaml,.yml,.tf,.tfvars,.hcl,.json"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def allowed_extensions_list(self) -> list[str]:
        """Parse allowed file extensions."""
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",") if ext.strip()]


@lru_cache
def get_settings() -> Settings:
    """Return cached Settings singleton loaded from .env only."""
    return Settings()
