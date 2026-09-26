"""FastAPI dependencies. Routes obtain everything through these, never a module singleton."""

from fastapi import Request

from app.config import Settings


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings
