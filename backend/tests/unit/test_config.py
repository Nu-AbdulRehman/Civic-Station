import pytest

from app.config import Settings, load_settings

REQUIRED = {
    "DATABASE_URL": "postgresql+asyncpg://u@database/db",
    "REDIS_URL": "redis://cache:6379/0",
}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in REQUIRED.items():
        monkeypatch.setenv(key, value)


def test_unknown_provider_exits_naming_variable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRIAGE_PROVIDER", "nonsense")
    with pytest.raises(SystemExit) as exc:
        load_settings()
    message = str(exc.value)
    assert "TRIAGE_PROVIDER" in message
    assert all(v in message for v in ("llm", "ollama", "rules", "simulated"))


def test_timeout_above_15_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRIAGE_TIMEOUT_SECONDS", "16")
    with pytest.raises(SystemExit, match="TRIAGE_TIMEOUT_SECONDS"):
        load_settings()


def test_llm_requires_key_without_echoing_it(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRIAGE_PROVIDER", "llm")
    with pytest.raises(SystemExit, match="GROQ_API_KEY"):
        load_settings()
    monkeypatch.setenv("GROQ_API_KEY", "sk-test-not-real")
    assert "sk-test-not-real" not in repr(load_settings())


def test_missing_required_variable_named(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DATABASE_URL")
    with pytest.raises(SystemExit, match="DATABASE_URL"):
        load_settings()


def test_every_registry_variable_has_a_setting() -> None:
    names = """DATABASE_URL REDIS_URL TRIAGE_PROVIDER TRIAGE_MODEL OLLAMA_MODEL OLLAMA_BASE_URL
    GROQ_API_KEY GROQ_BASE_URL TRIAGE_TIMEOUT_SECONDS TRIAGE_CACHE_TTL_SECONDS PROMPT_VERSION
    STATS_CACHE_TTL_SECONDS RATE_LIMIT_REQUESTS RATE_LIMIT_WINDOW_SECONDS TRUSTED_PROXY_CIDRS
    READINESS_TIMEOUT_SECONDS CORS_ALLOW_ORIGINS LOG_LEVEL APP_VERSION BACKEND_PORT
    SIMULATED_SEED SIMULATED_FAILURE_MODE SEED_UUID_NAMESPACE""".split()
    assert {n.lower() for n in names} <= set(Settings.model_fields)
