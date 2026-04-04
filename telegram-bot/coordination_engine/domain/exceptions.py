"""Domain exceptions — no dependencies on frameworks or infrastructure."""


class DomainError(Exception):
    """Base for all domain errors."""


class EntityNotFoundError(DomainError):
    pass


class InvalidTransitionError(DomainError):
    """Raised when an event state transition is not allowed."""


class ConcurrencyError(DomainError):
    """Raised when optimistic concurrency check fails (version mismatch)."""


class BusinessRuleViolation(DomainError):
    """Raised when a business rule is violated."""


class ThresholdNotMetError(BusinessRuleViolation):
    """Event cannot be locked — minimum participants not reached."""


class EventLockedError(BusinessRuleViolation):
    """Event is locked — no further modifications allowed."""


class ParticipantActionNotAllowedError(BusinessRuleViolation):
    """User cannot perform this action on the event."""
