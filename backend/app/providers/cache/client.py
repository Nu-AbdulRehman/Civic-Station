"""The only module that builds a Redis client (FR-BE-019). Callers see CacheUnavailableError."""

from redis.asyncio import Redis
from redis.exceptions import RedisError

# Short timeouts: a hung Redis must degrade a request (BR-CACHE-007), never stall it.
SOCKET_TIMEOUT_SECONDS = 1.0

# Every Redis failure mode the degradation paths handle, in one place.
REDIS_ERRORS = (RedisError, OSError)


class CacheUnavailableError(Exception):
    """Redis could not be reached or did not answer in time."""


def make_redis(redis_url: str) -> Redis:
    return Redis.from_url(
        redis_url,
        socket_timeout=SOCKET_TIMEOUT_SECONDS,
        socket_connect_timeout=SOCKET_TIMEOUT_SECONDS,
        decode_responses=True,
    )
