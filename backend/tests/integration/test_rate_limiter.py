"""Fixed-window limiter against real Redis, with a fake clock (FR-CACHE-003, AD-008/018)."""

import io
import json
from collections.abc import AsyncIterator

import pytest
from prometheus_client import REGISTRY
from redis.asyncio import Redis

from app.config import Settings
from app.domain.errors import RateLimitExceededError
from app.observability.logging import configure_logging
from app.providers.cache.client import make_redis
from app.providers.cache.ratelimit import RedisRateLimiter

T0 = 1_800_000_000.0  # a window boundary for a 60 s window
IP = "203.0.113.9"


class Clock:
    def __init__(self, now: float = T0) -> None:
        self.now = now

    def __call__(self) -> float:
        return self.now


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    client = make_redis(Settings().redis_url)
    keys = [k async for k in client.scan_iter("cs:ratelimit:*")]
    if keys:
        await client.delete(*keys)
    yield client
    await client.aclose()


async def _allowed(limiter: RedisRateLimiter, ip: str, n: int) -> None:
    for _ in range(n):
        await limiter.check(ip)


async def test_limit_then_429_with_remaining_window(redis: Redis) -> None:
    clock = Clock(T0 + 20.4)
    limiter = RedisRateLimiter(redis, limit=10, window_seconds=60, clock=clock)
    await _allowed(limiter, IP, 10)
    with pytest.raises(RateLimitExceededError) as exc:
        await limiter.check(IP)
    assert exc.value.retry_after_seconds == 40  # ceil(60 - 20.4)
    ttls = [await redis.ttl(k) async for k in redis.scan_iter("cs:ratelimit:*")]
    assert len(ttls) == 1 and 0 < ttls[0] <= 60


async def test_distinct_clients_are_limited_independently(redis: Redis) -> None:
    limiter = RedisRateLimiter(redis, limit=2, window_seconds=60, clock=Clock())
    await _allowed(limiter, "198.51.100.1", 2)
    await _allowed(limiter, "198.51.100.2", 2)
    with pytest.raises(RateLimitExceededError):
        await limiter.check("198.51.100.1")


async def test_next_window_restores_capacity(redis: Redis) -> None:
    clock = Clock()
    limiter = RedisRateLimiter(redis, limit=1, window_seconds=60, clock=clock)
    await limiter.check(IP)
    with pytest.raises(RateLimitExceededError):
        await limiter.check(IP)
    clock.now += 60
    await limiter.check(IP)


async def test_redis_down_fails_open_loudly_once_per_request() -> None:
    buffer = io.StringIO()
    configure_logging("INFO", stream=buffer)
    before = REGISTRY.get_sample_value("rate_limiter_unavailable_total") or 0.0
    limiter = RedisRateLimiter(
        make_redis("redis://127.0.0.1:1/0"), limit=1, window_seconds=60, clock=Clock()
    )
    await _allowed(limiter, IP, 2)  # over the limit, yet allowed: fail open

    errors = [json.loads(line) for line in buffer.getvalue().splitlines()]
    errors = [e for e in errors if e["level"] == "ERROR"]
    assert [e["msg"] for e in errors] == ["ratelimit.unavailable"] * 2
    assert REGISTRY.get_sample_value("rate_limiter_unavailable_total") == before + 2
