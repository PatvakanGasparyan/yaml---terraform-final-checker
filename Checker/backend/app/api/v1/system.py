"""Public system configuration (non-sensitive)."""

from fastapi import APIRouter

from app.core.config import get_settings
from app.plugins.registry import get_plugin_registry

router = APIRouter(prefix="/system", tags=["System"])
settings = get_settings()


@router.get("/config")
async def get_system_config() -> dict:
    """Return public system configuration for the frontend."""
    ai_configured = bool(
        (settings.AI_PROVIDER == "openai" and settings.OPENAI_API_KEY)
        or (settings.AI_PROVIDER == "azure" and settings.AZURE_OPENAI_API_KEY)
        or settings.AI_PROVIDER in ("ollama", "local")
    )
    model = settings.OPENAI_MODEL
    if settings.AI_PROVIDER == "azure":
        model = settings.AZURE_OPENAI_DEPLOYMENT
    elif settings.AI_PROVIDER in ("ollama", "local"):
        model = settings.OLLAMA_MODEL

    return {
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "ai": {
            "provider": settings.AI_PROVIDER,
            "model": model,
            "configured": ai_configured,
            "temperature": settings.AI_TEMPERATURE,
            "max_tokens": settings.AI_MAX_TOKENS,
            "timeout_seconds": settings.AI_TIMEOUT_SECONDS,
            "max_retries": settings.AI_MAX_RETRIES,
            "custom_prompt": bool(settings.AI_SYSTEM_PROMPT.strip()),
        },
        "cache": {
            "enabled": settings.VALIDATION_CACHE_ENABLED,
            "ttl_seconds": settings.VALIDATION_CACHE_TTL,
        },
        "plugins": get_plugin_registry().list_plugins(),
    }


@router.get("/plugins")
async def list_plugins() -> list[dict]:
    """List registered validator plugins."""
    return get_plugin_registry().list_plugins()
