"""TRIAGE_PROVIDER -> instance, once, at startup (FR-AI-002, FR-BE-018, BR-TRIAGE-002).

The only module outside the implementations that names a concrete provider class. An unknown
value never reaches here: `Settings` rejects it at startup with the legal values listed.
"""

from app.config import Settings
from app.domain.enums import ConfiguredProvider
from app.providers.triage.base import TriageProvider
from app.providers.triage.llm import LLMTriage
from app.providers.triage.rules import RuleBasedTriage
from app.providers.triage.simulated import SimulatedTriage


def build_triage_provider(settings: Settings) -> TriageProvider:
    match settings.triage_provider:
        case ConfiguredProvider.RULES:
            return RuleBasedTriage()
        case ConfiguredProvider.SIMULATED:
            return SimulatedTriage(settings.simulated_seed, settings.simulated_failure_mode)
        case ConfiguredProvider.LLM:
            return LLMTriage(settings)
        case ConfiguredProvider.OLLAMA:
            # ponytail: fails loudly until OllamaTriage (T-M5-009) lands; never a silent
            # default to a provider the operator did not ask for.
            raise SystemExit(
                f"TRIAGE_PROVIDER={settings.triage_provider.value} is not implemented yet."
            )
