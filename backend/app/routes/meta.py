"""Provider observability and version. T-M2-001 stubs; real in T-M5-010 / T-M2-011."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings
from app.deps import get_settings
from app.domain.enums import TriagedBy
from app.domain.models import ProvidersMeta, VersionInfo

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta/providers")
async def get_providers(settings: Annotated[Settings, Depends(get_settings)]) -> ProvidersMeta:
    return ProvidersMeta(
        active_provider=TriagedBy.RULES, configured=settings.triage_provider, recent=[]
    )


@router.get("/version")
async def get_version(settings: Annotated[Settings, Depends(get_settings)]) -> VersionInfo:
    return VersionInfo(version=settings.app_version, provider=TriagedBy.RULES)
