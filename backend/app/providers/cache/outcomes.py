"""Last-20 triage outcomes ring buffer (FR-AI-012, AD-009): global across pods."""

from redis.asyncio import Redis

from app.domain.models import ProviderOutcome
from app.observability.logging import get_logger
from app.providers.cache.client import REDIS_ERRORS

MAX_ENTRIES = 20
# Exactly these six and nothing else (FR-BE-006, CLAUDE.md rule 13): no text, no contact.
ENTRY_FIELDS = {"complaint_id", "provider", "latency_ms", "fallback", "error_class", "at"}

log = get_logger(__name__)


class RedisOutcomes:
    def __init__(self, redis: Redis, prompt_version: str) -> None:
        self._redis = redis
        # Versioned key, no TTL: a prompt change starts an empty list instead of presenting
        # outcomes from the old prompt as current.
        self._key = f"cs:outcomes:{prompt_version}"

    async def record(self, outcome: ProviderOutcome) -> None:
        entry = outcome.model_dump_json(include=ENTRY_FIELDS)
        try:
            async with self._redis.pipeline(transaction=True) as pipe:
                pipe.lpush(self._key, entry)
                pipe.ltrim(self._key, 0, MAX_ENTRIES - 1)
                await pipe.execute()
        except REDIS_ERRORS:
            log.warning("outcomes.unavailable")

    async def recent(self) -> list[ProviderOutcome]:
        try:
            entries = await self._redis.lrange(self._key, 0, MAX_ENTRIES - 1)
        except REDIS_ERRORS:
            log.warning("outcomes.unavailable")
            return []
        return [ProviderOutcome.model_validate_json(e) for e in entries]
