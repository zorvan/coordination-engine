#!/usr/bin/env python3
"""Integration tests for event flow."""
import pytest
from unittest.mock import MagicMock
from telegram import Update, Message, User, Chat, CallbackQuery
from datetime import datetime
from telegram.ext import ContextTypes

from bot.handlers.event_flow import handle_event_flow
from bot.common.event_states import can_transition, EVENT_STATE_TRANSITIONS
from bot.handlers.feedback import collect_feedback, handle_feedback_callback


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
    from unittest.mock import MagicMock
    context = ContextTypes.DEFAULT_TYPE(application=MagicMock())

    await handle_feedback_callback(update, context)


@pytest.mark.asyncio
async def test_feedback_collection():
    """Test feedback collection."""
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=datetime.utcnow(),
            chat=Chat(id=123, type="private"),
            from_user=User(id=456, first_name="Test", is_bot=False)
        )
    )
    from unittest.mock import MagicMock
    context = ContextTypes.DEFAULT_TYPE(application=MagicMock())
    context.args = ["1"]

    await collect_feedback(update, context)
