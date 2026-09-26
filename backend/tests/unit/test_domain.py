import itertools

import pytest
from pydantic import ValidationError

from app.domain.enums import Status
from app.domain.errors import InvalidTransitionError
from app.domain.models import ComplaintCreate, TriageResult
from app.domain.transitions import ensure_transition_allowed

ALLOWED = {
    (Status.OPEN, Status.IN_PROGRESS),
    (Status.OPEN, Status.REJECTED),
    (Status.IN_PROGRESS, Status.RESOLVED),
    (Status.IN_PROGRESS, Status.REJECTED),
}


@pytest.mark.parametrize(("current", "target"), list(itertools.product(Status, Status)))
def test_transition_table_every_pair(current: Status, target: Status) -> None:
    if (current, target) in ALLOWED:
        ensure_transition_allowed(current, target)
    else:
        with pytest.raises(InvalidTransitionError) as exc:
            ensure_transition_allowed(current, target)
        assert f"'{current}'" in str(exc.value) and f"'{target}'" in str(exc.value)


@pytest.mark.parametrize("field", ["category", "priority", "status", "id"])
def test_create_rejects_client_supplied_fields(field: str) -> None:
    with pytest.raises(ValidationError) as exc:
        ComplaintCreate.model_validate({"text": "Water pipe burst", "location": "G-9", field: "x"})
    assert exc.value.errors()[0]["loc"] == (field,)


def test_create_length_counts_after_trimming() -> None:
    with pytest.raises(ValidationError):
        ComplaintCreate(text="   123456789   ", location="G-9")
    assert ComplaintCreate(text=" 1234567890 ", location="G-9").text == "1234567890"


@pytest.mark.parametrize(
    "override", [{"summary": "x" * 141}, {"confidence": 1.5}, {"category": "Water"}]
)
def test_triage_result_rejects_bad_model_output(override: dict[str, object]) -> None:
    good = {"category": "water", "priority": "high", "summary": "ok", "confidence": 0.9}
    with pytest.raises(ValidationError):
        TriageResult.model_validate(good | override)
