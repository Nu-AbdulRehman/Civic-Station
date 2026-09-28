"""What services need from the layers below, as protocols. Services never import a session,
a Redis client or a concrete provider (NFR-ARCH-002); tests substitute in-memory fakes."""

from collections.abc import Callable
from typing import Protocol
from uuid import UUID

from app.domain.enums import Category, Priority, Status
from app.domain.models import Complaint
from app.providers.triage.base import TriageOutcome
from app.repositories.complaints import Counts, NewComplaint


class ComplaintStore(Protocol):
    async def create(self, new: NewComplaint) -> Complaint: ...

    async def get(self, complaint_id: UUID) -> Complaint | None: ...

    async def list_page(
        self,
        *,
        category: Category | None = None,
        priority: Priority | None = None,
        status: Status | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[Complaint], int]: ...

    async def change_status(
        self,
        complaint_id: UUID,
        target: Status,
        ensure_allowed: Callable[[Status, Status], None],
    ) -> Complaint: ...

    async def counts(self) -> Counts: ...


class Triage(Protocol):
    """The pipeline's two entry points (AD-061)."""

    async def run(self, text: str, location: str) -> TriageOutcome: ...

    async def report(self, outcome: TriageOutcome, complaint_id: UUID) -> None: ...
