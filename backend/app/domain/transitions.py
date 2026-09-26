"""The status machine as data (BR-STATUS-002/004).

Terminal states map to an empty set; self-transitions appear in no entry.
Adding a status is an edit to this table plus a migration, never a new branch.
"""

from collections.abc import Mapping
from types import MappingProxyType

from app.domain.enums import Status
from app.domain.errors import InvalidTransitionError

TRANSITIONS: Mapping[Status, frozenset[Status]] = MappingProxyType(
    {
        Status.OPEN: frozenset({Status.IN_PROGRESS, Status.REJECTED}),
        Status.IN_PROGRESS: frozenset({Status.RESOLVED, Status.REJECTED}),
        Status.RESOLVED: frozenset(),
        Status.REJECTED: frozenset(),
    }
)


def ensure_transition_allowed(current: Status, target: Status) -> None:
    """The one function that consults the table. Raises InvalidTransitionError."""
    if target not in TRANSITIONS[current]:
        raise InvalidTransitionError(current, target)
