#!/usr/bin/env python3
"""Integration tests for event flow."""
import pytest
from telegram import Update, Message, User, Chat, CallbackQuery
from telegram.ext import ContextTypes, CallbackContext

from bot.handlers.event_flow import EventFlowStateMachine, handle_event_flow
from bot.handlers.feedback import collect_feedback, handle_feedback_callback
from bot.utils.nudges import (
    generate_nudge_message,
    generate_fallback_warning,
    generate_reliability_warning,
    generate_deadline_warning,
    generate_lock_warning,
    generate_threshold_warning,
)


@pytest.mark.asyncio
async def test_event_flow_state_machine():
    """Test state machine transitions."""
    sm = EventFlowStateMachine()
    
    assert sm.can_transition("proposed", "interested")
    assert sm.can_transition("proposed", "locked")
    assert sm.can_transition("proposed", "cancelled")
    assert not sm.can_transition("proposed", "completed")
    
    assert sm.can_transition("interested", "confirmed")
    assert sm.can_transition("interested", "cancelled")
    
    assert sm.can_transition("confirmed", "locked")
    assert sm.can_transition("confirmed", "cancelled")
    
    assert sm.can_transition("locked", "completed")
    assert sm.can_transition("locked", "cancelled")
    
    assert sm.can_transition("cancelled", "proposed") is False
    assert sm.can_transition("completed", "locked") is False


@pytest.mark.asyncio
async def test_nudge_generation():
    """Test nudge message generation."""
    event_id = 123
    user_id = 456
    
    msg = generate_nudge_message(event_id, user_id, "social")
    assert "cancelled" in msg
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