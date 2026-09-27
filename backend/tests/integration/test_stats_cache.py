"""Stats read-through cache against real Redis (FR-CACHE-001/002, AD-055, BR-CACHE-007)."""

import asyncio
from collections.abc import AsyncIterator
from datetime import UTC, datetime
from typing import Any, cast

import pytest
from prometheus_client import REGISTRY
from redis.asyncio import Redis

from app.config import Settings
from app.domain.enums import Category, Priority, Status
from app.domain.models import Stats
from app.providers.cache.client import make_redis
from app.providers.cache.stats import LOCK_KEY, STATS_KEY, RedisStatsCache


def _stats(total: int = 0) -> Stats:
    return Stats(
        total=total,
        by_category=dict.fromkeys(Category, 0),
        by_priority=dict.fromkeys(Priority, 0),
        by_status=dict.fromkeys(Status, 0),
        generated_at=datetime.now(UTC),
    )


def _misses() -> float:
    return REGISTRY.get_sample_value("stats_cache_misses_total") or 0.0


class Aggregation:
    """A compute function that counts calls and can be held open by the test."""

    def __init__(self, hold: bool = False) -> None:
        self.calls = 0
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        if not hold:
            self.release.set()

    async def __call__(self) -> Stats:
        self.calls += 1
        self.entered.set()
        await self.release.wait()
        return _stats(total=self.calls)


class MissCountingRedis:
    """Proxy that signals once `n` reads of the stats key have come back empty."""

    def __init__(self, redis: Redis, n: int) -> None:
        self._redis = redis
        self._remaining = n
        self.all_missed = asyncio.Event()

    def __getattr__(self, name: str) -> Any:
        return getattr(self._redis, name)

    async def get(self, key: str) -> Any:
        value = await self._redis.get(key)
        if value is None and key == STATS_KEY:
            self._remaining -= 1
            if self._remaining == 0:
                self.all_missed.set()
        return value


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    client = make_redis(Settings().redis_url)
    await client.delete(STATS_KEY, LOCK_KEY)
    yield client
    await client.delete(STATS_KEY, LOCK_KEY)
    await client.aclose()


async def test_miss_then_hit_with_the_same_generated_at(redis: Redis) -> None:
    cache = RedisStatsCache(redis, ttl_seconds=30)
    compute = Aggregation()
    first, first_hit = await cache.get_or_compute(compute)
    second, second_hit = await cache.get_or_compute(compute)
    assert (first_hit, second_hit) == (False, True)
    assert second == first  # generated_at is when it was computed, not served (contract 28)
    assert compute.calls == 1
    assert 0 < await redis.ttl(STATS_KEY) <= 30


async def test_invalidate_forces_the_next_read_to_miss(redis: Redis) -> None:
    cache = RedisStatsCache(redis, ttl_seconds=30)
    compute = Aggregation()
    await cache.get_or_compute(compute)
    await cache.invalidate()
    stats, hit = await cache.get_or_compute(compute)
    assert hit is False and stats.total == 2 and compute.calls == 2


async def test_concurrent_cold_readers_run_one_aggregation(redis: Redis) -> None:
    """Contract test 29. The aggregation is held open until all twenty callers have seen the
    empty key, so every one of them really is a cold reader; the long wait means the losers
    are released by the winner's result, never by their own timeout."""
    spy = MissCountingRedis(redis, n=20)
    cache = RedisStatsCache(cast(Redis, spy), ttl_seconds=30, max_wait_seconds=10)
    compute = Aggregation(hold=True)
    misses_before = _misses()

    tasks = [asyncio.create_task(cache.get_or_compute(compute)) for _ in range(20)]
    await spy.all_missed.wait()
    compute.release.set()
    results = await asyncio.gather(*tasks)

    assert compute.calls == 1
    assert sorted(hit for _, hit in results) == [False] + [True] * 19
    assert _misses() == misses_before + 1
    assert await redis.get(LOCK_KEY) is None  # the winner released its lock


async def test_redis_down_computes_and_reports_miss() -> None:
    cache = RedisStatsCache(make_redis("redis://127.0.0.1:1/0"), ttl_seconds=30)
    compute = Aggregation()
    stats, hit = await cache.get_or_compute(compute)
    assert hit is False and stats.total == 1
    await cache.invalidate()  # must not raise either
