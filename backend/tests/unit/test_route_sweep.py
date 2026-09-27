"""FR-BE-011 (b): no route acquires a database session outside the service layer.

The grep in scripts/check_submission.py cannot prove this; this test can. The session factory
and engine are replaced with things that explode on use, the services run on in-memory ports,
and every route in the OpenAPI schema is called: none may produce a 500."""

from collections.abc import Callable
from typing import Any
from uuid import uuid4

import httpx2
from fastapi import FastAPI
from fastapi.testclient import TestClient

VALID = {"text": "Burst water main flooding Street 12 since fajr", "location": "Saddar"}


class Explodes:
    def __getattr__(self, name: str) -> Any:
        raise AssertionError(f"route touched the database directly ({name})")

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        raise AssertionError("route opened a session directly")


def test_every_route_works_without_touching_the_database(app: FastAPI) -> None:
    app.state.session_factory = Explodes()
    app.state.engine = Explodes()
    client = TestClient(app, raise_server_exceptions=True)
    created = client.post("/api/complaints", json=VALID)
    cid = created.json()["id"]

    calls: dict[tuple[str, str], Callable[[], httpx2.Response]] = {
        ("post", "/api/complaints"): lambda: client.post("/api/complaints", json=VALID),
        ("get", "/api/complaints"): lambda: client.get("/api/complaints"),
        ("get", "/api/complaints/{id}"): lambda: client.get(f"/api/complaints/{cid}"),
        ("patch", "/api/complaints/{id}/status"): lambda: client.patch(
            f"/api/complaints/{cid}/status", json={"status": "in_progress"}
        ),
        ("get", "/api/stats"): lambda: client.get("/api/stats"),
        ("get", "/api/meta/providers"): lambda: client.get("/api/meta/providers"),
        ("get", "/api/version"): lambda: client.get("/api/version"),
        ("get", "/ready"): lambda: client.get("/ready"),
        ("get", "/metrics"): lambda: client.get("/metrics"),
        ("get", "/health"): lambda: client.get("/health"),
    }
    documented = {
        (method, path)
        for path, ops in client.get("/openapi.json").json()["paths"].items()
        for method in ops
    }
    assert documented == set(calls), "a route was added without being swept"
    expected = {("post", "/api/complaints"): 201}
    for key, call in calls.items():
        assert call().status_code == expected.get(key, 200), key
    assert client.get(f"/api/complaints/{uuid4()}").status_code == 404
