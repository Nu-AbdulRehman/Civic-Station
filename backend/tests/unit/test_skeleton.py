import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

CONTRACT_PATHS = {
    "/api/complaints": {"post", "get"},
    "/api/complaints/{complaint_id}": {"get"},
    "/api/complaints/{complaint_id}/status": {"patch"},
    "/api/stats": {"get"},
    "/api/meta/providers": {"get"},
    "/api/version": {"get"},
    "/health": {"get"},
    "/ready": {"get"},
    "/metrics": {"get"},
}


@pytest.fixture
def client() -> TestClient:
    settings = Settings(
        database_url="postgresql+asyncpg://u@database/db", redis_url="redis://cache"
    )
    return TestClient(create_app(settings))


def test_openapi_lists_every_contract_endpoint(client: TestClient) -> None:
    paths = client.get("/openapi.json").json()["paths"]
    assert {p: set(ops) for p, ops in paths.items()} == CONTRACT_PATHS


def test_health_and_ready(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/ready").json()["checks"] == {"database": "ok", "cache": "ok"}


def test_create_stub_returns_201_with_location(client: TestClient) -> None:
    r = client.post("/api/complaints", json={"text": "Water pipe burst", "location": "G-9"})
    assert r.status_code == 201
    assert r.headers["Location"] == f"/api/complaints/{r.json()['id']}"
