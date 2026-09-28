"""Stats read-through cache with single-flight on a miss (FR-CACHE-001/002, AD-055)."""

import asyncio
import uuid
from collections.abc import Awaitable, Callable

from redis.asyncio import Redis

from app.domain.models import Stats
from app.observability.logging import get_logger
from app.observability.metrics import STATS_CACHE_HITS, STATS_CACHE_MISSES
from app.providers.cache.client import REDIS_ERRORS

STATS_KEY = "cs:stats:v1"
LOCK_KEY = "cs:stats:lock"
LOCK_TTL_SECONDS = 5  # backstop for a lock holder that dies mid-aggregation
POLL_INTERVAL_SECONDS = 0.025

# Delete the lock only if we still own it, so a holder that outlived the TTL cannot release
# the next holder's lock.
_RELEASE = """
if redis.call('get', KEYS[1]) == ARGV[1] then return redis.call('del', KEYS[1]) end
return 0
"""

log = get_logger(__name__)


class RedisStatsCache:
    """`X-Cache` truth comes from here: True only when the bytes came from Redis (BR-CACHE-002).

    A miss is counted once per aggregation actually run, so twenty concurrent cold readers
    move `stats_cache_misses_total` by exactly one (contract test 29)."""

    def __init__(self, redis: Redis, ttl_seconds: int, max_wait_seconds: float = 0.25) -> None:
        self._redis = redis
        self._ttl = ttl_seconds
        self._max_wait = max_wait_seconds

    async def get_or_compute(self, compute: Callable[[], Awaitable[Stats]]) -> tuple[Stats, bool]:
        try:
            cached = await self._redis.get(STATS_KEY)
            if cached is not None:
                return self._hit(cached)
            token = uuid.uuid4().hex
            if await self._redis.set(LOCK_KEY, token, nx=True, ex=LOCK_TTL_SECONDS):
                try:
                    stats = await self._miss(compute)
                    await self._redis.set(STATS_KEY, stats.model_dump_json(), ex=self._ttl)
                    return stats, False
                finally:
                    await self._redis.eval(_RELEASE, 1, LOCK_KEY, token)
            # Another caller is aggregating: wait a bounded time for its result.
            deadline = asyncio.get_running_loop().time() + self._max_wait
            while asyncio.get_running_loop().time() < deadline:
                await asyncio.sleep(POLL_INTERVAL_SECONDS)
                cached = await self._redis.get(STATS_KEY)
                if cached is not None:
                    return self._hit(cached)
        except REDIS_ERRORS:
            log.warning("stats.cache_unavailable")
        # Redis down, or the lock holder is slow: compute directly, never fail (BR-CACHE-007).
        return await self._miss(compute), False

    async def invalidate(self) -> None:
        try:
            await self._redis.delete(STATS_KEY)
        except REDIS_ERRORS:
            # The 30 s TTL still bounds staleness; a write must not fail over its cache.
            log.warning("stats.invalidate_failed")

    @staticmethod
    def _hit(cached: str | bytes) -> tuple[Stats, bool]:
        STATS_CACHE_HITS.inc()
        log.debug("stats.cache_hit")
        return Stats.model_validate_json(cached), True

    @staticmethod
    async def _miss(compute: Callable[[], Awaitable[Stats]]) -> Stats:
        STATS_CACHE_MISSES.inc()
        log.debug("stats.cache_miss")
        return await compute()
