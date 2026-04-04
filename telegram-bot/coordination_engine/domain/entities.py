"""Domain entities — rich models with behaviour and invariants."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from coordination_engine.domain.exceptions import (
    BusinessRuleViolation,
    EventLockedError,
    InvalidTransitionError,
    ThresholdNotMetError,
)
from coordination_engine.domain.value_objects import (
    BudgetLevel,
    ConstraintType,
    DatePreset,
    EventState,
    EventType,
    LocationType,
    ParticipantRole,
    ParticipantStatus,
    SchedulingMode,
    TimeWindow,
    TransportMode,
)


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

@dataclass
class User:
    user_id: Optional[int] = None
    telegram_user_id: Optional[int] = None
    username: Optional[str] = None
    display_name: Optional[str] = None
    reputation: float = 1.0
    expertise_per_activity: dict[str, float] = field(default_factory=dict)

    @property
    def display(self) -> str:
        if self.display_name:
            return self.display_name
        if self.username:
            return f"@{self.username}"
        return f"User#{self.telegram_user_id}"


# ---------------------------------------------------------------------------
# Group
# ---------------------------------------------------------------------------

@dataclass
class Group:
    group_id: Optional[int] = None
    telegram_group_id: Optional[int] = None
    group_name: Optional[str] = None
    group_type: str = "group"
    member_list: list[int] = field(default_factory=list)

    def add_member(self, telegram_user_id: int) -> None:
        if telegram_user_id not in self.member_list:
            self.member_list.append(telegram_user_id)

    def remove_member(self, telegram_user_id: int) -> None:
        self.member_list = [m for m in self.member_list if m != telegram_user_id]


# ---------------------------------------------------------------------------
# PlanningPreferences
# ---------------------------------------------------------------------------

@dataclass
class PlanningPreferences:
    """Mutable planning preferences attached to an event."""

    date_preset: Optional[DatePreset] = None
    time_window: Optional[TimeWindow] = None
    location_type: Optional[LocationType] = None
    budget_level: Optional[BudgetLevel] = None
    transport_mode: Optional[TransportMode] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.date_preset:
            result["date_preset"] = self.date_preset.value
        if self.time_window:
            result["time_window"] = self.time_window.value
        if self.location_type:
            result["location_type"] = self.location_type.value
        if self.budget_level:
            result["budget_level"] = self.budget_level.value
        if self.transport_mode:
            result["transport_mode"] = self.transport_mode.value
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "PlanningPreferences":
        if not data:
            return cls()
        return cls(
            date_preset=DatePreset(data["date_preset"]) if "date_preset" in data else None,
            time_window=TimeWindow(data["time_window"]) if "time_window" in data else None,
            location_type=LocationType(data["location_type"]) if "location_type" in data else None,
            budget_level=BudgetLevel(data["budget_level"]) if "budget_level" in data else None,
            transport_mode=TransportMode(data["transport_mode"]) if "transport_mode" in data else None,
        )


# ---------------------------------------------------------------------------
# Constraint
# ---------------------------------------------------------------------------

@dataclass
class Constraint:
    constraint_id: Optional[int] = None
    user_id: Optional[int] = None
    target_user_id: Optional[int] = None
    event_id: Optional[int] = None
    type: ConstraintType = ConstraintType.IF_JOINS
    confidence: float = 1.0
    created_at: Optional[datetime] = None


# ---------------------------------------------------------------------------
# EventParticipant
# ---------------------------------------------------------------------------

@dataclass
class EventParticipant:
    event_id: int
    telegram_user_id: int
    status: ParticipantStatus = ParticipantStatus.JOINED
    role: ParticipantRole = ParticipantRole.PARTICIPANT
    joined_at: Optional[datetime] = None
    confirmed_at: Optional[datetime] = None
    cancelled_at: Optional[datetime] = None
    source: Optional[str] = None

    def __post_init__(self) -> None:
        if self.joined_at is None:
            self.joined_at = datetime.now(timezone.utc)

    def confirm(self) -> None:
        if self.status == ParticipantStatus.CANCELLED:
            raise BusinessRuleViolation("Cannot confirm a cancelled participation.")
        self.status = ParticipantStatus.CONFIRMED
        self.confirmed_at = datetime.now(timezone.utc)

    def cancel(self) -> None:
        self.status = ParticipantStatus.CANCELLED
        self.cancelled_at = datetime.now(timezone.utc)

    def mark_no_show(self) -> None:
        self.status = ParticipantStatus.NO_SHOW


# ---------------------------------------------------------------------------
# Event — the aggregate root
# ---------------------------------------------------------------------------

# Valid state transitions
_ALLOWED_TRANSITIONS: dict[EventState, set[EventState]] = {
    EventState.PROPOSED: {EventState.INTERESTED, EventState.CANCELLED},
    EventState.INTERESTED: {EventState.CONFIRMED, EventState.CANCELLED},
    EventState.CONFIRMED: {EventState.LOCKED, EventState.CANCELLED},
    EventState.LOCKED: {EventState.COMPLETED, EventState.CANCELLED},
    EventState.COMPLETED: set(),
    EventState.CANCELLED: set(),
}


@dataclass
class Event:
    """Aggregate root for event lifecycle management."""

    event_id: Optional[int] = None
    group_id: Optional[int] = None
    event_type: EventType = EventType.SOCIAL
    description: str = ""
    organizer_telegram_user_id: Optional[int] = None
    admin_telegram_user_id: Optional[int] = None
    scheduled_time: Optional[datetime] = None
    commit_by: Optional[datetime] = None
    collapse_at: Optional[datetime] = None
    lock_deadline: Optional[datetime] = None
    duration_minutes: int = 120
    threshold_attendance: int = 3
    min_participants: int = 2
    target_participants: int = 5
    planning_prefs: PlanningPreferences = field(default_factory=PlanningPreferences)
    ai_score: Optional[float] = None
    state: EventState = EventState.PROPOSED
    version: int = 0
    locked_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    # Transient: loaded on demand
    _participants: list[EventParticipant] = field(default_factory=list, repr=False)

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    @property
    def is_locked(self) -> bool:
        return self.state == EventState.LOCKED

    @property
    def is_active(self) -> bool:
        return self.state not in {EventState.COMPLETED, EventState.CANCELLED}

    @property
    def scheduling_mode(self) -> SchedulingMode:
        return SchedulingMode.FIXED if self.scheduled_time else SchedulingMode.FLEXIBLE

    def confirmed_count(self) -> int:
        return sum(
            1 for p in self._participants
            if p.status == ParticipantStatus.CONFIRMED
        )

    def joined_count(self) -> int:
        return sum(
            1 for p in self._participants
            if p.status in {ParticipantStatus.JOINED, ParticipantStatus.CONFIRMED}
        )

    def has_participant(self, telegram_user_id: int) -> bool:
        return any(p.telegram_user_id == telegram_user_id for p in self._participants)

    def get_participant(self, telegram_user_id: int) -> EventParticipant | None:
        for p in self._participants:
            if p.telegram_user_id == telegram_user_id:
                return p
        return None

    def can_be_modified(self) -> bool:
        return self.state not in {EventState.LOCKED, EventState.COMPLETED, EventState.CANCELLED}

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------

    def can_transition_to(self, new_state: EventState) -> bool:
        return new_state in _ALLOWED_TRANSITIONS.get(self.state, set())

    def transition_to(
        self,
        new_state: EventState,
        *,
        actor_telegram_user_id: Optional[int] = None,
        reason: str = "",
        source: str = "manual",
    ) -> "StateTransition":
        if not self.can_transition_to(new_state):
            raise InvalidTransitionError(
                f"Cannot transition from {self.state.value} to {new_state.value}"
            )

        # Pre-conditions
        if new_state == EventState.LOCKED:
            if self.confirmed_count() < self.min_participants:
                raise ThresholdNotMetError(
                    f"Need at least {self.min_participants} confirmed participants "
                    f"(currently {self.confirmed_count()})"
                )
            self.locked_at = datetime.now(timezone.utc)

        old_state = self.state
        self.state = new_state
        self.version += 1

        if new_state == EventState.COMPLETED:
            self.completed_at = datetime.now(timezone.utc)

        return StateTransition(
            event_id=self.event_id,
            from_state=old_state,
            to_state=new_state,
            actor_telegram_user_id=actor_telegram_user_id,
            reason=reason,
            source=source,
        )

    # ------------------------------------------------------------------
    # Participant management
    # ------------------------------------------------------------------

    def add_participant(
        self,
        telegram_user_id: int,
        *,
        role: ParticipantRole = ParticipantRole.PARTICIPANT,
        source: str = "manual",
    ) -> EventParticipant:
        if self.has_participant(telegram_user_id):
            existing = self.get_participant(telegram_user_id)
            if existing and existing.status == ParticipantStatus.CANCELLED:
                existing.status = ParticipantStatus.JOINED
                existing.joined_at = datetime.now(timezone.utc)
                return existing
            raise BusinessRuleViolation(f"User {telegram_user_id} already participates.")

        participant = EventParticipant(
            event_id=self.event_id,  # type: ignore[arg-type]
            telegram_user_id=telegram_user_id,
            role=role,
            source=source,
        )
        self._participants.append(participant)
        return participant

    # ------------------------------------------------------------------
    # Modification (only when not locked)
    # ------------------------------------------------------------------

    def apply_modification(
        self,
        *,
        description: str | None = None,
        event_type: EventType | None = None,
        scheduled_time: datetime | None = None,
        duration_minutes: int | None = None,
        threshold_attendance: int | None = None,
        min_participants: int | None = None,
        target_participants: int | None = None,
        planning_prefs: PlanningPreferences | None = None,
    ) -> list[str]:
        if not self.can_be_modified():
            raise EventLockedError(
                f"Event {self.event_id} is {self.state.value}; modification is not allowed."
            )

        changed: list[str] = []

        if description is not None and description != self.description:
            self.description = description[:500]
            changed.append("description")

        if event_type is not None and event_type != self.event_type:
            self.event_type = event_type
            changed.append("event_type")

        if scheduled_time is not None and scheduled_time != self.scheduled_time:
            self.scheduled_time = scheduled_time
            changed.append("scheduled_time")

        if duration_minutes is not None and duration_minutes != self.duration_minutes:
            self.duration_minutes = max(1, min(720, duration_minutes))
            changed.append("duration_minutes")

        if threshold_attendance is not None and threshold_attendance != self.threshold_attendance:
            self.threshold_attendance = max(1, threshold_attendance)
            changed.append("threshold_attendance")

        if min_participants is not None and min_participants != self.min_participants:
            self.min_participants = max(1, min_participants)
            changed.append("min_participants")

        if target_participants is not None and target_participants != self.target_participants:
            self.target_participants = max(1, target_participants)
            changed.append("target_participants")

        if planning_prefs is not None:
            self.planning_prefs = planning_prefs
            changed.append("planning_prefs")

        self.version += 1
        return changed


# ---------------------------------------------------------------------------
# StateTransition (audit record)
# ---------------------------------------------------------------------------

@dataclass
class StateTransition:
    event_id: Optional[int]
    from_state: EventState
    to_state: EventState
    actor_telegram_user_id: Optional[int] = None
    timestamp: Optional[datetime] = None
    reason: str = ""
    source: str = "manual"

    def __post_init__(self) -> None:
        if self.timestamp is None:
            self.timestamp = datetime.now(timezone.utc)
