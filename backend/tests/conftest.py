"""Unit-test app: the real app factory, real routes and services, with every port replaced by
an in-memory fake. Nothing here opens a socket."""

from dataclasses import dataclass

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.enums import TriagedBy
from app.main import create_app
from app.providers.triage.base import TriageProvider
from app.providers.triage.pipeline import TriagePipeline
from app.services.complaints import ComplaintService
from app.services.meta import ProvidersService
from app.services.readiness import ReadinessService
from app.services.stats import StatsService
from tests.fakes import (
    FakeRateLimiter,
    InMemoryStore,
    MemoryOutcomes,
    MemoryStatsCache,
    MemoryTriageCache,
)


@dataclass
class Fakes:
    store: InMemoryStore
    stats_cache: MemoryStatsCache
    triage_cache: MemoryTriageCache
    outcomes: MemoryOutcomes
    limiter: FakeRateLimiter


async def _ok() -> None:
    return None


def install_fakes(app: FastAPI, fakes: Fakes, provider: TriageProvider | None = None) -> None:
    settings: Settings = app.state.settings
    provider = provider or app.state.triage_provider
    pipeline = TriagePipeline(
        provider,
        fakes.triage_cache,
        fakes.outcomes,
        timeout_seconds=settings.triage_timeout_seconds,
        prompt_version=settings.prompt_version,
    )
    app.state.triage_provider = provider
    app.state.triage_pipeline = pipeline
    app.state.rate_limiter = fakes.limiter
    app.state.complaint_service = ComplaintService(fakes.store, pipeline, fakes.stats_cache)
    app.state.stats_service = StatsService(fakes.store, fakes.stats_cache)
    app.state.providers_service = ProvidersService(
        settings.triage_provider, TriagedBy(provider.name), fakes.outcomes
    )
    app.state.readiness_service = ReadinessService({"database": _ok, "cache": _ok}, 1)


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url="postgresql+asyncpg://u@database/db", redis_url="redis://cache")


@pytest.fixture
def fakes() -> Fakes:
    return Fakes(
        InMemoryStore(),
        MemoryStatsCache(),
        MemoryTriageCache(),
        MemoryOutcomes(),
        FakeRateLimiter(),
    )


@pytest.fixture
def limiter(fakes: Fakes) -> FakeRateLimiter:
    return fakes.limiter


@pytest.fixture
def app(settings: Settings, fakes: Fakes) -> FastAPI:
    app = create_app(settings)
    install_fakes(app, fakes)
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
