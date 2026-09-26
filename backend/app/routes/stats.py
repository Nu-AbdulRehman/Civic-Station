"""GET /api/stats. T-M2-001 stub: zeroes, always MISS. Real cache in T-M2-009."""

from datetime import UTC, datetime

from fastapi import APIRouter, Response

from app.domain.enums import Category, Priority, Status
from app.domain.models import Stats

router = APIRouter(prefix="/api", tags=["stats"])


@router.get("/stats")
async def get_stats(response: Response) -> Stats:
    response.headers["X-Cache"] = "MISS"
    return Stats(
        total=0,
        by_category=dict.fromkeys(Category, 0),
        by_priority=dict.fromkeys(Priority, 0),
        by_status=dict.fromkeys(Status, 0),
        generated_at=datetime.now(UTC),
    )
