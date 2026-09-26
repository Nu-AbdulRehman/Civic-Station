"""Provider observability and version. `recent` is wired to cs:outcomes in T-M5-010."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings
from app.deps import get_settings, get_triage_provider
from app.domain.enums import TriagedBy
from app.domain.models import ProvidersMeta, VersionInfo
from app.providers.triage.base import TriageProvider

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta/providers")
async def get_providers(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[TriageProvider, Depends(get_triage_provider)],
) -> ProvidersMeta:
    return ProvidersMeta(
        active_provider=TriagedBy(provider.name), configured=settings.triage_provider, recent=[]
    )


@router.get("/version")
async def get_version(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[TriageProvider, Depends(get_triage_provider)],
) -> VersionInfo:
    """`provider` is the active identity, the same value /api/meta/providers reports (FR-BE-029)."""
    return VersionInfo(version=settings.app_version, provider=TriagedBy(provider.name))
