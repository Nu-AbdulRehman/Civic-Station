"""The one typed settings object (FR-BE-020). No other module reads the environment."""

from typing import Literal, Self

from pydantic import Field, SecretStr, ValidationError, model_validator
from pydantic_settings import BaseSettings

from app.domain.enums import ConfiguredProvider


class Settings(BaseSettings):
    """Mirrors 00-conventions.md §3. Field names map case-insensitively to env vars."""

    database_url: str
    redis_url: str

    triage_provider: ConfiguredProvider = ConfiguredProvider.RULES
    groq_api_key: SecretStr | None = None
    groq_base_url: str = "https://api.groq.com/openai/v1"
    triage_model: str = "llama-3.1-8b-instant"
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:1b"
    # Refused above 15 s: two calls plus jitter must stay under 31 s (BR-TRIAGE-008).
    triage_timeout_seconds: float = Field(default=10, gt=0, le=15)
    triage_cache_ttl_seconds: int = Field(default=86400, gt=0)
    prompt_version: str = "v1"
    simulated_seed: int = 1337
    simulated_failure_mode: Literal["none", "raise", "malformed", "slow"] = "none"

    stats_cache_ttl_seconds: int = Field(default=30, gt=0)
    rate_limit_requests: int = Field(default=10, gt=0)
    rate_limit_window_seconds: int = Field(default=60, gt=0)
    trusted_proxy_cidrs: str = "10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    cors_allow_origins: str = ""
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    app_version: str = "unknown"
    backend_port: int = Field(default=8000, gt=0, lt=65536)
    readiness_timeout_seconds: float = Field(default=1, gt=0)
    seed_uuid_namespace: str = "6f2a1c94-3e5b-4d80-9a17-c0b8e4f21d63"

    @model_validator(mode="after")
    def _groq_key_required_for_llm(self) -> Self:
        if self.triage_provider is ConfiguredProvider.LLM and not self.groq_api_key:
            raise ValueError("GROQ_API_KEY is required when TRIAGE_PROVIDER=llm")
        return self

    @property
    def cors_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_allow_origins.split(",") if o.strip()]


def load_settings() -> Settings:
    """Build settings or exit with a message naming each offending variable (FR-BE-018)."""
    try:
        return Settings()
    except ValidationError as exc:
        problems = "; ".join(
            f"{'.'.join(str(p) for p in err['loc']).upper() or 'SETTINGS'}: {err['msg']}"
            for err in exc.errors()
        )
        raise SystemExit(f"Invalid configuration: {problems}") from None
