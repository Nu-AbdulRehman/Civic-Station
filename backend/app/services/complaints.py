"""Complaint business rules and orchestration (03-M2 §2.4, FR-BE-013/014)."""

from uuid import UUID

from app.domain.enums import Category, Priority, Status
from app.domain.errors import ComplaintNotFoundError
from app.domain.models import Complaint, ComplaintCreate
from app.domain.transitions import ensure_transition_allowed
from app.providers.cache.ports import StatsCachePort
from app.repositories.complaints import NewComplaint
from app.services.ports import ComplaintStore, Triage


class ComplaintService:
    def __init__(self, store: ComplaintStore, triage: Triage, stats_cache: StatsCachePort) -> None:
        self._store = store
        self._triage = triage
        self._stats = stats_cache

    async def submit(self, body: ComplaintCreate) -> Complaint:
        """Rate limit (route dependency) -> triage -> persist -> report -> invalidate.
        Triage cannot raise for a provider failure, so this cannot 5xx because of one
        (BR-TRIAGE-006); no row exists without a triage result (BR-TRIAGE-001)."""
        # reporter_contact is never passed to triage (BR-TRIAGE-015).
        outcome = await self._triage.run(body.text, body.location)
        complaint = await self._store.create(
            NewComplaint(
                text=body.text,
                location=body.location,
                reporter_contact=body.reporter_contact,
                category=outcome.result.category,
                priority=outcome.result.priority,
                ai_summary=outcome.result.summary,
                triaged_by=outcome.triaged_by,
                triage_confidence=outcome.result.confidence,
                triage_latency_ms=outcome.latency_ms,
            )
        )
        await self._triage.report(outcome, complaint.id)
        await self._stats.invalidate()  # before the response (BR-CACHE-003)
        return complaint

    async def get(self, complaint_id: UUID) -> Complaint:
        complaint = await self._store.get(complaint_id)
        if complaint is None:
            raise ComplaintNotFoundError(complaint_id)
        return complaint

    async def list_page(
        self,
        *,
        category: Category | None,
        priority: Priority | None,
        status: Status | None,
        page: int,
        page_size: int,
    ) -> tuple[list[Complaint], int]:
        return await self._store.list_page(
            category=category, priority=priority, status=status, page=page, page_size=page_size
        )

    async def change_status(self, complaint_id: UUID, target: Status) -> Complaint:
        """404 before 409 and no write on rejection are held inside the store's transaction
        (AD-059); the rule itself is the domain's transition table (BR-STATUS-004)."""
        complaint = await self._store.change_status(complaint_id, target, ensure_transition_allowed)
        await self._stats.invalidate()  # counts by status changed (AD-024)
        return complaint
