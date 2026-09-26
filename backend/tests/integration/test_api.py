"""The contract end to end against real PostgreSQL and Redis (01-api-contract §14, AD-010).
TRIAGE_PROVIDER=simulated throughout, as in CI; no test calls a hosted model."""

from collections.abc import Iterator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY
from redis import Redis as SyncRedis
from sqlalchemy import text

from app.config import Settings
from app.main import create_app

VALID = {"text": "Burst water main flooding Street 12 since fajr", "location": "Saddar"}


@pytest.fixture(autouse=True)
def clean(database_url: str) -> Iterator[None]:
    """A clean cs:* keyspace before each test (tables are truncated per client)."""
    redis = SyncRedis.from_url(Settings().redis_url)
    keys = list(redis.scan_iter("cs:*"))
    if keys:
        redis.delete(*keys)
    redis.close()
    yield


def make_client(**overrides: Any) -> TestClient:
    options: dict[str, Any] = {"triage_provider": "simulated", "rate_limit_requests": 1000}
    return TestClient(create_app(Settings(**(options | overrides))))


@pytest.fixture
def client() -> Iterator[TestClient]:
    with make_client() as c:  # runs the lifespan, so shutdown closes the pools
        truncate(c)
        yield c


def truncate(c: TestClient) -> None:
    async def _truncate() -> None:
        async with c.app.state.engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.execute(text("TRUNCATE complaints"))

    c.portal.call(_truncate)  # type: ignore[union-attr]


def post(c: TestClient, **overrides: object) -> dict[str, Any]:
    r = c.post("/api/complaints", json=VALID | overrides)
    assert r.status_code == 201, r.text
    body: dict[str, Any] = r.json()
    return body


def test_01_02_create_persists_and_reads_back(client: TestClient) -> None:
    body = post(client, reporter_contact="0300-1234567")
    assert body["triaged_by"] == "simulated"
    assert client.get(f"/api/complaints/{body['id']}").json() == body


def test_05_limit_plus_one_is_429_with_retry_after() -> None:
    with make_client(rate_limit_requests=3) as c:
        truncate(c)
        statuses = [c.post("/api/complaints", json=VALID).status_code for _ in range(4)]
        assert statuses == [201, 201, 201, 429]
        r = c.post("/api/complaints", json=VALID)
        assert 1 <= int(r.headers["retry-after"]) <= 60
        assert c.get("/api/complaints").json()["total"] == 3  # a 429 wrote no row


def test_07_08_filtered_total_and_stable_pages(client: TestClient) -> None:
    for i in range(7):
        post(client, text=f"Complaint number {i} about the area near market")
    first = client.get("/api/complaints", params={"page_size": 3}).json()
    assert first["total"] == 7
    seen = []
    for n in (1, 2, 3):
        seen += [c["id"] for c in client.get(
            "/api/complaints", params={"page": n, "page_size": 3}
        ).json()["items"]]  # fmt: skip
    assert len(seen) == 7 and len(set(seen)) == 7
    some = first["items"][0]
    filtered = client.get(
        "/api/complaints", params={"category": some["category"], "priority": some["priority"]}
    ).json()
    assert filtered["total"] >= 1
    assert all(
        c["category"] == some["category"] and c["priority"] == some["priority"]
        for c in filtered["items"]
    )


def test_09_10_status_machine_over_http(client: TestClient) -> None:
    cid = post(client)["id"]
    url = f"/api/complaints/{cid}/status"
    assert client.patch(url, json={"status": "in_progress"}).status_code == 200
    resolved = client.patch(url, json={"status": "resolved"}).json()
    r = client.patch(url, json={"status": "open"})
    assert r.status_code == 409 and "'resolved'" in r.json()["error"]["message"]
    assert client.get(f"/api/complaints/{cid}").json()["updated_at"] == resolved["updated_at"]


def test_11_12_28_stats_cache(client: TestClient) -> None:
    a, b = client.get("/api/stats"), client.get("/api/stats")
    assert (a.headers["X-Cache"], b.headers["X-Cache"]) == ("MISS", "HIT")
    assert a.json()["generated_at"] == b.json()["generated_at"]
    post(client)
    c = client.get("/api/stats")
    assert c.headers["X-Cache"] == "MISS" and c.json()["total"] == 1
    assert c.json()["generated_at"] > a.json()["generated_at"]


def test_14_ready_503_names_cache_when_redis_is_down() -> None:
    with make_client(redis_url="redis://127.0.0.1:1/0") as c:
        r = c.get("/ready")
        assert r.status_code == 503
        assert r.json()["checks"] == {"database": "ok", "cache": "fail"}
        assert "cache" in r.json()["error"]["message"]
        # And the degradations hold: stats still answer, as MISS (BR-CACHE-007).
        assert c.get("/api/stats").headers["X-Cache"] == "MISS"


def test_ready_200_with_both_dependencies(client: TestClient) -> None:
    assert client.get("/ready").json() == {
        "status": "ready",
        "checks": {"database": "ok", "cache": "ok"},
    }


@pytest.mark.parametrize("mode", ["raise", "malformed"])
def test_15_16_mandatory_fallback_persists_rules_fallback(mode: str) -> None:
    with make_client(simulated_failure_mode=mode) as c:
        truncate(c)
        body = post(c)
        assert body["triaged_by"] == "rules:fallback"
        stored = c.get(f"/api/complaints/{body['id']}").json()
        assert stored["triaged_by"] == "rules:fallback"  # persisted, not just returned

        async def recent() -> list[Any]:
            return await c.app.state.triage_pipeline._outcomes.recent()  # type: ignore[attr-defined, no-any-return]

        newest = c.portal.call(recent)[0]  # type: ignore[union-attr]
        assert newest.fallback and str(newest.complaint_id) == body["id"]  # contract 19


def test_18_identical_complaints_cost_one_inference(client: TestClient) -> None:
    before = REGISTRY.get_sample_value("triage_cache_hits_total") or 0.0
    first, second = post(client), post(client)
    assert REGISTRY.get_sample_value("triage_cache_hits_total") == before + 1
    assert (first["category"], first["priority"]) == (second["category"], second["priority"])
