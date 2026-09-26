"""Aggregate statistics, read through the stats cache (FR-BE-015, AD-025, AD-055)."""

from datetime import UTC, datetime

from app.domain.enums import Category, Priority, Status
from app.domain.models import Stats
from app.providers.cache.ports import StatsCachePort
from app.services.ports import ComplaintStore


class StatsService:
    def __init__(self, store: ComplaintStore, cache: StatsCachePort) -> None:
        self._store = store
        self._cache = cache

    async def get_stats(self) -> tuple[Stats, bool]:
        """(stats, served_from_cache). Redis down still answers, as a MISS (BR-CACHE-007)."""
        return await self._cache.get_or_compute(self._compute)

    async def _compute(self) -> Stats:
        counts = await self._store.counts()
        by_status = dict.fromkeys(Status, 0) | counts.by_status
        return Stats(
            total=sum(by_status.values()),
            # Every enum key present with an explicit zero, so no client guesses (AD-025).
            by_category=dict.fromkeys(Category, 0) | counts.by_category,
            by_priority=dict.fromkeys(Priority, 0) | counts.by_priority,
            by_status=by_status,
            generated_at=datetime.now(UTC),
        )
