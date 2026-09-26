"""Cache ports. Services depend on these protocols, never on the Redis client (FR-BE-019)."""

from collections.abc import Awaitable, Callable
from typing import Protocol

from app.domain.models import Stats


class StatsCachePort(Protocol):
    async def get_or_compute(self, compute: Callable[[], Awaitable[Stats]]) -> tuple[Stats, bool]:
        """Return (stats, served_from_cache). Never raises because Redis is down."""
        ...

    async def invalidate(self) -> None:
        """Drop the cached stats after a write (BR-CACHE-001, AD-024). Never raises."""
        ...
