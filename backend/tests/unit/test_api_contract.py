"""01-api-contract.md §14 against the real app with in-memory ports (T-M2-007…013).
The same contract is proven against PostgreSQL and Redis in tests/integration/test_api.py."""

import itertools
from uuid import uuid4

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.domain.enums import Status
from app.main import create_app
from app.providers.triage.simulated import SimulatedTriage
from tests.conftest import Fakes, install_fakes

COMPLAINT_FIELDS = {
    "id", "text", "location", "reporter_contact", "category", "priority", "status",
    "ai_summary", "triaged_by", "triage_confidence", "triage_latency_ms", "created_at",
    "updated_at",
}  # fmt: skip
TRIAGED_BY = {"llm:groq", "llm:ollama", "rules", "rules:fallback", "simulated"}
VALID = {"text": "Burst water main flooding Street 12 since fajr", "location": "Saddar"}


def post(client: TestClient, **overrides: object) -> dict[str, object]:
    r = client.post("/api/complaints", json=VALID | overrides)
    assert r.status_code == 201, r.text
    body: dict[str, object] = r.json()
    return body


def test_01_02_create_then_get(client: TestClient) -> None:
    r = client.post("/api/complaints", json=VALID | {"reporter_contact": "0300-1234567"})
    assert r.status_code == 201
    body = r.json()
    assert set(body) == COMPLAINT_FIELDS and body["triaged_by"] in TRIAGED_BY
    assert body["status"] == "open" and r.headers["Location"] == f"/api/complaints/{body['id']}"
    assert client.get(f"/api/complaints/{body['id']}").json() == body


def test_create_never_sends_contact_to_the_provider(app: FastAPI, fakes: Fakes) -> None:
    seen: list[tuple[str, str]] = []

    class Spy:
        name = "simulated"

        async def triage(self, text: str, location: str) -> object:
            seen.append((text, location))
            return await SimulatedTriage(1).triage(text, location)

    install_fakes(app, fakes, provider=Spy())  # type: ignore[arg-type]
    # A name, not a number or address: redact() would scrub those and mask a leak.
    post(TestClient(app), reporter_contact="Imran Qureshi")
    assert seen and all("Qureshi" not in t and "Qureshi" not in loc for t, loc in seen)


def test_07_08_filters_total_and_pagination(client: TestClient) -> None:
    ids = [str(post(client, text=f"Burst water main number {i} flooding")["id"]) for i in range(5)]
    post(client, text="Streetlight not working for weeks")
    page = client.get("/api/complaints", params={"category": "water", "page_size": 2}).json()
    assert page["total"] == 5 and len(page["items"]) == 2 and page["page_size"] == 2
    seen = []
    for n in (1, 2, 3):
        r = client.get("/api/complaints", params={"category": "water", "page": n, "page_size": 2})
        seen += [c["id"] for c in r.json()["items"]]
    assert sorted(seen) == sorted(ids) and len(set(seen)) == 5


def test_22_page_beyond_the_end_is_empty_with_true_total(client: TestClient) -> None:
    post(client)
    body = client.get("/api/complaints", params={"page": 999}).json()
    assert body["items"] == [] and body["total"] == 1


def test_09_status_walk_and_409_message(client: TestClient) -> None:
    cid = post(client)["id"]
    url = f"/api/complaints/{cid}/status"
    assert client.patch(url, json={"status": "in_progress"}).json()["status"] == "in_progress"
    assert client.patch(url, json={"status": "resolved"}).json()["status"] == "resolved"
    r = client.patch(url, json={"status": "open"})
    assert r.status_code == 409
    assert r.json()["error"]["message"] == "Cannot transition complaint from 'resolved' to 'open'."


