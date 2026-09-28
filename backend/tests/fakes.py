"""In-memory stand-ins for every port, so unit tests exercise real services and routes without
PostgreSQL or Redis (FR-BE-019: the stats service passes unchanged against a fake port)."""

from collections import Counter
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.enums import Category, Priority, Status, TriagedBy
from app.domain.errors import ComplaintNotFoundError, RateLimitExceededError
from app.domain.models import Complaint, ProviderOutcome, Stats, TriageResult
from app.repositories.complaints import Counts, NewComplaint


class InMemoryStore:
    def __init__(self) -> None:
        self.rows: dict[UUID, Complaint] = {}
        self.writes = 0

    async def create(self, new: NewComplaint) -> Complaint:
        now = datetime.now(UTC)
        complaint = Complaint(
            id=uuid4(), status=Status.OPEN, created_at=now, updated_at=now, **new.__dict__
        )
        self.rows[complaint.id] = complaint
        self.writes += 1
        return complaint

    async def get(self, complaint_id: UUID) -> Complaint | None:
        return self.rows.get(complaint_id)

    async def list_page(
        self,
        *,
        category: Category | None = None,
        priority: Priority | None = None,
        status: Status | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Complaint], int]:
        matches = [
            c
            for c in self.rows.values()
            if (category is None or c.category == category)
            and (priority is None or c.priority == priority)
            and (status is None or c.status == status)
        ]
        matches.sort(key=lambda c: (c.created_at, c.id), reverse=True)
        start = (page - 1) * page_size
        return matches[start : start + page_size], len(matches)

    async def change_status(
        self,
        complaint_id: UUID,
        target: Status,
        ensure_allowed: Callable[[Status, Status], None],
    ) -> Complaint:
        current = self.rows.get(complaint_id)
        if current is None:
            raise ComplaintNotFoundError(complaint_id)
        ensure_allowed(current.status, target)
        updated = current.model_copy(update={"status": target, "updated_at": datetime.now(UTC)})
        self.rows[complaint_id] = updated
        self.writes += 1
        return updated

    async def counts(self) -> Counts:
        rows = list(self.rows.values())
        return Counts(
            by_category=dict(Counter(c.category for c in rows)),
            by_priority=dict(Counter(c.priority for c in rows)),
            by_status=dict(Counter(c.status for c in rows)),
        )


class MemoryStatsCache:
    def __init__(self) -> None:
        self.value: Stats | None = None
        self.computations = 0

    async def get_or_compute(self, compute: Callable[[], Awaitable[Stats]]) -> tuple[Stats, bool]:
        if self.value is not None:
            return self.value, True
        self.computations += 1
        self.value = await compute()
        return self.value, False

    async def invalidate(self) -> None:
        self.value = None


class MemoryTriageCache:
    def __init__(self) -> None:
        self.data: dict[str, tuple[TriageResult, TriagedBy]] = {}

    async def get(self, key: str) -> tuple[TriageResult, TriagedBy] | None:
        return self.data.get(key)

    async def set(self, key: str, result: TriageResult, provider: TriagedBy) -> None:
        self.data[key] = (result, provider)


class MemoryOutcomes:
    def __init__(self) -> None:
        self.entries: list[ProviderOutcome] = []

    async def record(self, outcome: ProviderOutcome) -> None:
        self.entries.insert(0, outcome)
        del self.entries[20:]

    async def recent(self) -> list[ProviderOutcome]:
        return list(self.entries)


class FakeRateLimiter:
    def __init__(self) -> None:
        self.seen: list[str] = []
        self.retry_after: int | None = None  # set to make every check a 429

    async def check(self, client_ip: str) -> None:
        self.seen.append(client_ip)
        if self.retry_after is not None:
            raise RateLimitExceededError(self.retry_after)
