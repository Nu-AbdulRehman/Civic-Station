"""Cache ports. Services depend on these protocols, never on the Redis client (FR-BE-019)."""

from collections.abc import Awaitable, Callable
from typing import Protocol

from app.domain.enums import TriagedBy
from app.domain.models import ProviderOutcome, Stats, TriageResult


class StatsCachePort(Protocol):
    async def get_or_compute(self, compute: Callable[[], Awaitable[Stats]]) -> tuple[Stats, bool]:
        """Return (stats, served_from_cache). Never raises because Redis is down."""
        ...

    async def invalidate(self) -> None:
        """Drop the cached stats after a write (BR-CACHE-001, AD-024). Never raises."""
        ...


class RateLimiterPort(Protocol):
    async def check(self, client_ip: str) -> None:
        """Raise RateLimitExceededError when over the limit. Fails open if Redis is down."""
        ...


class TriageCachePort(Protocol):
    async def get(self, key: str) -> tuple[TriageResult, TriagedBy] | None:
        """The cached result and the provider that produced it; None on a miss or Redis down."""
        ...

    async def set(self, key: str, result: TriageResult, provider: TriagedBy) -> None: ...


class OutcomesPort(Protocol):
    async def record(self, outcome: ProviderOutcome) -> None: ...

    async def recent(self) -> list[ProviderOutcome]:
        """Newest first, at most 20; empty when Redis is down (BR-CACHE-007)."""
        ...
