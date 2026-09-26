"""Complaint endpoints. T-M2-001 stubs: static bodies, replaced by service calls in T-M2-010."""

from datetime import UTC, datetime
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Response, status

from app.domain.enums import Category, Priority, Status, TriagedBy
from app.domain.models import Complaint, ComplaintCreate, ComplaintPage, StatusUpdate

router = APIRouter(prefix="/api/complaints", tags=["complaints"])

_STUB_TIME = datetime(2026, 1, 1, tzinfo=UTC)


def _stub_complaint(complaint_id: UUID, complaint_status: Status = Status.OPEN) -> Complaint:
    return Complaint(
        id=complaint_id,
        text="Stub complaint text.",
        location="Stub location",
        reporter_contact=None,
        category=Category.OTHER,
        priority=Priority.NORMAL,
        status=complaint_status,
        ai_summary="other: Stub complaint text.",
        triaged_by=TriagedBy.RULES,
        triage_confidence=0.35,
        triage_latency_ms=0,
        created_at=_STUB_TIME,
        updated_at=_STUB_TIME,
    )


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_complaint(body: ComplaintCreate, response: Response) -> Complaint:
    complaint = _stub_complaint(uuid4())
    response.headers["Location"] = f"/api/complaints/{complaint.id}"
    return complaint


@router.get("")
async def list_complaints(
    category: Category | None = None,
    priority: Priority | None = None,
    status: Status | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ComplaintPage:
    return ComplaintPage(items=[], total=0, page=page, page_size=page_size)


@router.get("/{id}")
async def get_complaint(id: UUID) -> Complaint:
    return _stub_complaint(id)


@router.patch("/{id}/status")
async def change_status(id: UUID, body: StatusUpdate) -> Complaint:
    return _stub_complaint(id, body.status)
