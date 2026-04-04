"""Domain services — business rules that don't belong to a single entity."""

from __future__ import annotations

from datetime import datetime, timezone, timedelta

from coordination_engine.domain.entities import Event
from coordination_engine.domain.value_objects import (
    EventState,
    ParticipantStatus,
)


class EventStateService:
    """Pure domain logic for event state transitions and threshold checks."""

    @staticmethod
    def should_auto_collapse(event: Event) -> bool:
        """Check if event should be auto-cancelled due to collapse_at deadline."""
        if event.state in {EventState.COMPLETED, EventState.CANCELLED, EventState.LOCKED}:
            return False
        if event.collapse_at is None:
            return False
        return datetime.now(timezone.utc) >= event.collapse_at

    @staticmethod
    def should_auto_lock(event: Event) -> bool:
        """Check if event should be auto-locked at commit_by deadline."""
        if event.state != EventState.CONFIRMED:
            return False
        if event.commit_by is None:
            return False
        if event.confirmed_count() < event.min_participants:
            return False
        return datetime.now(timezone.utc) >= event.commit_by

    @staticmethod
    def should_send_threshold_reminder(event: Event) -> bool:
        """Check if we should remind about approaching collapse deadline."""
        if event.state in {EventState.COMPLETED, EventState.CANCELLED, EventState.LOCKED}:
            return False
        if event.collapse_at is None:
            return False
        remaining = event.collapse_at - datetime.now(timezone.utc)
        return timedelta(hours=0) < remaining <= timedelta(hours=24)

    @staticmethod
    def compute_collapse_at(
        scheduled_time: datetime | None,
        *,
        default_hours_before: int = 2,
        default_days_from_now: int = 7,
    ) -> datetime:
        """Compute the auto-cancel deadline."""
        now = datetime.now(timezone.utc)
        if scheduled_time:
            candidate = scheduled_time - timedelta(hours=default_hours_before)
            return candidate if candidate > now else now + timedelta(hours=1)
        return now + timedelta(days=default_days_from_now)

    @staticmethod
    def compute_commit_by(
        scheduled_time: datetime | None,
        *,
        default_hours_before: int = 12,
    ) -> datetime | None:
        """Derive default commit-by deadline from scheduled time."""
        if scheduled_time is None:
            return None
        return scheduled_time - timedelta(hours=default_hours_before)


class ParticipantService:
    """Pure domain logic for participant operations."""

    @staticmethod
    def can_user_join(event: Event, telegram_user_id: int) -> tuple[bool, str]:
        """Check if a user can join the event."""
        if not event.is_active:
            return False, f"Event is {event.state.value}."
        if event.has_participant(telegram_user_id):
            existing = event.get_participant(telegram_user_id)
            if existing and existing.status == ParticipantStatus.CANCELLED:
                return True, ""  # Can rejoin after cancellation
            return False, "Already a participant."
        return True, ""

    @staticmethod
    def can_user_confirm(event: Event, telegram_user_id: int) -> tuple[bool, str]:
        """Check if a user can confirm attendance."""
        participant = event.get_participant(telegram_user_id)
        if not participant:
            return False, "Not a participant. Join first."
        if participant.status == ParticipantStatus.CONFIRMED:
            return False, "Already confirmed."
        if participant.status == ParticipantStatus.CANCELLED:
            return False, "Participation was cancelled."
        if event.state not in {EventState.PROPOSED, EventState.INTERESTED, EventState.CONFIRMED}:
            return False, f"Event is {event.state.value}."
        return True, ""

    @staticmethod
    def can_user_cancel(event: Event, telegram_user_id: int) -> tuple[bool, str]:
        """Check if a user can cancel their participation."""
        participant = event.get_participant(telegram_user_id)
        if not participant:
            return False, "Not a participant."
        if participant.status == ParticipantStatus.CANCELLED:
            return False, "Already cancelled."
        if event.state in {EventState.COMPLETED}:
            return False, "Event is completed."
        return True, ""

    @staticmethod
    def check_threshold_reached(
        event: Event,
    ) -> tuple[bool, int]:
        """Check if confirmed count meets or exceeds threshold."""
        confirmed = event.confirmed_count()
        return confirmed >= event.threshold_attendance, confirmed


class ScheduleConflictService:
    """Pure domain logic for detecting scheduling conflicts."""

    @staticmethod
    def events_overlap(
        start1: datetime, duration1: int,
        start2: datetime, duration2: int,
    ) -> bool:
        """Check if two events overlap in time."""
        end1 = start1 + timedelta(minutes=duration1)
        end2 = start2 + timedelta(minutes=duration2)
        return start1 < end2 and start2 < end1
