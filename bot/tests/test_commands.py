#!/usr/bin/env python3
"""Unit tests for command handlers."""
import pytest
from telegram import Update, Message, User, Chat
from telegram.ext import ContextTypes

from bot.commands import start, my_groups, profile, reputation
from bot.commands import organize_event, join, confirm, cancel
from bot.commands import constraints, suggest_time, status, event_details


@pytest.mark.asyncio
async def test_start_command():
    """Test /start command handler."""
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
    
    await start.handle(update, context)
    
    assert update.message.text == "/start"


@pytest.mark.asyncio
async def test_my_groups_command():
    """Test /my_groups command handler."""
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=None,
            chat=Chat(id=123, type="group"),
            from_user=User(id=456, first_name="Test", is_bot=False)
        )
    )
    context = ContextTypes.DEFAULT_TYPE()
    
    await my_groups.handle(update, context)


@pytest.mark.asyncio
async def test_profile_command():
    """Test /profile command handler."""
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
    
    await profile.handle(update, context)


@pytest.mark.asyncio
async def test_reputation_command():
    """Test /reputation command handler."""
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
    
    await reputation.handle(update, context)


@pytest.mark.asyncio
async def test_join_command_without_args():
    """Test /join command without event_id."""
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
    context.args = []
    
    await join.handle(update, context)


@pytest.mark.asyncio
async def test_join_command_with_event_id():
    """Test /join command with event_id."""
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
    
    await join.handle(update, context)


@pytest.mark.asyncio
async def test_cancel_command():
    """Test /cancel command."""
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
    
    await cancel.handle(update, context)


@pytest.mark.asyncio
async def test_status_command():
    """Test /status command."""
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
    
    await status.handle(update, context)


@pytest.mark.asyncio
async def test_event_details_command():
    """Test /event_details command."""
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
    
    await event_details.handle(update, context)


@pytest.mark.asyncio
async def test_constraints_command_view():
    """Test /constraints command - view action."""
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
    context.args = ["1", "view"]
    
    await constraints.handle(update, context)


@pytest.mark.asyncio
async def test_suggest_time_command():
    """Test /suggest_time command."""
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
    
    await suggest_time.handle(update, context)


@pytest.mark.asyncio
async def test_organize_event_command():
    """Test /organize_event command."""
    update = Update(
        update_id=1,
        message=Message(
            message_id=1,
            date=None,
            chat=Chat(id=123, type="group"),
            from_user=User(id=456, first_name="Test", is_bot=False)
        )
    )
    context = ContextTypes.DEFAULT_TYPE()
    
    await organize_event.handle(update, context)