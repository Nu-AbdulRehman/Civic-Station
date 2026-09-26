"""The triage contracts (ADR-0001, FR-AI-001). Services see only these, never a concrete class."""

from dataclasses import dataclass
from typing import Protocol

from app.domain.enums import ErrorClass, TriagedBy
from app.domain.models import TriageResult

__all__ = ["ProviderHTTPError", "TriageOutcome", "TriageProvider", "TriageResult"]


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


class ProviderHTTPError(Exception):
    """A vendor-neutral HTTP failure. Providers translate their SDK's errors into this, so the
    pipeline can classify and retry without importing any vendor library (06-M5 §2.2)."""

    def __init__(self, status_code: int, retry_after_seconds: float | None = None) -> None:
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"provider returned HTTP {status_code}")
