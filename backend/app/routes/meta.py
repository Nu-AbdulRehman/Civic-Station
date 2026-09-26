"""Provider observability and the running version."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.config import Settings
from app.deps import get_providers_service, get_settings, get_triage_provider
from app.domain.enums import TriagedBy
from app.domain.models import ProvidersMeta, VersionInfo
from app.providers.triage.base import TriageProvider
from app.services.meta import ProvidersService

router = APIRouter(prefix="/api", tags=["meta"])


@router.get("/meta/providers")
async def get_providers(
    service: Annotated[ProvidersService, Depends(get_providers_service)],
) -> ProvidersMeta:
    return await service.describe()


@router.get("/version")
async def get_version(
    settings: Annotated[Settings, Depends(get_settings)],
    provider: Annotated[TriageProvider, Depends(get_triage_provider)],
) -> VersionInfo:
    """`provider` is the active identity, the same value /api/meta/providers reports (FR-BE-029)."""
    return VersionInfo(version=settings.app_version, provider=TriagedBy(provider.name))
