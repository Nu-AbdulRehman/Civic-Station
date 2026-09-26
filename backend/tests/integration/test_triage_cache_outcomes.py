"""Triage cache and outcomes list against real Redis (FR-CACHE-004, FR-AI-012, T-M4-006/007)."""

import json
from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from prometheus_client import REGISTRY
from redis.asyncio import Redis

from app.config import Settings
from app.domain.enums import Category, ErrorClass, Priority, TriagedBy
from app.domain.models import ProviderOutcome, TriageResult
from app.providers.cache.client import make_redis
from app.providers.cache.outcomes import RedisOutcomes
from app.providers.cache.triage import RedisTriageCache, triage_cache_key

RESULT = TriageResult(
    category=Category.WATER, priority=Priority.HIGH, summary="water: pipe burst", confidence=0.9
)
DOWN = "redis://127.0.0.1:1/0"


@pytest.fixture
async def redis() -> AsyncIterator[Redis]:
    client = make_redis(Settings().redis_url)
    for pattern in ("cs:triage:*", "cs:outcomes:*"):
        keys = [k async for k in client.scan_iter(pattern)]
        if keys:
            await client.delete(*keys)
    yield client
    await client.aclose()


def _count(name: str) -> float:
    return REGISTRY.get_sample_value(name) or 0.0


# --- key derivation (pure) --------------------------------------------------------------------


def test_key_normalises_case_whitespace_and_surrounding_punctuation() -> None:
    a = triage_cache_key("  Water PIPE   burst!! ", "Saddar.", "simulated", "v1")
    b = triage_cache_key("water pipe burst", "saddar", "simulated", "v1")
    assert a == b and a.startswith("cs:triage:") and len(a) == len("cs:triage:") + 64


@pytest.mark.parametrize(
    "changed",
    [
        ("water pipe burst", "saddar", "rules", "v1"),  # provider
        ("water pipe burst", "saddar", "simulated", "v2"),  # prompt version
        ("water pipe burst", "clifton", "simulated", "v1"),  # location
        ("water main burst", "saddar", "simulated", "v1"),  # text
    ],
)
def test_key_changes_with_every_input(changed: tuple[str, str, str, str]) -> None:
    assert triage_cache_key(*changed) != triage_cache_key(
        "water pipe burst", "saddar", "simulated", "v1"
    )


def test_key_fields_cannot_run_together() -> None:
    assert triage_cache_key("a b", "c", "p", "v1") != triage_cache_key("a", "b c", "p", "v1")


# --- triage cache ------------------------------------------------------------------------------


async def test_miss_then_hit_with_provider_and_ttl(redis: Redis) -> None:
    cache = RedisTriageCache(redis, ttl_seconds=86400)
    key = triage_cache_key("water pipe burst", "saddar", "llm:groq", "v1")
    hits, misses = _count("triage_cache_hits_total"), _count("triage_cache_misses_total")

    assert await cache.get(key) is None
    await cache.set(key, RESULT, TriagedBy.LLM_GROQ)
    assert await cache.get(key) == (RESULT, TriagedBy.LLM_GROQ)

    assert _count("triage_cache_hits_total") == hits + 1
    assert _count("triage_cache_misses_total") == misses + 1
    assert 86000 < await redis.ttl(key) <= 86400


async def test_triage_cache_redis_down_is_a_skip_not_an_error() -> None:
    cache = RedisTriageCache(make_redis(DOWN), ttl_seconds=60)
    misses = _count("triage_cache_misses_total")
    assert await cache.get("cs:triage:x") is None
    await cache.set("cs:triage:x", RESULT, TriagedBy.SIMULATED)
    assert _count("triage_cache_misses_total") == misses


# --- outcomes ----------------------------------------------------------------------------------


def _outcome(i: int, fallback: bool = False) -> ProviderOutcome:
    return ProviderOutcome(
        complaint_id=uuid4(),
        provider=TriagedBy.RULES_FALLBACK if fallback else TriagedBy.SIMULATED,
        latency_ms=i,
        fallback=fallback,
        error_class=ErrorClass.TIMEOUT if fallback else None,
        confidence=0.9,
        at=datetime(2026, 9, 26, tzinfo=UTC) + timedelta(seconds=i),
    )


async def test_outcomes_keep_the_newest_twenty(redis: Redis) -> None:
    outcomes = RedisOutcomes(redis, prompt_version="v1")
    for i in range(25):
        await outcomes.record(_outcome(i, fallback=(i == 24)))
    recent = await outcomes.recent()
    assert [o.latency_ms for o in recent] == list(range(24, 4, -1))
    assert recent[0].fallback and recent[0].error_class is ErrorClass.TIMEOUT
    assert await redis.llen("cs:outcomes:v1") == 20


async def test_outcome_entries_carry_exactly_six_fields(redis: Redis) -> None:
    await RedisOutcomes(redis, prompt_version="v1").record(_outcome(1))
    raw = await redis.lindex("cs:outcomes:v1", 0)
    assert raw is not None
    assert set(json.loads(raw)) == {
        "complaint_id", "provider", "latency_ms", "fallback", "error_class", "at",
    }  # fmt: skip


async def test_prompt_version_change_starts_an_empty_list(redis: Redis) -> None:
    await RedisOutcomes(redis, prompt_version="v1").record(_outcome(1))
    assert await RedisOutcomes(redis, prompt_version="v2").recent() == []


async def test_outcomes_redis_down() -> None:
    outcomes = RedisOutcomes(make_redis(DOWN), prompt_version="v1")
    await outcomes.record(_outcome(1))
    assert await outcomes.recent() == []
