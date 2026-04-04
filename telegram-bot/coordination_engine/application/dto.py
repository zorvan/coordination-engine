"""DTOs — data carriers between layers. No business logic."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


# ---------------------------------------------------------------------------
# Event DTOs
# ---------------------------------------------------------------------------

@dataclass
class CreateEventCommand:
    group_telegram_id: int
    organizer_telegram_id: int
    event_type: str = "social"
    description: str = ""
    scheduled_time: datetime | None = None
    collapse_at: datetime | None = None
    commit_by: datetime | None = None
    duration_minutes: int = 120
    threshold_attendance: int = 3
    min_participants: int = 2
    target_participants: int = 5
    scheduling_mode: str = "fixed"
    planning_prefs: dict[str, Any] = field(default_factory=dict)


@dataclass
class ModifyEventCommand:
    event_id: int
    modifier_telegram_id: int
    description: str | None = None
    event_type: str | None = None
    scheduled_time: datetime | None = None
    duration_minutes: int | None = None
    threshold_attendance: int | None = None
    min_participants: int | None = None
    target_participants: int | None = None
    planning_prefs: dict[str, Any] | None = None


@dataclass
class TransitionEventCommand:
    event_id: int
    target_state: str
    actor_telegram_user_id: int
    reason: str = ""
    source: str = "manual"


@dataclass
class CancelEventCommand:
    event_id: int
    actor_telegram_user_id: int
    reason: str = ""


@dataclass
class ModifyEventRequest:
    event_id: int
    requester_telegram_id: int
    change_text: str


@dataclass
class ApproveModifyRequestCommand:
    request_id: str
    admin_telegram_id: int


@dataclass
class RejectModifyRequestCommand:
    request_id: str
    admin_telegram_id: int


# ---------------------------------------------------------------------------
# Participant DTOs
# ---------------------------------------------------------------------------

@dataclass
class JoinEventCommand:
    event_id: int
    telegram_user_id: int
    source: str = "manual"
    role: str = "participant"


@dataclass
class ConfirmAttendanceCommand:
    event_id: int
    telegram_user_id: int


@dataclass
class CancelAttendanceCommand:
    event_id: int
    telegram_user_id: int
    reason: str = ""


# ---------------------------------------------------------------------------
# Constraint DTOs
# ---------------------------------------------------------------------------

@dataclass
class AddConstraintCommand:
    event_id: int
    user_telegram_id: int
    target_username: str
    constraint_type: str
    confidence: float = 0.75


# ---------------------------------------------------------------------------
# Query DTOs
# ---------------------------------------------------------------------------

@dataclass
class GetEventQuery:
    event_id: int


@dataclass
class GetEventsForGroupQuery:
    group_telegram_id: int
    states: list[str] = field(default_factory=lambda: ["proposed", "interested", "confirmed", "locked"])


@dataclass
class GetEventsForUserQuery:
    telegram_user_id: int


@dataclass
class GetParticipantQuery:
    event_id: int
    telegram_user_id: int


# ---------------------------------------------------------------------------
# Result DTOs
# ---------------------------------------------------------------------------

@dataclass
class EventDTO:
    event_id: int
    group_id: int
    event_type: str
    description: str
    organizer_telegram_user_id: int | None
    admin_telegram_user_id: int | None
    scheduled_time: datetime | None
    duration_minutes: int
    threshold_attendance: int
    min_participants: int
    target_participants: int
    state: str
    version: int
    locked_at: datetime | None
    completed_at: datetime | None
    collapse_at: datetime | None
    commit_by: datetime | None
    planning_prefs: dict[str, Any] = field(default_factory=dict)
    participant_count: int = 0
    confirmed_count: int = 0


@dataclass
class ParticipantDTO:
    event_id: int
    telegram_user_id: int
    username: str | None = None
    display_name: str | None = None
    status: str = "joined"
    role: str = "participant"
    joined_at: datetime | None = None
    confirmed_at: datetime | None = None


@dataclass
class Result:
    """Generic result envelope."""
    success: bool = True
    data: Any = None
    errors: list[str] = field(default_factory=list)
    messages: list[str] = field(default_factory=list)

    @classmethod
    def ok(cls, data: Any = None, messages: list[str] | None = None) -> "Result":
        return cls(success=True, data=data, messages=messages or [])

    @classmethod
    def fail(cls, errors: str | list[str]) -> "Result":
        if isinstance(errors, str):
            errors = [errors]
        return cls(success=False, errors=errors)
