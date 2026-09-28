"""GET /api/stats; `X-Cache` says where the body came from (BR-CACHE-002)."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.deps import get_stats_service
from app.domain.models import Stats
from app.services.stats import StatsService

router = APIRouter(prefix="/api", tags=["stats"])


@router.get(
    "/stats",
    responses={
        200: {
            "headers": {
                "X-Cache": {
                    "description": "HIT if served from Redis, MISS if computed",
                    "schema": {"type": "string", "enum": ["HIT", "MISS"]},
                }
            }
        }
    },
)
async def get_stats(
    response: Response, service: Annotated[StatsService, Depends(get_stats_service)]
) -> Stats:
    stats, hit = await service.get_stats()
    response.headers["X-Cache"] = "HIT" if hit else "MISS"
    return stats
