"""App factory. Run with: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000"""

from fastapi import FastAPI

from app.config import Settings, load_settings
from app.errors import register_error_handlers
from app.observability import metrics
from app.observability.logging import configure_logging
from app.observability.middleware import RequestMiddleware
from app.routes import complaints, meta, ops, stats


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    configure_logging(settings.log_level)
    app = FastAPI(title="Civic-Station", version=settings.app_version)
    app.state.settings = settings
    for router in (complaints.router, stats.router, meta.router, ops.router, metrics.router):
        app.include_router(router)
    register_error_handlers(app)
    # Added last = outermost. CORS (T-M2-013) is added after this so it wraps it.
    app.add_middleware(RequestMiddleware)
    return app
