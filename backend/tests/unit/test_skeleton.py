from fastapi.testclient import TestClient

CONTRACT_PATHS = {
    "/api/complaints": {"post", "get"},
    "/api/complaints/{id}": {"get"},
    "/api/complaints/{id}/status": {"patch"},
    "/api/stats": {"get"},
    "/api/meta/providers": {"get"},
    "/api/version": {"get"},
    "/health": {"get"},
    "/ready": {"get"},
    "/metrics": {"get"},
}


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
