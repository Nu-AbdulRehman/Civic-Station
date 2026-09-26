"""The triage contracts (ADR-0001, FR-AI-001). Services see only these, never a concrete class."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import ErrorClass, TriagedBy
from app.domain.models import TriageResult

__all__ = ["TriageOutcome", "TriageProvider", "TriageResult"]


class TriageProvider(Protocol):
    """`name` is the `triaged_by` identity the provider reports (`llm:groq`, `rules`, ...).

    Implementations validate their raw output with `TriageResult.model_validate`, so bad model
    output surfaces as pydantic's ValidationError (AD-060). `reporter_contact` is not a
    parameter: it is excluded structurally, not by discipline (BR-TRIAGE-015)."""

    @property
    def name(self) -> str: ...

    async def triage(self, text: str, location: str) -> TriageResult: ...


@dataclass(frozen=True)
class TriageOutcome:
    """What the pipeline hands the service. The service persists it; it computes none of it."""

    result: TriageResult
    triaged_by: TriagedBy
    latency_ms: int
    fallback: bool
    error_class: ErrorClass | None = None
