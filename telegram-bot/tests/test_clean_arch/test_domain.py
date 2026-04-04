"""Tests for domain layer — entities, value objects, domain services."""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from coordination_engine.domain.entities import (
    Event,
    EventParticipant,
    Group,
    PlanningPreferences,
    User,
)
from coordination_engine.domain.exceptions import (
    BusinessRuleViolation,
    EventLockedError,
    InvalidTransitionError,
    ThresholdNotMetError,
)
from coordination_engine.domain.services import (
    EventStateService,
    ParticipantService,
    ScheduleConflictService,
)
from coordination_engine.domain.value_objects import (
    EventState,
    EventType,
    ParticipantRole,
    ParticipantStatus,
)


# ---------------------------------------------------------------------------
# Value Objects
# ---------------------------------------------------------------------------

class TestEventState:
    def test_valid_states(self):
        assert EventState.PROPOSED.value == "proposed"
        assert EventState.LOCKED.value == "locked"
        assert EventState.COMPLETED.value == "completed"
        assert EventState.CANCELLED.value == "cancelled"

    def test_state_count(self):
        assert len(EventState) == 6


class TestEventType:
    def test_valid_types(self):
        assert EventType.SOCIAL.value == "social"
        assert EventType.SPORTS.value == "sports"
        assert EventType.WORK.value == "work"


class TestParticipantStatus:
    def test_all_statuses(self):
        assert ParticipantStatus.JOINED.value == "joined"
        assert ParticipantStatus.CONFIRMED.value == "confirmed"
        assert ParticipantStatus.CANCELLED.value == "cancelled"
        assert ParticipantStatus.NO_SHOW.value == "no_show"


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

class TestUser:
    def test_default_user(self):
        user = User()
        assert user.reputation == 1.0
        assert user.expertise_per_activity == {}

    def test_display_name_priority(self):
        user = User(telegram_user_id=123, display_name="Alice", username="alice")
        assert user.display == "Alice"

    def test_display_fallback_username(self):
        user = User(telegram_user_id=123, username="alice")
        assert user.display == "@alice"

    def test_display_fallback_id(self):
        user = User(telegram_user_id=123)
        assert user.display == "User#123"


class TestGroup:
    def test_add_member(self):
        group = Group()
        group.add_member(1)
        group.add_member(2)
        assert group.member_list == [1, 2]

    def test_add_duplicate_member(self):
        group = Group()
        group.add_member(1)
        group.add_member(1)
        assert group.member_list == [1]

    def test_remove_member(self):
        group = Group(member_list=[1, 2, 3])
        group.remove_member(2)
        assert group.member_list == [1, 3]


class TestPlanningPreferences:
    def test_to_dict_empty(self):
        prefs = PlanningPreferences()
        assert prefs.to_dict() == {}

    def test_to_dict_with_values(self):
        from coordination_engine.domain.value_objects import LocationType
        prefs = PlanningPreferences(location_type=LocationType.HOME)
        assert prefs.to_dict() == {"location_type": "home"}

    def test_from_dict_none(self):
        prefs = PlanningPreferences.from_dict(None)
        assert prefs.location_type is None

    def test_from_dict_with_values(self):
        prefs = PlanningPreferences.from_dict({
            "location_type": "cafe",
            "budget_level": "low",
        })
        from coordination_engine.domain.value_objects import LocationType, BudgetLevel
        assert prefs.location_type == LocationType.CAFE
        assert prefs.budget_level == BudgetLevel.LOW


