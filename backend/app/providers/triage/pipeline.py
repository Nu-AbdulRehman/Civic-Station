"""The resilience pipeline: the one place timeout, retry, validation and fallback live (ADR-0001).

    run():    redact -> cache key -> cache get -> provider under a hard timeout
              -> at most one jittered retry (timeout / 429 / 5xx only) -> re-validate
              -> any failure: RuleBasedTriage as "rules:fallback" -> cache set (success only)
    report(): after the row exists -> one triage.fallback WARNING -> cs:outcomes   (AD-061)

Nothing a provider does can escape `run()` as an exception: every failure ends in the rules
floor, which itself never raises (BR-TRIAGE-005/006/009). CancelledError is a BaseException
and is deliberately not caught, so a client disconnect or shutdown still cancels cleanly.
"""

import asyncio
import math
import random
import time
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from uuid import UUID

from pydantic import ValidationError

from app.domain.enums import ErrorClass, TriagedBy
from app.domain.models import ProviderOutcome, TriageResult
from app.observability.logging import get_logger
from app.observability.metrics import TRIAGE_DURATION, TRIAGE_FALLBACK
from app.providers.cache.ports import OutcomesPort, TriageCachePort
from app.providers.cache.triage import triage_cache_key
from app.providers.triage.base import (
    ProviderHTTPError,
    TriageOutcome,
    TriageProvider,
)
from app.providers.triage.redact import redact
from app.providers.triage.rules import RuleBasedTriage

RETRY_AFTER_CAP_SECONDS = 5.0
JITTER_SECONDS = (0.25, 1.0)

log = get_logger(__name__)


class _Failure(Exception):
    """Internal: a provider attempt failed, with its closed-set class and retry decision."""

    def __init__(self, error_class: ErrorClass, retry_delay: float | None) -> None:
        self.error_class = error_class
        self.retry_delay = retry_delay  # None = not retryable


class TriagePipeline:
    def __init__(
        self,
        provider: TriageProvider,
        cache: TriageCachePort,
        outcomes: OutcomesPort,
        *,
        timeout_seconds: float,
        prompt_version: str,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        jitter: Callable[[float, float], float] = random.uniform,
        clock: Callable[[], float] = time.perf_counter,
    ) -> None:
        self._provider = provider
        self._fallback = RuleBasedTriage()
        self._cache = cache
        self._outcomes = outcomes
        self._timeout = timeout_seconds
        self._prompt_version = prompt_version
        self._sleep = sleep
        self._jitter = jitter
        self._clock = clock

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def run(self, text: str, location: str) -> TriageOutcome:
        """Never raises for anything a provider does. Worst case: timeout + 1 s + timeout."""
        started = self._clock()
        redacted = redact(text)  # first: the cache key and the prompt see the same content
        key = triage_cache_key(redacted, location, self._provider.name, self._prompt_version)

        cached = await self._cache_get(key)
        if cached is not None:
            result, provider = cached
            return self._finish(started, result, provider, fallback=False)

        try:
            result = await self._call_with_retry(redacted, location)
        except _Failure as failure:
            TRIAGE_FALLBACK.labels(self._provider.name, failure.error_class.value).inc()
            result = await self._fallback.triage(redacted, location)
            return self._finish(
                started, result, TriagedBy.RULES_FALLBACK, True, failure.error_class
            )

        provider = TriagedBy(self._provider.name)
        await self._cache.set(key, result, provider)  # only a real provider result is cached
        return self._finish(started, result, provider, fallback=False)

    async def report(self, outcome: TriageOutcome, complaint_id: UUID) -> None:
        """After persistence: the fallback WARNING can now name the complaint (AD-061)."""
        if outcome.fallback:
            log.warning(
                "triage.fallback",
                complaint_id=str(complaint_id),
                from_provider=self._provider.name,
                provider=outcome.triaged_by.value,
                error_class=outcome.error_class.value if outcome.error_class else None,
            )
        await self._outcomes.record(
            ProviderOutcome(
                complaint_id=complaint_id,
                provider=outcome.triaged_by,
                latency_ms=outcome.latency_ms,
                fallback=outcome.fallback,
                error_class=outcome.error_class,
                at=datetime.now(UTC),
            )
        )

    async def _cache_get(self, key: str) -> tuple[TriageResult, TriagedBy] | None:
        try:
            return await self._cache.get(key)
        except Exception:
            # An unreadable entry (say, written by an older schema) is a miss, not an outage.
            log.info("triage.cache_entry_unreadable")
            return None

    async def _call_with_retry(self, text: str, location: str) -> TriageResult:
        try:
            return await self._attempt(text, location)
        except _Failure as failure:
            if failure.retry_delay is None:
                raise
            log.info("triage.retry", error_class=failure.error_class.value)
            await self._sleep(failure.retry_delay)
            return await self._attempt(text, location)  # at most once (BR-TRIAGE-007)

    async def _attempt(self, text: str, location: str) -> TriageResult:
        try:
            async with asyncio.timeout(self._timeout):  # no untimed call (BR-TRIAGE-008)
                result = await self._provider.triage(text, location)
            # AD-060: re-validate whatever came back, so nothing built with model_construct
            # or otherwise unchecked can reach the database.
            return TriageResult.model_validate(result.model_dump())
        except Exception as exc:
            raise self._classify(exc) from exc

    def _classify(self, exc: Exception) -> _Failure:
        """Map any exception to the closed ErrorClass set and a retry decision. A validation
        failure is never retried (AD-007); neither is a 4xx other than 429."""
        if isinstance(exc, TimeoutError):
            return _Failure(ErrorClass.TIMEOUT, self._jitter(*JITTER_SECONDS))
        if isinstance(exc, ValidationError):
            log.info("triage.validation_failed", error_count=exc.error_count())
            return _Failure(ErrorClass.VALIDATION_FAILED, None)
        if isinstance(exc, ProviderHTTPError):
            if exc.status_code == 429:
                delay = (
                    min(exc.retry_after_seconds, RETRY_AFTER_CAP_SECONDS)
                    if exc.retry_after_seconds is not None
                    else self._jitter(*JITTER_SECONDS)
                )
                return _Failure(ErrorClass.RATE_LIMITED, max(delay, 0.0))
            if exc.status_code >= 500:
                return _Failure(ErrorClass.SERVER_ERROR, self._jitter(*JITTER_SECONDS))
        return _Failure(ErrorClass.OTHER, None)

    def _finish(
        self,
        started: float,
        result: TriageResult,
        provider: TriagedBy,
        fallback: bool,
        error_class: ErrorClass | None = None,
    ) -> TriageOutcome:
        elapsed = self._clock() - started
        # Never zero-as-sentinel: a cache hit records a small non-zero value (FR-AI-009).
        latency_ms = max(1, math.ceil(elapsed * 1000))
        TRIAGE_DURATION.labels(provider.value).observe(elapsed)
        log.info(
            "triage.completed",
            provider=provider.value,
            duration_ms=latency_ms,
            confidence=result.confidence,
            fallback=fallback,
        )
        return TriageOutcome(result, provider, latency_ms, fallback, error_class)