@pytest.mark.parametrize(("current", "target"), list(itertools.product(Status, Status)))
def test_every_status_pair_over_http(
    client: TestClient, fakes: Fakes, current: Status, target: Status
) -> None:
    """All 16 pairs through the real route and service; a 409 writes nothing (BR-STATUS-006)."""
    cid = post(client)["id"]
    key = next(iter(fakes.store.rows))
    fakes.store.rows[key] = fakes.store.rows[key].model_copy(update={"status": current})
    before = fakes.store.rows[key]
    allowed = {
        (Status.OPEN, Status.IN_PROGRESS),
        (Status.OPEN, Status.REJECTED),
        (Status.IN_PROGRESS, Status.RESOLVED),
        (Status.IN_PROGRESS, Status.REJECTED),
    }
    r = client.patch(f"/api/complaints/{cid}/status", json={"status": target.value})
    if (current, target) in allowed:
        assert r.status_code == 200 and r.json()["status"] == target.value
    else:
        assert r.status_code == 409 and fakes.store.rows[key] == before


def test_10_body_validation_before_existence_before_transition(client: TestClient) -> None:
    unknown = f"/api/complaints/{uuid4()}/status"
    assert client.patch(unknown, json={"status": "closed"}).status_code == 400
    r = client.patch(unknown, json={"status": "resolved"})
    assert r.status_code == 404 and r.json()["error"]["code"] == "not_found"


def test_404_for_unknown_id(client: TestClient) -> None:
    assert client.get(f"/api/complaints/{uuid4()}").status_code == 404


def test_11_12_stats_miss_hit_and_invalidation(client: TestClient) -> None:
    first = client.get("/api/stats")
    second = client.get("/api/stats")
    assert (first.headers["X-Cache"], second.headers["X-Cache"]) == ("MISS", "HIT")
    assert first.json() == second.json()  # same generated_at within the TTL (contract 28)
    assert first.json()["by_category"] == dict.fromkeys(
        ["water", "electricity", "sanitation", "roads", "streetlights", "other"], 0
    )

    cid = post(client)["id"]
    after_create = client.get("/api/stats")
    assert after_create.headers["X-Cache"] == "MISS" and after_create.json()["total"] == 1

    client.get("/api/stats")
    client.patch(f"/api/complaints/{cid}/status", json={"status": "in_progress"})
    after_patch = client.get("/api/stats")
    assert after_patch.headers["X-Cache"] == "MISS"
    assert after_patch.json()["by_status"]["in_progress"] == 1


def test_rejected_transition_does_not_invalidate_stats(client: TestClient) -> None:
    cid = post(client)["id"]
    client.get("/api/stats")
    client.patch(f"/api/complaints/{cid}/status", json={"status": "resolved"})
    assert client.get("/api/stats").headers["X-Cache"] == "HIT"


def test_rate_limited_submission_costs_no_inference_and_no_row(
    client: TestClient, fakes: Fakes
) -> None:
    fakes.limiter.retry_after = 30
    assert client.post("/api/complaints", json=VALID).status_code == 429
    assert fakes.store.writes == 0 and fakes.outcomes.entries == []


@pytest.mark.parametrize(
    ("mode", "error_class"), [("raise", "Other"), ("malformed", "ValidationFailed")]
)
def test_15_16_provider_failure_is_still_201_with_rules_fallback(
    app: FastAPI, fakes: Fakes, mode: str, error_class: str
) -> None:
    """THE mandatory test, over HTTP (FR-BE-028, contract 15/16)."""
    install_fakes(app, fakes, provider=SimulatedTriage(1337, mode))  # type: ignore[arg-type]
    client = TestClient(app)
    body = post(client)
    assert body["triaged_by"] == "rules:fallback"
    assert fakes.store.rows[next(iter(fakes.store.rows))].triaged_by == "rules:fallback"
    newest = fakes.outcomes.entries[0]
    assert newest.fallback and newest.error_class == error_class  # contract 19


