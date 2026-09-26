"""FastAPI dependencies. Routes obtain everything through these, never a module singleton."""

from fastapi import Request

from app.client_ip import resolve_client_ip
from app.config import Settings
from app.providers.cache.ports import RateLimiterPort
from app.providers.triage.base import TriageProvider


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_triage_provider(request: Request) -> TriageProvider:
    provider: TriageProvider = request.app.state.triage_provider
    return provider


def client_ip(request: Request) -> str:
    settings = get_settings(request)
    peer = request.client.host if request.client else None
    forwarded = request.headers.get("x-forwarded-for")
    return resolve_client_ip(peer, forwarded, settings.trusted_proxy_networks)


async def enforce_rate_limit(request: Request) -> None:
    """Route dependency on POST /api/complaints only. FastAPI resolves dependencies before it
    validates the body, so a 429 costs no validation, no inference and no row (BR-CACHE-006)."""
    limiter: RateLimiterPort = request.app.state.rate_limiter
    await limiter.check(client_ip(request))
