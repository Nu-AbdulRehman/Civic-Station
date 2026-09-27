"""The controlled vocabulary, declared once (BR-VOCAB-005).

The migration and the frontend's generated types both derive from these enums.
"""

from enum import StrEnum


class Category(StrEnum):
    """BR-VOCAB-001."""

    WATER = "water"
    ELECTRICITY = "electricity"
    SANITATION = "sanitation"
    ROADS = "roads"
    STREETLIGHTS = "streetlights"
    OTHER = "other"


class Priority(StrEnum):
    """BR-VOCAB-002."""

    HIGH = "high"
    NORMAL = "normal"
    LOW = "low"


class Status(StrEnum):
    """BR-VOCAB-003."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    REJECTED = "rejected"


class TriagedBy(StrEnum):
    """How a classification was actually produced (BR-VOCAB-004, AD-020)."""

    LLM_GROQ = "llm:groq"
    LLM_OLLAMA = "llm:ollama"
    RULES = "rules"
    RULES_FALLBACK = "rules:fallback"
    SIMULATED = "simulated"


class ConfiguredProvider(StrEnum):
    """Legal values of TRIAGE_PROVIDER (FR-BE-018)."""

    LLM = "llm"
    OLLAMA = "ollama"
    RULES = "rules"
    SIMULATED = "simulated"


class ErrorClass(StrEnum):
    """Closed set for the `error_class` metric label and outcome field (00-conventions §6)."""

    TIMEOUT = "Timeout"
    RATE_LIMITED = "RateLimited"
    SERVER_ERROR = "ServerError"
    VALIDATION_FAILED = "ValidationFailed"
    OTHER = "Other"
