import io
import json
import re
from typing import Any
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from prometheus_client.parser import text_string_to_metric_families

from app.observability.logging import configure_logging
from app.observability.middleware import resolve_request_id

UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[0-9a-f]{4}-[0-9a-f]{12}$")
TS_RE = re.compile(r"^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\.\d{3}Z$")


@pytest.fixture
def logs(client: TestClient) -> io.StringIO:
    buffer = io.StringIO()
    configure_logging("INFO", stream=buffer)
    return buffer


def lines(buffer: io.StringIO) -> list[dict[str, Any]]:
    """App log lines only; the test client's own httpx lines are JSON too but not ours."""
    parsed = [json.loads(line) for line in buffer.getvalue().splitlines()]
    return [line for line in parsed if line["logger"].startswith("app.")]


@pytest.mark.parametrize("bad", ["a\r\nX-Injected: 1", "x" * 65, "has space", "", None])
def test_unsafe_request_id_replaced_with_uuid(bad: str | None) -> None:
    assert UUID_RE.match(resolve_request_id(bad))


def test_valid_request_id_echoed(client: TestClient) -> None:
    r = client.get("/health", headers={"X-Request-ID": "abc.DEF_123-x"})
    assert r.headers["x-request-id"] == "abc.DEF_123-x"


def test_overlong_request_id_replaced_and_logged(client: TestClient, logs: io.StringIO) -> None:
    r = client.get("/health", headers={"X-Request-ID": "x" * 500})
    generated = r.headers["x-request-id"]
    assert UUID_RE.match(generated)
    assert {line["request_id"] for line in lines(logs)} == {generated}


def test_log_lines_carry_the_five_fixed_fields(client: TestClient, logs: io.StringIO) -> None:
    client.get("/health")
    parsed = lines(logs)
    assert [line["msg"] for line in parsed] == ["request.started", "request.completed"]
    for line in parsed:
        assert TS_RE.match(line["ts"])
        assert line["level"] == "INFO"
        assert UUID_RE.match(line["request_id"])
        assert line["logger"] == "app.observability.middleware"
    assert parsed[1]["status_code"] == 200 and parsed[1]["path"] == "/health"


def test_complaint_text_and_contact_absent_at_info(client: TestClient, logs: io.StringIO) -> None:
    sentinel = "Zebracrossing sentinel text 7731"
    contact = "0300-1234567"
    body = {"text": sentinel, "location": "G-9", "reporter_contact": contact}
    assert client.post("/api/complaints", json=body).status_code == 201
    output = logs.getvalue()
    assert output and sentinel not in output and contact not in output


def _count(template: str) -> float:
    labels = {"method": "GET", "path_template": template, "status": "200"}
    return REGISTRY.get_sample_value("http_requests_total", labels) or 0.0


def test_metrics_use_path_template_not_raw_path(client: TestClient) -> None:
    template = "/api/complaints/{id}"
    before = _count(template)
    complaint_id = uuid4()
    client.get(f"/api/complaints/{complaint_id}")
    assert _count(template) == before + 1
    assert str(complaint_id) not in client.get("/metrics").text


def test_metrics_endpoint_exposes_every_fixed_series(client: TestClient) -> None:
    names = {f.name for f in text_string_to_metric_families(client.get("/metrics").text)}
    expected = {
        "http_requests",
        "http_request_duration_seconds",
        "triage_duration_seconds",
        "triage_fallback",
        "triage_cache_hits",
        "triage_cache_misses",
        "stats_cache_hits",
        "stats_cache_misses",
        "rate_limit_rejected",
        "rate_limiter_unavailable",
    }
    assert expected <= names