class TestEvent:
    def test_default_event(self):
        event = Event()
        assert event.state == EventState.PROPOSED
        assert event.event_type == EventType.SOCIAL
        assert event.version == 0
        assert not event.is_locked
        assert event.is_active

    def test_scheduling_mode_fixed(self):
        event = Event(scheduled_time=datetime.now(timezone.utc))
        from coordination_engine.domain.value_objects import SchedulingMode
        assert event.scheduling_mode == SchedulingMode.FIXED

    def test_scheduling_mode_flexible(self):
        event = Event(scheduled_time=None)
        from coordination_engine.domain.value_objects import SchedulingMode
        assert event.scheduling_mode == SchedulingMode.FLEXIBLE

    def test_add_participant(self):
        event = Event(event_id=1)
        participant = event.add_participant(123, source="test")
        assert participant.telegram_user_id == 123
        assert participant.status == ParticipantStatus.JOINED
        assert event.has_participant(123)

    def test_duplicate_participant_raises(self):
        event = Event(event_id=1)
        event.add_participant(123)
        with pytest.raises(BusinessRuleViolation):
            event.add_participant(123)

    def test_rejoin_after_cancel(self):
        event = Event(event_id=1)
        event.add_participant(123)
        participant = event.get_participant(123)
        participant.cancel()
        # Rejoin should work
        participant2 = event.add_participant(123)
        assert participant2.status == ParticipantStatus.JOINED

    def test_transition_proposed_to_interested(self):
        event = Event()
        event.transition_to(EventState.INTERESTED, reason="Testing")
        assert event.state == EventState.INTERESTED
        assert event.version == 1

    def test_invalid_transition_raises(self):
        event = Event(state=EventState.COMPLETED)
        with pytest.raises(InvalidTransitionError):
            event.transition_to(EventState.PROPOSED)

    def test_lock_requires_min_participants(self):
        event = Event(
            event_id=1,
            state=EventState.CONFIRMED,
            min_participants=2,
        )
        event.add_participant(1, role=ParticipantRole.ORGANIZER)
        # Only 1 participant, need 2
        with pytest.raises(ThresholdNotMetError):
            event.transition_to(EventState.LOCKED)

    def test_lock_succeed_with_enough_participants(self):
        event = Event(
            event_id=1,
            state=EventState.CONFIRMED,
            min_participants=2,
            threshold_attendance=2,
        )
        event.add_participant(1, role=ParticipantRole.ORGANIZER)
        p2 = event.add_participant(2)
        p2.confirm()
        p1 = event.get_participant(1)
        p1.confirm()

        event.transition_to(EventState.LOCKED)
        assert event.state == EventState.LOCKED
        assert event.locked_at is not None
        assert event.is_locked

    def test_completed_event_cannot_transition(self):
        event = Event(state=EventState.COMPLETED)
        for state in EventState:
            if state != EventState.COMPLETED:
                assert not event.can_transition_to(state)

    def test_cancel_from_any_state(self):
        for state in [EventState.PROPOSED, EventState.INTERESTED, EventState.CONFIRMED]:
            event = Event(state=state)
            event.transition_to(EventState.CANCELLED, reason="Test")
            assert event.state == EventState.CANCELLED

    def test_apply_modification(self):
        event = Event(
            event_id=1,
            description="Old desc",
            duration_minutes=60,
        )
        changed = event.apply_modification(
            description="New desc",
            duration_minutes=120,
        )
        assert "description" in changed
        assert "duration_minutes" in changed
        assert event.description == "New desc"
        assert event.duration_minutes == 120
        assert event.version == 1

    def test_apply_modification_locked_raises(self):
        event = Event(
            event_id=1,
            state=EventState.LOCKED,
        )
        with pytest.raises(EventLockedError):
            event.apply_modification(description="New desc")

    def test_apply_no_changes(self):
        event = Event(event_id=1, description="Same")
        changed = event.apply_modification(description="Same")
        assert changed == []

    def test_count_methods(self):
        event = Event(event_id=1, threshold_attendance=2)
        event.add_participant(1, role=ParticipantRole.ORGANIZER)
        p2 = event.add_participant(2)
        p2.confirm()

        assert event.confirmed_count() == 1
        assert event.joined_count() == 2


