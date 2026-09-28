"""RuleBasedTriage: the deterministic floor under every other provider (FR-AI-003, BR-TRIAGE-009).

No network, no dependency, and no input for which it raises: if the fallback can fail, there
is no fallback. The whole vocabulary lives in the mappings below so it is reviewable in one place.
"""

import re

from app.domain.enums import Category, Priority
from app.domain.models import SUMMARY_MAX_LENGTH, TriageResult

CONFIDENCE = 0.35  # AD-026: a keyword match is weak evidence, and the number says so.

# First match wins, in this order; no match is `other`. Streetlights precede electricity
# ("streetlight ... electricity wasting") and sanitation precedes water ("sewage water").
CATEGORY_KEYWORDS: tuple[tuple[Category, tuple[str, ...]], ...] = (
    (Category.STREETLIGHTS, ("streetlight", "street light", "pole light", "lamp post", "bulb")),
    (
        Category.ELECTRICITY,
        ("electric", "bijli", "load shedding", "loadshedding", "transformer", "live wire",
         "wire", "voltage", "meter", "k-electric", "pole", "power"),
    ),
    (
        Category.SANITATION,
        ("sewage", "sewerage", "gutter", "manhole", "nala", "garbage", "kachra", "trash",
         "drain", "sweeper", "litter"),
    ),
    (
        Category.WATER,
        ("water", "pipe", "nalka", "tanker", "tanki", "leakage", "leak", "kwsc", "supply"),
    ),
    (
        Category.ROADS,
        ("road", "pothole", "footpath", "speed breaker", "sadak", "bridge", "signal", "traffic"),
    ),
)  # fmt: skip

# Escalation is checked before minor, so "streetlight pole collapsed" is high.
PRIORITY_KEYWORDS: tuple[tuple[Priority, tuple[str, ...]], ...] = (
    (
        Priority.HIGH,
        ("burst", "flood", "sewage", "live wire", "electrocut", "collapse", "gas leak",
         "overflow", "danger", "children", "fire", "no water since", "khatarnak", "aag"),
    ),
    (
        Priority.LOW,
        ("streetlight", "street light", "bulb", "flicker", "paint", "signboard", "litter",
         "pothole$"),
    ),
)  # fmt: skip


def _pattern(keyword: str) -> re.Pattern[str]:
    """Word-start match, so `flood` covers `flooding` and `electrocut` covers `electrocuted`.
    A trailing `$` means whole word only: `pothole` but not `potholes` (06-M5 §2.5)."""
    if keyword.endswith("$"):
        return re.compile(rf"\b{re.escape(keyword[:-1])}\b")
    return re.compile(rf"\b{re.escape(keyword)}")


_CATEGORY_RULES = [(c, [_pattern(k) for k in ks]) for c, ks in CATEGORY_KEYWORDS]
_PRIORITY_RULES = [(p, [_pattern(k) for k in ks]) for p, ks in PRIORITY_KEYWORDS]
_TERMINATOR = re.compile(r"[.!?\n]")


def normalise(text: str) -> str:
    return " ".join(text.lower().split())


def summarise(category: str, text: str) -> str:
    """AD-023: first sentence or 120 chars, whichever is shorter; whitespace collapsed;
    `<category>: ` prefix; whole result cut to 140 on a word boundary."""
    end = _TERMINATOR.search(text)
    first = " ".join((text[: end.start()] if end else text)[:120].split())
    summary = f"{category}: {first}".strip()
    if len(summary) > SUMMARY_MAX_LENGTH:
        summary = summary[:SUMMARY_MAX_LENGTH].rsplit(" ", 1)[0]
    return summary


def classify(text: str) -> TriageResult:
    normalised = normalise(text)
    category = next(
        (c for c, patterns in _CATEGORY_RULES if any(p.search(normalised) for p in patterns)),
        Category.OTHER,
    )
    priority = next(
        (p for p, patterns in _PRIORITY_RULES if any(r.search(normalised) for r in patterns)),
        Priority.NORMAL,
    )
    return TriageResult(
        category=category,
        priority=priority,
        summary=summarise(category.value, text),
        confidence=CONFIDENCE,
    )


# The one result that cannot fail validation, for the input nothing above anticipated.
_LAST_RESORT = TriageResult(
    category=Category.OTHER, priority=Priority.NORMAL, summary="other", confidence=CONFIDENCE
)


class RuleBasedTriage:
    name = "rules"

    async def triage(self, text: str, location: str) -> TriageResult:
        try:
            return classify(text)
        except Exception:  # BR-TRIAGE-009: the floor never raises, whatever it is given.
            return _LAST_RESORT
