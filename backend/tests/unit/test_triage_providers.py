"""M5 contracts, rules, simulated, redaction, factory (T-M5-001…005)."""

import asyncio

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.config import Settings
from app.domain.enums import Category, ConfiguredProvider, Priority
from app.domain.models import TriageResult
from app.providers.triage.factory import build_triage_provider
from app.providers.triage.redact import redact
from app.providers.triage.rules import RuleBasedTriage, classify, summarise
from app.providers.triage.simulated import SimulatedProviderError, SimulatedTriage

# --- T-M5-001 -------------------------------------------------------------------------------


@pytest.mark.parametrize("override", [{"summary": "x" * 141}, {"confidence": 1.5}])
def test_triage_result_rejects(override: dict[str, object]) -> None:
    good = {"category": "water", "priority": "high", "summary": "ok", "confidence": 0.5}
    with pytest.raises(ValidationError):
        TriageResult.model_validate(good | override)


# --- T-M5-002: RuleBasedTriage ---------------------------------------------------------------

ADVERSARIAL = [
    "",
    "     \n\t   ",
    "?!?!.,;:-- ... !!!",
    "a" * 10,
    "Water pipe burst. " * 111 + "xx",  # exactly 2000 characters
    "Nothing here matches any keyword whatsoever",
    "پانی کی پائپ لائن پھٹ گئی ہے اور گلی میں پانی بھر گیا ہے",  # Urdu script
    "水管爆裂，街道被淹",
    "\x00\x01\x02 control characters \x7f",
    "🚰💥🌊" * 50,
]


@pytest.mark.parametrize("text", ADVERSARIAL)
async def test_rules_never_raise_and_always_validate(text: str) -> None:
    result = await RuleBasedTriage().triage(text, "Saddar")
    TriageResult.model_validate(result.model_dump())
    assert result.confidence == 0.35


def test_adversarial_set_includes_the_2000_character_edge() -> None:
    assert len(ADVERSARIAL[4]) == 2000


@pytest.mark.parametrize(
    ("text", "category", "priority"),
    [
        ("Burst water main flooding Street 12 since fajr", Category.WATER, Priority.HIGH),
        ("Gutter overflow, sewage water standing near school", Category.SANITATION, Priority.HIGH),
        ("Live wire hanging from pole after storm", Category.ELECTRICITY, Priority.HIGH),
        ("Load shedding 10 hours daily in our area", Category.ELECTRICITY, Priority.NORMAL),
        ("Streetlight not working for two weeks", Category.STREETLIGHTS, Priority.LOW),
        ("Streetlight pole collapsed on the road", Category.STREETLIGHTS, Priority.HIGH),
        ("Single pothole near bus stop", Category.ROADS, Priority.LOW),
        ("Many potholes near bus stop", Category.ROADS, Priority.NORMAL),
        ("Manhole cover missing, children playing there", Category.SANITATION, Priority.HIGH),
        ("Nala choked with plastic behind houses", Category.SANITATION, Priority.NORMAL),
        ("Stray dogs near the school gate", Category.OTHER, Priority.NORMAL),
    ],
)
def test_rules_keywords(text: str, category: Category, priority: Priority) -> None:
    result = classify(text)
    assert (result.category, result.priority) == (category, priority)


def test_summary_algorithm() -> None:
    assert summarise("water", "Pipe burst. Street flooded!") == "water: Pipe burst"
    assert summarise("water", "no   terminator\there") == "water: no terminator here"
    long = summarise("streetlights", "word " * 60)
    assert len(long) <= 140 and long.startswith("streetlights: word")
    assert len(summarise("other", "x" * 500)) <= 140


def test_rules_are_deterministic() -> None:
    text = "Transformer making loud noise and sparks since Tuesday"
    assert classify(text) == classify(text)


# --- T-M5-003: SimulatedTriage ---------------------------------------------------------------


async def test_simulated_is_deterministic_per_seed() -> None:
    a = await SimulatedTriage(seed=1337).triage("Water pipe burst", "Saddar")
    b = await SimulatedTriage(seed=1337).triage("Water pipe burst", "Saddar")
    assert a.model_dump_json() == b.model_dump_json()
    others = {
        (await SimulatedTriage(seed=s).triage("Water pipe burst", "Saddar")).model_dump_json()
        for s in range(10)
    }
    assert len(others) > 1  # the seed actually matters


async def test_simulated_output_is_pinned_across_processes() -> None:
    """Pinned, because a salted hash() would pass the in-process test above and still differ
    between two CI runs (FR-AI-004: identical across runs and processes)."""
    result = await SimulatedTriage(seed=1337).triage("Water pipe burst", "Saddar")
    assert result.model_dump_json() == (
        '{"category":"electricity","priority":"normal","summary":"Water pipe burst",'
        '"confidence":0.78}'
    )


async def test_simulated_raise_mode() -> None:
    with pytest.raises(SimulatedProviderError):
        await SimulatedTriage(1337, "raise").triage("Water pipe burst", "Saddar")


async def test_simulated_malformed_mode_fails_validation() -> None:
    with pytest.raises(ValidationError):
        await SimulatedTriage(1337, "malformed").triage("Water pipe burst", "Saddar")


async def test_simulated_slow_mode_never_completes_on_its_own() -> None:
    task = asyncio.create_task(SimulatedTriage(1337, "slow").triage("Water pipe burst", "x"))
    done, _ = await asyncio.wait({task}, timeout=0.05)
    assert not done
    task.cancel()


# --- T-M5-005: redact -------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Call me on 0300-1234567 please", "Call me on [PHONE] please"),
        ("Call 03001234567 now", "Call [PHONE] now"),
        ("Number +92 300 1234567", "Number [PHONE]"),
        ("Office 021-34567890", "Office [PHONE]"),
        ("Mail ahmed.k@example.com today", "Mail [EMAIL] today"),
        ("CNIC 42101-1234567-1 attached", "CNIC [NUMBER] attached"),
        ("Account 12345678901 blocked", "Account [NUMBER] blocked"),
        ("House number 45, Street 12, Block 13-D", "House number 45, Street 12, Block 13-D"),
    ],
)
def test_redact(text: str, expected: str) -> None:
    assert redact(text) == expected


def test_redact_is_deterministic_and_idempotent() -> None:
    text = "Voltage issue, call 0300-1234567 or mail a@b.pk, CNIC 42101-1234567-1"
    once = redact(text)
    assert once == redact(text) == redact(once)
    assert "0300" not in once and "@" not in once and "42101" not in once


# --- T-M5-004: factory ------------------------------------------------------------------------


def _settings(**overrides: object) -> Settings:
    return Settings(database_url="x", redis_url="y", **overrides)  # type: ignore[arg-type]


def test_factory_resolves_by_configuration() -> None:
    assert build_triage_provider(_settings(triage_provider="rules")).name == "rules"
    assert build_triage_provider(_settings(triage_provider="simulated")).name == "simulated"


@pytest.mark.parametrize("value", [ConfiguredProvider.LLM, ConfiguredProvider.OLLAMA])
def test_factory_refuses_unimplemented_providers_loudly(value: ConfiguredProvider) -> None:
    extra = {"groq_api_key": "k"} if value is ConfiguredProvider.LLM else {}
    with pytest.raises(SystemExit, match=f"TRIAGE_PROVIDER={value.value}"):
        build_triage_provider(_settings(triage_provider=value, **extra))


def test_version_and_meta_report_the_active_provider(client: TestClient) -> None:
    assert client.get("/api/version").json()["provider"] == "rules"
    meta = client.get("/api/meta/providers").json()
    assert meta["active_provider"] == "rules" and meta["configured"] == "rules"