class TestEventParticipant:
    def test_confirm(self):
        p = EventParticipant(event_id=1, telegram_user_id=123)
        p.confirm()
        assert p.status == ParticipantStatus.CONFIRMED
        assert p.confirmed_at is not None

    def test_cancel(self):
        p = EventParticipant(event_id=1, telegram_user_id=123)
        p.cancel()
        assert p.status == ParticipantStatus.CANCELLED
        assert p.cancelled_at is not None

    def test_confirm_after_cancel_raises(self):
        p = EventParticipant(event_id=1, telegram_user_id=123)
        p.cancel()
        with pytest.raises(BusinessRuleViolation):
            p.confirm()

    def test_mark_no_show(self):
        p = EventParticipant(event_id=1, telegram_user_id=123)
        p.mark_no_show()
        assert p.status == ParticipantStatus.NO_SHOW


# ---------------------------------------------------------------------------
# Domain Services
# ---------------------------------------------------------------------------

class TestEventStateService:
    def test_should_auto_collapse(self):
        event = Event(
            state=EventState.PROPOSED,
            collapse_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert EventStateService.should_auto_collapse(event)

    def test_should_not_collapse_locked(self):
        event = Event(
            state=EventState.LOCKED,
            collapse_at=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert not EventStateService.should_auto_collapse(event)

    def test_should_auto_lock(self):
        now = datetime.now(timezone.utc)
        event = Event(
            state=EventState.CONFIRMED,
            commit_by=now - timedelta(minutes=1),
            min_participants=1,
        )
        event.add_participant(1, role=ParticipantRole.ORGANIZER)
        p = event.get_participant(1)
        p.confirm()
        assert EventStateService.should_auto_lock(event)

    def test_compute_collapse_at_with_scheduled(self):
        scheduled = datetime.now(timezone.utc) + timedelta(days=1)
        collapse = EventStateService.compute_collapse_at(scheduled)
        assert collapse > datetime.now(timezone.utc)

    def test_compute_collapse_at_without_scheduled(self):
        collapse = EventStateService.compute_collapse_at(None)
        assert collapse > datetime.now(timezone.utc)


class TestParticipantService:
    def test_can_join_active_event(self):
        event = Event(event_id=1, state=EventState.PROPOSED)
        can, reason = ParticipantService.can_user_join(event, 123)
        assert can

    def test_cannot_join_inactive_event(self):
        event = Event(event_id=1, state=EventState.COMPLETED)
        can, reason = ParticipantService.can_user_join(event, 123)
        assert not can

    def test_can_confirm(self):
        event = Event(event_id=1, state=EventState.INTERESTED)
        event.add_participant(123)
        can, reason = ParticipantService.can_user_confirm(event, 123)
        assert can

    def test_cannot_confirm_not_participant(self):
        event = Event(event_id=1)
        can, reason = ParticipantService.can_user_confirm(event, 123)
        assert not can

    def test_threshold_reached(self):
        event = Event(event_id=1, threshold_attendance=2)
        p1 = event.add_participant(1)
        p1.confirm()
        p2 = event.add_participant(2)
        p2.confirm()

        reached, count = ParticipantService.check_threshold_reached(event)
        assert reached
        assert count == 2

    def test_threshold_not_reached(self):
        event = Event(event_id=1, threshold_attendance=5)
        event.add_participant(1)
        event.add_participant(2)

        reached, count = ParticipantService.check_threshold_reached(event)
        assert not reached
        assert count == 0


class TestScheduleConflictService:
    def test_overlapping_events(self):
        assert ScheduleConflictService.events_overlap(
            datetime(2026, 1, 1, 10, 0), 60,
            datetime(2026, 1, 1, 10, 30), 60,
        )

    def test_non_overlapping_events(self):
        assert not ScheduleConflictService.events_overlap(
            datetime(2026, 1, 1, 10, 0), 60,
            datetime(2026, 1, 1, 11, 0), 60,
        )

    def test_adjacent_events(self):
        # Event 1: 10:00-11:00, Event 2: 11:00-12:00 → not overlapping
        assert not ScheduleConflictService.events_overlap(
            datetime(2026, 1, 1, 10, 0), 60,
            datetime(2026, 1, 1, 11, 0), 60,
        )
