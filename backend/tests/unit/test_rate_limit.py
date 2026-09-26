from ipaddress import ip_network

import pytest
from fastapi.testclient import TestClient

from app.client_ip import resolve_client_ip
from app.config import Settings
from tests.fakes import FakeRateLimiter

TRUSTED = [ip_network("10.0.0.0/8")]
VALID = {"text": "Water pipe burst on main road", "location": "Saddar"}


@pytest.mark.parametrize(
    ("peer", "forwarded", "expected"),
    [
        ("10.0.0.5", "203.0.113.9", "203.0.113.9"),  # trusted proxy: its appended entry
        ("10.0.0.5", "6.6.6.6, 203.0.113.9", "203.0.113.9"),  # forged first entry ignored
        ("198.51.100.7", "203.0.113.9", "198.51.100.7"),  # untrusted peer: header ignored
        ("10.0.0.5", None, "10.0.0.5"),  # no header: socket peer
        ("10.0.0.5", "not-an-ip", "10.0.0.5"),  # garbage from a proxy: peer
        (None, "203.0.113.9", "unknown"),
    ],
)
def test_resolve_client_ip(peer: str | None, forwarded: str | None, expected: str) -> None:
    assert resolve_client_ip(peer, forwarded, TRUSTED) == expected


def test_invalid_trusted_cidr_fails_at_startup() -> None:
    with pytest.raises(ValueError, match="TRUSTED|trusted_proxy_cidrs"):
        Settings(database_url="x", redis_url="y", trusted_proxy_cidrs="10.0.0.0/8,banana")


def test_post_is_limited_before_body_validation(
    client: TestClient, limiter: FakeRateLimiter
) -> None:
    """BR-CACHE-006: an over-limit request with an invalid body is a 429, not a 400."""
    limiter.retry_after = 17
    r = client.post("/api/complaints", json={"text": "short", "category": "water"})
    assert r.status_code == 429
    assert r.headers["retry-after"] == "17"
    assert r.json()["error"]["code"] == "rate_limited"


def test_only_post_is_limited(client: TestClient, limiter: FakeRateLimiter) -> None:
    limiter.retry_after = 5
    assert client.get("/api/complaints").status_code == 200
    assert client.get("/api/stats").status_code == 200
    assert limiter.seen == []


def test_limiter_receives_the_resolved_client_ip(
    client: TestClient, limiter: FakeRateLimiter
) -> None:
    client.post("/api/complaints", json=VALID, headers={"X-Forwarded-For": "203.0.113.9"})
    assert limiter.seen == ["testclient"]  # the test peer is not a trusted proxy
