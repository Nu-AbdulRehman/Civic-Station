"""Domain errors. Mapped to HTTP once, by the registered exception handlers."""

from uuid import UUID


class DomainError(Exception):
    """Base for every error a service may raise."""


class ComplaintNotFoundError(DomainError):
    def __init__(self, complaint_id: UUID) -> None:
        self.complaint_id = complaint_id
        super().__init__(f"Complaint '{complaint_id}' was not found.")


class InvalidTransitionError(DomainError):
    """The 409 message is authored here and nowhere else (BR-STATUS-005)."""

    def __init__(self, current: str, target: str) -> None:
        self.current = current
        self.target = target
        super().__init__(f"Cannot transition complaint from '{current}' to '{target}'.")


class RateLimitExceededError(DomainError):
    def __init__(self, retry_after_seconds: int) -> None:
        self.retry_after_seconds = retry_after_seconds
        super().__init__(f"Too many submissions. Retry after {retry_after_seconds} seconds.")
