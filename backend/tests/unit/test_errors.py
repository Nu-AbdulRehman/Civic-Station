from typing import Any
from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.domain.enums import Status
from app.domain.errors import InvalidTransitionError, RateLimitExceededError

VALID = {"text": "Water pipe burst on main road", "location": "G-9 Markaz"}


def assert_envelope(r: httpx.Response, status: int, code: str) -> dict[str, Any]:
    """00-conventions §4: exactly `error` + `request_id`; contract test 20."""
    assert r.status_code == status
    body: dict[str, Any] = r.json()
    assert set(body) == {"error", "request_id"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    assert body["request_id"] == r.headers["x-request-id"]
    return body


def fields(body: dict[str, Any]) -> list[str]:
    return [f["field"] for f in body["error"]["fields"]]


def test_short_text_is_400_naming_text(client: TestClient) -> None:
    r = client.post("/api/complaints", json={**VALID, "text": "123456789"})
    body = assert_envelope(r, 400, "validation_error")
    assert fields(body) == ["text"]
    assert body["error"]["fields"][0]["rule"] == "string_too_short"


@pytest.mark.parametrize("extra", ["category", "priority", "status", "unknown_field"])
def test_client_supplied_field_is_400_naming_it(client: TestClient, extra: str) -> None:
    r = client.post("/api/complaints", json={**VALID, extra: "high"})
    assert fields(assert_envelope(r, 400, "validation_error")) == [extra]


def test_page_size_over_limit_is_400(client: TestClient) -> None:
    r = client.get("/api/complaints", params={"page_size": 101})
    body = assert_envelope(r, 400, "validation_error")
    assert fields(body) == ["page_size"] and "100" in body["error"]["fields"][0]["detail"]


def test_malformed_id_is_400_naming_id(client: TestClient) -> None:
    r = client.get("/api/complaints/not-a-uuid")
    assert fields(assert_envelope(r, 400, "validation_error")) == ["id"]


def test_patch_invalid_status_is_400_before_existence(client: TestClient) -> None:
    r = client.patch(f"/api/complaints/{uuid4()}/status", json={"status": "closed"})
    assert fields(assert_envelope(r, 400, "validation_error")) == ["status"]


def test_malformed_json_is_400(client: TestClient) -> None:
    r = client.post(
        "/api/complaints", content=b"{not json", headers={"content-type": "application/json"}
    )
    assert_envelope(r, 400, "validation_error")


def test_unknown_route_and_method(client: TestClient) -> None:
    assert_envelope(client.get("/api/nope"), 404, "not_found")
    assert_envelope(client.delete("/api/stats"), 405, "method_not_allowed")


def test_non_json_write_is_415(client: TestClient) -> None:
    r = client.post("/api/complaints", content=b"text", headers={"content-type": "text/plain"})
    assert_envelope(r, 415, "unsupported_media_type")


def test_oversize_body_is_413(client: TestClient) -> None:
    big = {**VALID, "reporter_contact": "x" * (65 * 1024)}
    assert_envelope(client.post("/api/complaints", json=big), 413, "payload_too_large")


def test_oversize_chunked_body_without_length_is_413(client: TestClient) -> None:
    def chunks() -> Any:
        yield b'{"text": "'
        for _ in range(70):
            yield b"x" * 1024
        yield b'"}'

    r = client.post(
        "/api/complaints", content=chunks(), headers={"content-type": "application/json"}
    )
    assert "content-length" not in r.request.headers
    assert_envelope(r, 413, "payload_too_large")


def test_domain_errors_and_unhandled_exception(app: FastAPI, client: TestClient) -> None:
    async def conflict() -> None:
        raise InvalidTransitionError(Status.RESOLVED, Status.OPEN)

    async def limited() -> None:
        raise RateLimitExceededError(42)

    async def boom() -> None:
        raise RuntimeError("secret db error string")

    app.add_api_route("/t/conflict", conflict)
    app.add_api_route("/t/limited", limited)
    app.add_api_route("/t/boom", boom)

    body = assert_envelope(client.get("/t/conflict"), 409, "invalid_transition")
    assert body["error"]["message"] == "Cannot transition complaint from 'resolved' to 'open'."
    r = client.get("/t/limited")
    assert_envelope(r, 429, "rate_limited")
    assert r.headers["retry-after"] == "42"
    r = client.get("/t/boom")
    assert_envelope(r, 500, "internal_error")
    assert "secret db error string" not in r.text
