"""Triage content-hash cache (FR-CACHE-004, AD-019, BR-TRIAGE-011)."""

import hashlib
import json
import string

from redis.asyncio import Redis

from app.domain.enums import TriagedBy
from app.domain.models import TriageResult
from app.observability.logging import get_logger
from app.observability.metrics import TRIAGE_CACHE_HITS, TRIAGE_CACHE_MISSES
from app.providers.cache.client import REDIS_ERRORS

log = get_logger(__name__)
_STRIP = string.punctuation + string.whitespace


def normalise(value: str) -> str:
    """Lower-case, collapse whitespace runs, strip surrounding punctuation (AD-019)."""
    return " ".join(value.lower().split()).strip(_STRIP)


def triage_cache_key(redacted_text: str, location: str, provider: str, prompt_version: str) -> str:
    """Computed on REDACTED text (ADR-0004). Provider and prompt version are in the key, so
    switching either can never serve a result produced under the old configuration."""
    material = "|".join((normalise(redacted_text), normalise(location), provider, prompt_version))
    return f"cs:triage:{hashlib.sha256(material.encode()).hexdigest()}"


class RedisTriageCache:
    def __init__(self, redis: Redis, ttl_seconds: int) -> None:
        self._redis = redis
        self._ttl = ttl_seconds

    async def get(self, key: str) -> tuple[TriageResult, TriagedBy] | None:
        try:
            raw = await self._redis.get(key)
        except REDIS_ERRORS:
            log.warning("triage.cache_unavailable")
            return None  # skipped, not a miss: the hit rate is over answered lookups
        if raw is None:
            TRIAGE_CACHE_MISSES.inc()
            log.debug("triage.cache_miss")
            return None
        stored = json.loads(raw)
        TRIAGE_CACHE_HITS.inc()
        log.debug("triage.cache_hit")
        return TriageResult.model_validate(stored["result"]), TriagedBy(stored["provider"])

    async def set(self, key: str, result: TriageResult, provider: TriagedBy) -> None:
        value = json.dumps({"result": result.model_dump(mode="json"), "provider": provider.value})
        try:
            await self._redis.set(key, value, ex=self._ttl)
        except REDIS_ERRORS:
            log.warning("triage.cache_unavailable")
