#!/usr/bin/env python3
"""Integration tests for event flow."""
import pytest
from unittest.mock import MagicMock
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes

from bot.handlers.event_flow import can_transition, handle_event_flow, EVENT_STATE_TRANSITIONS
from bot.handlers.feedback import collect_feedback, handle_feedback_callback
from bot.utils.nudges import (
    generate_nudge_message,
    generate_fallback_warning,
    generate_reliability_warning,
    generate_deadline_warning,
    generate_lock_warning,
    generate_threshold_warning,
)


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
    
    assert can_transition("confirmed", "locked")
    assert can_transition("confirmed", "cancelled")
    
    assert can_transition("locked", "completed")
    assert can_transition("locked", "cancelled")
    
    assert not can_transition("cancelled", "proposed")
    assert not can_transition("completed", "locked")


@pytest.mark.asyncio
async def test_nudge_generation():
    """Test nudge message generation."""
    event_id = 123
    user_id = 456
    
    msg = generate_nudge_message(event_id, user_id, "social")
    assert "event" in msg
    assert str(event_id) in msg
    assert str(user_id) in msg
    
    fallback_msg = generate_fallback_warning(event_id)
    assert "AI" in fallback_msg
    assert str(event_id) in fallback_msg
    
    reliability_msg = generate_reliability_warning(user_id, 0.2)
    assert "low reliability" in reliability_msg.lower() or "0.2" in reliability_msg
    
    deadline_msg = generate_deadline_warning(event_id, "2 hours")
    assert "deadline" in deadline_msg.lower()
    
    lock_msg = generate_lock_warning(event_id)
    assert "locked" in lock_msg.lower()
    
    threshold_msg = generate_threshold_warning(event_id, 3, 5)
    assert "below threshold" in threshold_msg.lower()
    assert "3" in threshold_msg
    assert "5" in threshold_msg


@pytest.mark.asyncio
async def test_feedback_callback():
    """Test feedback callback handler."""
    user = User(id=456, first_name="Test", is_bot=False)
    callback_query = CallbackQuery(
        id="123",
        from_user=user,
        chat_instance="123",
        data="feedback_123_4"
    )
    update = Update(update_id=1, callback_query=callback_query)
    context = ContextTypes.DEFAULT_TYPE()
    
    await handle_feedback_callback(update, context)


@pytest.mark.asyncio
async def test_feedback_collection():
    """Test feedback collection."""
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=None,
            chat=Chat(id=123, type="private"),
            from_user=User(id=456, first_name="Test", is_bot=False)
        )
    )
    context = ContextTypes.DEFAULT_TYPE()
    context.args = ["1"]
    
    await collect_feedback(update, context)