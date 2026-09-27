"""SimulatedTriage: deterministic, network-free, with failure injection (FR-AI-004).

How a probabilistic dependency is tested by design rather than by luck: CI pins this provider
and chooses the failure with SIMULATED_FAILURE_MODE instead of hoping a live model misbehaves.
"""

import asyncio
import hashlib
import random
from typing import Literal

from app.domain.enums import Category, Priority
from app.domain.models import TriageResult

FailureMode = Literal["none", "raise", "malformed", "slow"]


class SimulatedProviderError(Exception):
    """What `raise` mode raises: stands in for any provider-side failure."""


class SimulatedTriage:
    name = "simulated"

    def __init__(self, seed: int, failure_mode: FailureMode = "none") -> None:
        self._seed = seed
        self._mode = failure_mode

    async def triage(self, text: str, location: str) -> TriageResult:
        if self._mode == "raise":
            raise SimulatedProviderError("simulated provider failure")
        if self._mode == "slow":
            await asyncio.Event().wait()  # never completes; the pipeline's timeout ends it
        # sha256, not hash(): Python salts str hashes per process, and the output must be
        # identical across runs and processes.
        digest = hashlib.sha256(f"{self._seed}\x00{text}\x00{location}".encode()).digest()
        rng = random.Random(digest)  # noqa: S311 - not security; a reproducible fake
        raw: dict[str, object] = {
            "category": rng.choice(list(Category)).value,
            "priority": rng.choice(list(Priority)).value,
            "summary": " ".join(text.split())[:100] or "simulated",
            "confidence": round(rng.uniform(0.5, 0.99), 2),
        }
        if self._mode == "malformed":
            # What a misbehaving model returns: an out-of-enum value and an overlong summary.
            raw |= {"category": "urgent", "summary": "x" * 400}
        return TriageResult.model_validate(raw)  # AD-060: validate at the provider boundary
