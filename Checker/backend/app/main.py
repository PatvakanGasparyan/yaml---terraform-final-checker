"""
FastAPI application entry point.

Initializes the YAML & Terraform AI Validator API with middleware,
OpenTelemetry, rate limiting, CORS, and route registration.
"""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import text
from starlette.responses import Response

from app.api.deps import get_guest_user
from app.api.v1 import api_router
from app.core.config import get_settings
from app.core.database import AsyncSessionLocal, engine, init_db
from app.core.limiter import limiter
from app.logging.setup import setup_logging
from app.schemas import HealthResponse
from app.services.auth_service import AuthService

settings = get_settings()
logger = logging.getLogger(__name__)

# Prometheus metrics
REQUEST_COUNT = Counter("http_requests_total", "Total HTTP requests", ["method", "endpoint", "status"])
REQUEST_LATENCY = Histogram("http_request_duration_seconds", "HTTP request latency")

limiter.default_limits = [f"{settings.RATE_LIMIT_PER_MINUTE}/minute"]


def setup_opentelemetry() -> None:
    """Configure OpenTelemetry tracing if enabled."""
    if not settings.OTEL_ENABLED:
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        resource = Resource.create({"service.name": settings.OTEL_SERVICE_NAME})
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=settings.OTEL_EXPORTER_ENDPOINT, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)

        SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine if hasattr(engine, 'sync_engine') else None)

        logger.info("OpenTelemetry configured")
    except Exception as e:
        logger.warning(f"OpenTelemetry setup failed: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Runs startup tasks (DB init, role seeding) and cleanup on shutdown.
    """
    logger = logging.getLogger(__name__)
    setup_logging(level=settings.LOG_LEVEL, json_format=settings.LOG_JSON)
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(
        "Runtime config: DB_ENGINE=%s SQLITE_PATH=%s REDIS_HOST=%s",
        settings.DB_ENGINE,
        settings.SQLITE_PATH,
        settings.REDIS_HOST,
    )

    try:
        await init_db()

        async with AsyncSessionLocal() as session:
            auth_service = AuthService(session)
            await auth_service.seed_default_roles()
            await get_guest_user(session)
            await session.commit()
    except Exception:
        logger.exception("Application startup failed during database initialization")
        raise

    setup_opentelemetry()
    logger.info("Application startup complete")

    yield

    logger.info("Application shutting down")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Enterprise YAML & Terraform AI Validator SaaS Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    lifespan=lifespan,
)

# Middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def metrics_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
    """Record request metrics for Prometheus."""
    import time

    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code,
    ).inc()
    REQUEST_LATENCY.observe(duration)

    return response


# Routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check() -> HealthResponse:
    """
    Health check endpoint for load balancers and Docker.

    Checks database and Redis connectivity.
    """
    db_status = "healthy"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
    except Exception:
        db_status = "unhealthy"

    redis_status = "skipped"
    if settings.redis_enabled:
        redis_status = "healthy"
        try:
            import redis

            r = redis.from_url(
                f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/{settings.REDIS_DB}"
            )
            r.ping()
        except Exception:
            redis_status = "unhealthy"

    db_required = db_status == "healthy"
    redis_required = settings.redis_enabled and redis_status != "healthy"
    overall = "healthy" if db_required and not redis_required else "degraded"

    return HealthResponse(
        status=overall,
        version=settings.APP_VERSION,
        database=db_status,
        redis=redis_status,
        celery="unknown",
    )


@app.get("/metrics", tags=["Monitoring"])
async def metrics() -> Response:
    """Prometheus metrics endpoint."""
    return Response(content=generate_latest(), media_type="text/plain")


@app.get("/", tags=["Root"])
async def root() -> JSONResponse:
    """API root with version info."""
    return JSONResponse({
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "health": "/health",
    })
