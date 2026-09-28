"""App factory. Run with: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000"""

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.config import Settings, load_settings
from app.db.session import make_engine, make_session_factory
from app.domain.enums import TriagedBy
from app.errors import register_error_handlers
from app.observability import metrics
from app.observability.cors import (
    ALLOWED_HEADERS,
    ALLOWED_METHODS,
    EXPOSED_HEADERS,
    ContractCORSMiddleware,
)
from app.observability.logging import configure_logging, get_logger
from app.observability.middleware import RequestMiddleware
from app.providers.cache.client import make_redis, ping
from app.providers.cache.outcomes import RedisOutcomes
from app.providers.cache.ratelimit import RedisRateLimiter
from app.providers.cache.stats import RedisStatsCache
from app.providers.cache.triage import RedisTriageCache
from app.providers.triage.factory import build_triage_provider
from app.providers.triage.pipeline import TriagePipeline
from app.repositories.complaints import ComplaintRepository
from app.repositories.health import ping_database
from app.routes import complaints, meta, ops, stats
from app.services.complaints import ComplaintService
from app.services.meta import ProvidersService
from app.services.readiness import ReadinessService
from app.services.stats import StatsService

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Startup verifies nothing and migrates nothing (BR-DATA-001). On SIGTERM, uvicorn stops
    accepting connections and drains in-flight requests before this shutdown half runs, which
    then closes the pools (FR-BE-021). Exec-form CMD is what makes the signal arrive at all."""
    yield
    log.info("shutdown.started")
    await app.state.engine.dispose()
    await app.state.redis.aclose()
    close_provider = getattr(app.state.triage_provider, "aclose", None)
    if close_provider is not None:  # HTTP-backed providers hold a connection pool
        await close_provider()
    log.info("shutdown.completed")


def _openapi_without_422(app: FastAPI) -> Callable[[], dict[str, Any]]:
    """FastAPI documents a 422 on every route with parameters, but the error handler turns every
    validation failure into a 400 with the one envelope (FR-BE-002). Document what is sent:
    drop the 422s and the schemas only they used; routes declare their real errors."""

    def openapi() -> dict[str, Any]:
        if app.openapi_schema is None:
            schema = get_openapi(title=app.title, version=app.version, routes=app.routes)
            for operations in schema["paths"].values():
                for operation in operations.values():
                    operation["responses"].pop("422", None)
            for unused in ("HTTPValidationError", "ValidationError"):
                schema["components"]["schemas"].pop(unused, None)
            app.openapi_schema = schema
        return app.openapi_schema

    return openapi


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="Civic-Station", version=settings.app_version, lifespan=lifespan)
    app.state.settings = settings

    # All three connect lazily: nothing is opened until the first request needs it.
    engine = make_engine(settings.database_url)
    session_factory = make_session_factory(engine)
    redis = make_redis(settings.redis_url)
    app.state.engine, app.state.session_factory, app.state.redis = engine, session_factory, redis

    provider = build_triage_provider(settings)  # resolution failure = no boot
    outcomes = RedisOutcomes(redis, settings.prompt_version)
    pipeline = TriagePipeline(
        provider,
        RedisTriageCache(redis, settings.triage_cache_ttl_seconds),
        outcomes,
        timeout_seconds=settings.triage_timeout_seconds,
        prompt_version=settings.prompt_version,
    )
    store = ComplaintRepository(session_factory)
    stats_cache = RedisStatsCache(redis, settings.stats_cache_ttl_seconds)

    app.state.triage_provider = provider
    app.state.triage_pipeline = pipeline
    app.state.rate_limiter = RedisRateLimiter(
        redis, settings.rate_limit_requests, settings.rate_limit_window_seconds
    )
    app.state.complaint_service = ComplaintService(store, pipeline, stats_cache)
    app.state.stats_service = StatsService(store, stats_cache)
    app.state.providers_service = ProvidersService(
        settings.triage_provider, TriagedBy(provider.name), outcomes
    )
    app.state.readiness_service = ReadinessService(
        {
            "database": lambda: ping_database(app.state.session_factory),
            "cache": lambda: ping(app.state.redis),
        },
        settings.readiness_timeout_seconds,
    )

    for router in (complaints.router, stats.router, meta.router, ops.router, metrics.router):
        app.include_router(router)
    register_error_handlers(app)
    app.openapi = _openapi_without_422(app)  # type: ignore[method-assign]
    # add_middleware prepends: the last one added is the outermost. CORS must be outermost.
    app.add_middleware(RequestMiddleware)
    app.add_middleware(
        ContractCORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=ALLOWED_METHODS,
        allow_headers=ALLOWED_HEADERS,
        expose_headers=EXPOSED_HEADERS,
    )
    return app
