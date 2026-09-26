"""App factory. Run with: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000"""

from fastapi import FastAPI

from app.config import Settings, load_settings
from app.errors import register_error_handlers
from app.observability import metrics
from app.observability.logging import configure_logging
from app.observability.middleware import RequestMiddleware
from app.providers.cache.client import make_redis
from app.providers.cache.ratelimit import RedisRateLimiter
from app.providers.triage.factory import build_triage_provider
from app.routes import complaints, meta, ops, stats


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="Civic-Station", version=settings.app_version)
    app.state.settings = settings
    app.state.triage_provider = build_triage_provider(settings)  # resolution failure = no boot
    # redis-py connects lazily, so building the client here opens no connection.
    # ponytail: closed in lifespan shutdown once T-M2-012 lands.
    redis = make_redis(settings.redis_url)
    app.state.redis = redis
    app.state.rate_limiter = RedisRateLimiter(
        redis, settings.rate_limit_requests, settings.rate_limit_window_seconds
    )
    for router in (complaints.router, stats.router, meta.router, ops.router, metrics.router):
        app.include_router(router)
    register_error_handlers(app)
    # Added last = outermost. CORS (T-M2-013) is added after this so it wraps it.
    app.add_middleware(RequestMiddleware)
    return app
