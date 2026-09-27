"""Redact formatted identifiers before complaint text leaves the process (ADR-0004, AD-003).

Deterministic by construction (pure regex substitution), because the triage cache key is
computed on this output (AD-019). Catches formatted identifiers only, never names in prose:
it reduces exposure, it does not eliminate it.
"""

import re

# Order matters: emails before numbers (digits inside an address), phones before generic runs.
_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), "[EMAIL]"),
    # Mobile 03xx-xxxxxxx, +92 3xx..., and landlines like 021-34567890.
    (re.compile(r"(?:\+92[\s-]?|\b0)\d{2,3}[\s-]?\d{7,8}\b"), "[PHONE]"),
    (re.compile(r"\b\d{5}-\d{7}-\d\b"), "[NUMBER]"),  # CNIC
    (re.compile(r"\b\d{7,}\b"), "[NUMBER]"),  # account-shaped runs; house numbers survive
)


def redact(text: str) -> str:
    for pattern, placeholder in _RULES:
        text = pattern.sub(placeholder, text)
    return text
