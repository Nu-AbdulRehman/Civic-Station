"""Operational endpoints at the root, where probes and scrapers expect them."""

from fastapi import APIRouter

from app.domain.models import HealthStatus, ReadyStatus

router = APIRouter(tags=["ops"])


@router.get("/health")
async def health() -> HealthStatus:
    """Liveness from process state alone. Touches no dependency (BR-OPS-001)."""
    return HealthStatus()


@router.get("/ready")
async def ready() -> ReadyStatus:
    """T-M2-001: dependency checks stubbed to ok. Real SELECT 1 / PING in T-M2-011."""
    return ReadyStatus(checks={"database": "ok", "cache": "ok"})
