"""Complaint endpoints. HTTP only: parse, call one service operation, shape the response."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Response, status

from app.deps import enforce_rate_limit, get_complaint_service
from app.domain.enums import Category, Priority, Status
from app.domain.models import Complaint, ComplaintCreate, ComplaintPage, StatusUpdate
from app.services.complaints import ComplaintService

router = APIRouter(prefix="/api/complaints", tags=["complaints"])

Service = Annotated[ComplaintService, Depends(get_complaint_service)]


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(enforce_rate_limit)],
)
async def create_complaint(
    body: ComplaintCreate, response: Response, service: Service
) -> Complaint:
    complaint = await service.submit(body)
    response.headers["Location"] = f"/api/complaints/{complaint.id}"
    return complaint


@router.get("")
async def list_complaints(
    service: Service,
    category: Category | None = None,
    priority: Priority | None = None,
    status: Status | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ComplaintPage:
    items, total = await service.list_page(
        category=category, priority=priority, status=status, page=page, page_size=page_size
    )
    return ComplaintPage(items=items, total=total, page=page, page_size=page_size)


@router.get("/{id}")
async def get_complaint(id: UUID, service: Service) -> Complaint:
    return await service.get(id)


@router.patch("/{id}/status")
async def change_status(id: UUID, body: StatusUpdate, service: Service) -> Complaint:
    return await service.change_status(id, body.status)