def test_13_health_does_not_touch_the_database(app: FastAPI) -> None:
    def explode() -> None:
        raise RuntimeError("database is down")

    app.state.session_factory = explode
    app.state.engine = None
    assert TestClient(app).get("/health").status_code == 200


def test_14_ready_names_the_failed_dependency(app: FastAPI) -> None:
    from app.services.readiness import ReadinessService

    async def ok() -> None:
        return None

    async def down() -> None:
        raise ConnectionError("refused")

    app.state.readiness_service = ReadinessService({"database": ok, "cache": down}, 1)
    r = TestClient(app).get("/ready")
    assert r.status_code == 503
    body = r.json()
    assert body["error"] == {"code": "dependency_unavailable", "message": "cache unreachable"}
    assert body["checks"] == {"database": "ok", "cache": "fail"}
    assert body["request_id"] == r.headers["x-request-id"]


def test_ready_ok(client: TestClient) -> None:
    r = client.get("/ready")
    assert r.status_code == 200 and r.json()["status"] == "ready"


# --- CORS (T-M2-013, contract tests 26/27) -----------------------------------------------------

ORIGIN = "http://localhost:5173"


@pytest.fixture
def cors_client(fakes: Fakes) -> TestClient:
    settings = Settings(
        database_url="postgresql+asyncpg://u@database/db",
        redis_url="redis://cache",
        cors_allow_origins=f"{ORIGIN},http://localhost:8080",
    )
    app = create_app(settings)
    install_fakes(app, fakes)
    return TestClient(app)


def test_26_preflight_allowed_and_refused(cors_client: TestClient) -> None:
    preflight = {"Access-Control-Request-Method": "POST"}
    ok = cors_client.options(
        "/api/complaints",
        headers=preflight | {"Origin": ORIGIN, "Access-Control-Request-Headers": "X-Request-ID"},
    )
    assert ok.status_code == 204
    assert "x-request-id" in ok.headers["access-control-allow-headers"].lower()
    refused = cors_client.options(
        "/api/complaints", headers=preflight | {"Origin": "https://evil.example"}
    )
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "cors_forbidden"


def test_27_a_429_still_carries_cors_headers(cors_client: TestClient, fakes: Fakes) -> None:
    fakes.limiter.retry_after = 10
    r = cors_client.post("/api/complaints", json=VALID, headers={"Origin": ORIGIN})
    assert r.status_code == 429
    assert r.headers["access-control-allow-origin"] == ORIGIN
    assert "retry-after" in r.headers["access-control-expose-headers"].lower()


def test_same_origin_default_sends_no_cors_headers(client: TestClient) -> None:
    r = client.get("/api/stats", headers={"Origin": ORIGIN})
    assert "access-control-allow-origin" not in r.headers


def test_middleware_rejections_carry_cors_too(cors_client: TestClient) -> None:
    """A 429 is raised inside the route, so it would get CORS headers even from an inner CORS
    layer. A 415 is produced by the request middleware itself: only an OUTERMOST CORS layer
    can decorate it, which is the ordering FR-BE-012 requires."""
    r = cors_client.post(
        "/api/complaints",
        content=b"text",
        headers={"Origin": ORIGIN, "Content-Type": "text/plain"},
    )
    assert r.status_code == 415
    assert r.headers["access-control-allow-origin"] == ORIGIN


def test_19_meta_providers_reports_the_forced_failure(app: FastAPI, fakes: Fakes) -> None:
    install_fakes(app, fakes, provider=SimulatedTriage(1337, "raise"))
    client = TestClient(app)
    body = post(client)
    meta = client.get("/api/meta/providers").json()
    assert meta["active_provider"] == "simulated"
    newest = meta["recent"][0]
    assert newest["complaint_id"] == body["id"]
    assert (newest["provider"], newest["fallback"], newest["error_class"]) == (
        "rules:fallback",
        True,
        "Other",
    )
    assert (
        newest["confidence"] is None
    )  # six fields stored (FR-BE-006); the contract's slot stays null
