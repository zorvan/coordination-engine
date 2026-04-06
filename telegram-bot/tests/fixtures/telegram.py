"""
Telegram mock factories for test system.
Phase 1: §6 — Telegram Boundary mocks.
"""
from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock

from telegram import Update, Message, User, Chat, CallbackQuery


def make_message_update(
    text: str,
    user_id: int = 100,
    username: str | None = None,
    full_name: str | None = None,
    chat_type: str = "private",
    chat_id: int = 200,
    **kwargs: Any,
) -> Update:
    """Build a synthetic Update for a text message."""
    update = MagicMock(spec=Update)
    update.effective_user = MagicMock(
        spec=User,
        id=user_id,
        username=username or f"user_{user_id}",
        full_name=full_name or f"User {user_id}",
    )
    update.effective_chat = MagicMock(
        spec=Chat,
        id=chat_id,
        type=chat_type,
    )
    msg = MagicMock(
        spec=Message,
        text=text,
        chat=update.effective_chat,
    )
    msg.reply_text = AsyncMock()
    update.message = msg
    update.callback_query = None
    update.effective_message = msg
    update.get_bot = MagicMock(return_value=MagicMock(username="test_bot"))
    return update


def make_callback_update(
    data: str,
    user_id: int = 100,
    username: str | None = None,
    full_name: str | None = None,
    chat_type: str = "private",
    chat_id: int = 200,
    **kwargs: Any,
) -> Update:
    """Build a synthetic Update for a callback query."""
    update = MagicMock(spec=Update)
    user = MagicMock(
        spec=User,
        id=user_id,
        username=username or f"user_{user_id}",
        full_name=full_name or f"User {user_id}",
    )
    chat = MagicMock(
        spec=Chat,
        id=chat_id,
        type=chat_type,
    )
    query = MagicMock(
        spec=CallbackQuery,
        id="cb_1",
        data=data,
        from_user=user,
        message=MagicMock(
            spec=Message,
            chat=chat,
            chat_id=chat_id,
        ),
    )
    query.edit_message_text = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    query.answer = AsyncMock()
    update.callback_query = query
    update.message = None
    update.effective_user = user
    update.effective_chat = chat
    update.effective_message = query.message
    update.get_bot = MagicMock(return_value=MagicMock(username="test_bot"))
    return update
