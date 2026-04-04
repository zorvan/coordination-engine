"""Domain events — emitted by aggregates, handled by application/infra layers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional


@dataclass(frozen=True, kw_only=True)
class DomainEvent:
    occurred_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# -- Event lifecycle events --

@dataclass(frozen=True, kw_only=True)
class EventCreated(DomainEvent):
    event_id: int
    organizer_telegram_user_id: int
    group_id: int
    description: str


@dataclass(frozen=True, kw_only=True)
class EventStateChanged(DomainEvent):
    event_id: int
    from_state: str
    to_state: str
    actor_telegram_user_id: Optional[int] = None
    reason: str = ""


@dataclass(frozen=True, kw_only=True)
class EventModified(DomainEvent):
    event_id: int
    changed_fields: list[str]
    modifier_telegram_user_id: Optional[int] = None


@dataclass(frozen=True, kw_only=True)
class EventCancelled(DomainEvent):
    event_id: int
    reason: str = ""


@dataclass(frozen=True, kw_only=True)
class EventLocked(DomainEvent):
    event_id: int
    locked_at: datetime


@dataclass(frozen=True, kw_only=True)
class EventCompleted(DomainEvent):
    event_id: int
    completed_at: datetime


# -- Participant events --

@dataclass(frozen=True, kw_only=True)
class ParticipantJoined(DomainEvent):
    event_id: int
    telegram_user_id: int
    source: str = ""


@dataclass(frozen=True, kw_only=True)
class ParticipantConfirmed(DomainEvent):
    event_id: int
    telegram_user_id: int


@dataclass(frozen=True, kw_only=True)
class ParticipantCancelled(DomainEvent):
    event_id: int
    telegram_user_id: int
    reason: str = ""


@dataclass(frozen=True, kw_only=True)
class ThresholdReached(DomainEvent):
    event_id: int
    current_count: int
    threshold: int


@dataclass(frozen=True, kw_only=True)
class MemoryCollectionRequested(DomainEvent):
    event_id: int
    scheduled_at: datetime


@dataclass(frozen=True, kw_only=True)
class ModificationRequested(DomainEvent):
    event_id: int
    requester_telegram_user_id: int
    change_description: str
    request_id: str


@dataclass(frozen=True, kw_only=True)
class ModificationApproved(DomainEvent):
    event_id: int
    changed_fields: list[str]
    admin_telegram_user_id: int


@dataclass(frozen=True, kw_only=True)
class ModificationRejected(DomainEvent):
    event_id: int
    requester_telegram_user_id: int
    admin_telegram_user_id: int
