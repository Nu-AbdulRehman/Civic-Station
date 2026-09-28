"""Readiness: is every dependency serving needs reachable right now? (BR-OPS-002, FR-BE-008)"""

import asyncio
from collections.abc import Awaitable, Callable, Mapping
from typing import Literal

Check = Callable[[], Awaitable[None]]
Result = Literal["ok", "fail"]


class ReadinessService:
    def __init__(self, checks: Mapping[str, Check], timeout_seconds: float) -> None:
        self._checks = checks
        self._timeout = timeout_seconds

    async def check(self) -> dict[str, Result]:
        """All checks run concurrently, so the worst case is one timeout, not the sum."""
        names = list(self._checks)
        results = await asyncio.gather(*(self._one(self._checks[n]) for n in names))
        return dict(zip(names, results, strict=True))

    async def _one(self, check: Check) -> Result:
        try:
            await asyncio.wait_for(check(), self._timeout)
        except Exception:  # a timeout counts as unreachable
            return "fail"
        return "ok"
