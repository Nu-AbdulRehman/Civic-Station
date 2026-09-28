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


def test_create_returns_201_with_location(client: TestClient) -> None:
    r = client.post("/api/complaints", json={"text": "Water pipe burst", "location": "G-9"})
    assert r.status_code == 201
    assert r.headers["Location"] == f"/api/complaints/{r.json()['id']}"


EXPECTED_ERRORS = {
    ("post", "/api/complaints"): {"400", "413", "415", "429"},
    ("get", "/api/complaints"): {"400"},
    ("get", "/api/complaints/{id}"): {"400", "404"},
    ("patch", "/api/complaints/{id}/status"): {"400", "404", "409", "413", "415"},
}


def test_openapi_documents_the_errors_actually_sent(client: TestClient) -> None:
    """No FastAPI-default 422 anywhere: validation is a 400 in the one envelope (FR-BE-002), and
    the generated frontend types must describe that (FR-FE-012)."""
    schema = client.get("/openapi.json").json()
    assert '"422"' not in client.get("/openapi.json").text
    assert "HTTPValidationError" not in schema["components"]["schemas"]
    envelope = {"$ref": "#/components/schemas/ErrorResponse"}
    for (method, path), codes in EXPECTED_ERRORS.items():
        responses = schema["paths"][path][method]["responses"]
        assert {c for c in responses if c.startswith(("4", "5"))} == codes, (method, path)
        for code in codes:
            assert responses[code]["content"]["application/json"]["schema"] == envelope
    post = schema["paths"]["/api/complaints"]["post"]["responses"]
    assert "Retry-After" in post["429"]["headers"] and "Location" in post["201"]["headers"]
    ready = schema["paths"]["/ready"]["get"]["responses"]["503"]
    assert ready["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/ReadinessFailure"
    }
