#!/usr/bin/env python3
"""Integration tests for event flow."""
import pytest
from bot.common.event_states import can_transition


class MockContext:
    """Mock context for testing."""
    def __init__(self):
        self.args = None


@pytest.mark.asyncio
async def test_event_flow_state_machine():
    """Test state machine transitions."""
    assert can_transition("proposed", "interested")
    assert can_transition("proposed", "cancelled")
    assert not can_transition("proposed", "completed")
    assert not can_transition("proposed", "locked")  # proposed -> interested -> confirmed -> locked

    assert can_transition("interested", "confirmed")
    assert can_transition("interested", "cancelled")

    assert can_transition("confirmed", "interested")
    assert can_transition("confirmed", "proposed")
    assert can_transition("confirmed", "locked")
    assert can_transition("confirmed", "cancelled")

    assert can_transition("locked", "completed")
    assert can_transition("locked", "cancelled")

    assert not can_transition("cancelled", "proposed")
    assert not can_transition("completed", "locked")
