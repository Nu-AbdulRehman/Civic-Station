"""Distributed fixed-window rate limiter in Redis (FR-CACHE-003, AD-017/018, BR-CACHE-004/007).

State lives in Redis, never in process: with four replicas an in-process counter would allow
four times the configured rate.
"""

import math
import time
from collections.abc import Callable

from redis.asyncio import Redis

from app.domain.errors import RateLimitExceededError
from app.observability.logging import get_logger
from app.observability.metrics import RATE_LIMIT_REJECTED, RATE_LIMITER_UNAVAILABLE
from app.providers.cache.client import REDIS_ERRORS

log = get_logger(__name__)


class RedisRateLimiter:
    def __init__(
        self,
        redis: Redis,
        limit: int,
        window_seconds: int,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._redis = redis
        self._limit = limit
        self._window = window_seconds
        self._clock = clock

    async def check(self, client_ip: str) -> None:
        """Count one request. Raises RateLimitExceededError over the limit; fails open."""
        now = self._clock()
        window = int(now // self._window)
        key = f"cs:ratelimit:{client_ip}:{window}"
        try:
            # One round trip. EXPIRE NX sets the TTL only on the window's first request.
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.incr(key)
                pipe.expire(key, self._window, nx=True)
                count, _ = await pipe.execute()
        except REDIS_ERRORS:
            # Fail open, loudly (AD-008, ADR-0005): /ready is 503 in this state, so the pod
            # leaves the Service and the unprotected window is bounded and visible.
            RATE_LIMITER_UNAVAILABLE.inc()
            log.error("ratelimit.unavailable")
            return
        if count > self._limit:
            retry_after = max(1, math.ceil((window + 1) * self._window - now))
            RATE_LIMIT_REJECTED.inc()
            log.info("ratelimit.exceeded", client_ip=client_ip, retry_after=retry_after)
            raise RateLimitExceededError(retry_after)
