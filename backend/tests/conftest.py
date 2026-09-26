import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.errors import RateLimitExceededError
from app.main import create_app


class FakeRateLimiter:
    """In-memory stand-in for the port: unit tests never touch Redis."""

    def __init__(self) -> None:
        self.seen: list[str] = []
        self.retry_after: int | None = None  # set to make every check a 429

    async def check(self, client_ip: str) -> None:
        self.seen.append(client_ip)
        if self.retry_after is not None:
            raise RateLimitExceededError(self.retry_after)


@pytest.fixture
def settings() -> Settings:
    return Settings(database_url="postgresql+asyncpg://u@database/db", redis_url="redis://cache")


@pytest.fixture
def limiter() -> FakeRateLimiter:
    return FakeRateLimiter()


@pytest.fixture
def app(settings: Settings, limiter: FakeRateLimiter) -> FastAPI:
    app = create_app(settings)
    app.state.rate_limiter = limiter
    return app


@pytest.fixture
def client(app: FastAPI) -> TestClient:
    return TestClient(app, raise_server_exceptions=False)
