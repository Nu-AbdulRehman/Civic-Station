"""The observability surface behind GET /api/meta/providers (FR-BE-006, FR-AI-012)."""

from app.domain.enums import ConfiguredProvider, TriagedBy
from app.domain.models import ProvidersMeta
from app.providers.cache.ports import OutcomesPort


class ProvidersService:
    def __init__(
        self, configured: ConfiguredProvider, active: TriagedBy, outcomes: OutcomesPort
    ) -> None:
        self._configured = configured  # what the operator asked for
        self._active = active  # what actually runs; /api/version reports the same value
        self._outcomes = outcomes

    async def describe(self) -> ProvidersMeta:
        return ProvidersMeta(
            active_provider=self._active,
            configured=self._configured,
            recent=await self._outcomes.recent(),  # global across pods (AD-009)
        )
