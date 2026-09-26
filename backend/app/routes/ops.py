"""Operational endpoints at the root, where probes and scrapers expect them."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends

from app.deps import get_readiness_service
from app.domain.models import HealthStatus, ReadyStatus
from app.errors import error_response
from app.services.readiness import ReadinessService

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health() -> HealthStatus:
    """Liveness from process state alone. No database, no Redis, nothing outbound (BR-OPS-001):
    a liveness probe that touches PostgreSQL turns a slow database into a restart loop."""
    return HealthStatus()


@router.get(
    "/ready", responses={503: {"description": "A dependency is unreachable; names which one"}}
)
async def ready(
    service: Annotated[ReadinessService, Depends(get_readiness_service)],
) -> Any:
    checks = await service.check()
    failed = [name for name, result in checks.items() if result == "fail"]
    if failed:  # 503 removes the pod from the Service; it does not restart it (BR-OPS-002)
        message = f"{', '.join(failed)} unreachable"
        return error_response(503, "dependency_unavailable", message, extra={"checks": checks})
    return ReadyStatus(checks=checks)
