"""All complaint SQL (BR-DATA-003, FR-BE-016/017). One transaction per method (AD-059)."""

from collections.abc import Callable
from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, insert, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import InstrumentedAttribute

from app.db.models import ComplaintRow
from app.domain.enums import Category, Priority, Status, TriagedBy
from app.domain.errors import ComplaintNotFoundError
from app.domain.models import Complaint


@dataclass(frozen=True)
class NewComplaint:
    text: str
    location: str
    reporter_contact: str | None
    category: Category
    priority: Priority
    ai_summary: str
    triaged_by: TriagedBy
    triage_confidence: float
    triage_latency_ms: int


@dataclass(frozen=True)
class Counts:
    """Raw GROUP BY results. Zero-filling every enum key is the stats service's job (AD-025)."""

    by_category: dict[Category, int]
    by_priority: dict[Priority, int]
    by_status: dict[Status, int]


def _to_domain(row: ComplaintRow) -> Complaint:
    return Complaint.model_validate(row, from_attributes=True)


class ComplaintRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._sessions = session_factory

    async def create(self, new: NewComplaint) -> Complaint:
        values = {**new.__dict__, "triaged_by": new.triaged_by.value}
        async with self._sessions.begin() as session:
            row = await session.scalar(insert(ComplaintRow).values(values).returning(ComplaintRow))
            assert row is not None
            return _to_domain(row)

    async def get(self, complaint_id: UUID) -> Complaint | None:
        async with self._sessions() as session:
            row = await session.get(ComplaintRow, complaint_id)
            return _to_domain(row) if row is not None else None

    async def list_page(
        self,
        *,
        category: Category | None = None,
        priority: Priority | None = None,
        status: Status | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Complaint], int]:
        conditions = [
            column == value
            for column, value in (
                (ComplaintRow.category, category),
                (ComplaintRow.priority, priority),
                (ComplaintRow.status, status),
            )
            if value is not None
        ]
        page_query = (
            select(ComplaintRow)
            .where(*conditions)
            # AD-016: the id tie-break is what keeps pagination stable on equal timestamps.
            .order_by(ComplaintRow.created_at.desc(), ComplaintRow.id.desc())
            .limit(page_size)
            .offset((page - 1) * page_size)
        )
        count_query = select(func.count()).select_from(ComplaintRow).where(*conditions)
        # One transaction: the total and the page describe the same snapshot.
        async with self._sessions.begin() as session:
            total = await session.scalar(count_query) or 0
            rows = (await session.scalars(page_query)).all()
            return [_to_domain(r) for r in rows], total

    async def change_status(
        self,
        complaint_id: UUID,
        target: Status,
        ensure_allowed: Callable[[Status, Status], None],
    ) -> Complaint:
        """Lock, check, update. Existence before transition (BR-STATUS-007); a rejected
        transition raises before any write, so `updated_at` is untouched (BR-STATUS-006)."""
        async with self._sessions.begin() as session:
            row = await session.get(ComplaintRow, complaint_id, with_for_update=True)
            if row is None:
                raise ComplaintNotFoundError(complaint_id)
            ensure_allowed(row.status, target)
            row.status = target
            row.updated_at = func.now()
            await session.flush()
            await session.refresh(row)
            return _to_domain(row)

    async def counts(self) -> Counts:
        """Three GROUP BY queries in SQL, never a Python loop over rows (NFR-PERF-005)."""
        async with self._sessions.begin() as session:
            return Counts(
                by_category=await _group(session, ComplaintRow.category),
                by_priority=await _group(session, ComplaintRow.priority),
                by_status=await _group(session, ComplaintRow.status),
            )


async def _group[T](session: AsyncSession, column: InstrumentedAttribute[T]) -> dict[T, int]:
    result = await session.execute(select(column, func.count()).group_by(column))
    return {key: count for key, count in result}
