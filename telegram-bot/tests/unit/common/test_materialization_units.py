"""
Unit tests — bot/common helpers.
Phase 2: Pure Unit Tests per TEST_SYSTEM_PLAN_v3.2 §4A.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta

from bot.common.materialization import get_time_framing_tier
from bot.common.event_states import can_transition, EVENT_STATE_TRANSITIONS


class TestGetTimeFramingTier:
    """v3.2 temporal gradient — event state only, no user data."""

    def _make_event(self, hours_until: int | None) -> object:
        """Minimal event-like object."""
        class _Event:
            scheduled_time: datetime | None
        e = _Event()
        if hours_until is None:
            e.scheduled_time = None
        else:
            e.scheduled_time = datetime.utcnow() + timedelta(hours=hours_until)
        return e

    def test_no_scheduled_time_is_light(self) -> None:
        event = self._make_event(None)
        assert get_time_framing_tier(event) == "light"

    def test_more_than_72h_is_light(self) -> None:
        event = self._make_event(73)
        assert get_time_framing_tier(event) == "light"

    def test_exactly_73h_is_light(self) -> None:
        event = self._make_event(73)
        assert get_time_framing_tier(event) == "light"

    def test_48h_is_warm(self) -> None:
        event = self._make_event(48)
        assert get_time_framing_tier(event) == "warm"

    def test_25h_is_warm(self) -> None:
        event = self._make_event(25)
        assert get_time_framing_tier(event) == "warm"

    def test_12h_is_urgent(self) -> None:
        event = self._make_event(12)
        assert get_time_framing_tier(event) == "urgent"

    def test_3h_is_urgent(self) -> None:
        event = self._make_event(3)
        assert get_time_framing_tier(event) == "urgent"

    def test_1h_is_immediate(self) -> None:
        event = self._make_event(1)
        assert get_time_framing_tier(event) == "immediate"

    def test_0h_is_immediate(self) -> None:
        event = self._make_event(0)
        assert get_time_framing_tier(event) == "immediate"

    def test_boundary_72h(self) -> None:
        event = self._make_event(72)
        assert get_time_framing_tier(event) == "warm"

    def test_boundary_24h(self) -> None:
        event = self._make_event(24)
        assert get_time_framing_tier(event) == "urgent"

    def test_boundary_2h(self) -> None:
        event = self._make_event(2)
        assert get_time_framing_tier(event) == "immediate"


class TestStateTransitionValidation:
    """State machine guard rails — unit-level."""

    def test_proposed_to_interested_valid(self) -> None:
        assert can_transition("proposed", "interested") is True

    def test_interested_to_confirmed_valid(self) -> None:
        assert can_transition("interested", "confirmed") is True

    def test_confirmed_to_locked_valid(self) -> None:
        assert can_transition("confirmed", "locked") is True

    def test_confirmed_can_step_back_when_commitments_drop(self) -> None:
        assert can_transition("confirmed", "interested") is True
        assert can_transition("confirmed", "proposed") is True

    def test_locked_to_completed_valid(self) -> None:
        assert can_transition("locked", "completed") is True

    def test_proposed_to_completed_invalid(self) -> None:
        assert can_transition("proposed", "completed") is False

    def test_completed_to_anything_invalid(self) -> None:
        for state in EVENT_STATE_TRANSITIONS:
            if state != "completed":
                assert can_transition("completed", state) is False

    def test_cancelled_to_anything_invalid(self) -> None:
        for state in EVENT_STATE_TRANSITIONS:
            if state != "cancelled":
                assert can_transition("cancelled", state) is False

    def test_unknown_state_invalid(self) -> None:
        assert can_transition("banana", "interested") is False

    def test_same_state_invalid(self) -> None:
        assert can_transition("proposed", "proposed") is False
