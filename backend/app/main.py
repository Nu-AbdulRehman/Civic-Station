"""App factory. Run with: uvicorn app.main:create_app --factory --host 0.0.0.0 --port 8000"""

from fastapi import FastAPI

from app.config import Settings, load_settings
from app.routes import complaints, meta, ops, stats


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="Civic-Station", version=settings.app_version)
    app.state.settings = settings
    for module in (complaints, stats, meta, ops):
        app.include_router(module.router)
    return app
