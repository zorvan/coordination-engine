#!/usr/bin/env python3
"""Suggest time command handler for AI time suggestions."""
from typing import cast
from telegram import (
    Update,
    Message,
    InaccessibleMessage,
    MaybeInaccessibleMessage,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes
from db.models import Event
from db.connection import get_session
from config.settings import settings
from ai.core import AICoordinationEngine


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /suggest_time command - request AI time suggestions."""
    if not update.message or not update.effective_user:
        return

    args = context.args or []
    event_id_raw = args[0] if args else None

    if not event_id_raw:
        await update.message.reply_text(
            "Usage: /suggest_time <event_id>\n\n"
            "Example: /suggest_time 123"
        )
        return

    try:
        event_id = int(event_id_raw)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    await _send_suggestion(update.message, event_id)


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for suggest_time buttons."""
    del context
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data
    if not data or not data.startswith("suggest_time_retry_"):
        return

    try:
        event_id = int(data.replace("suggest_time_retry_", ""))
    except ValueError:
        await query.edit_message_text("❌ Invalid event ID in callback.")
        return

    message = query.message
    if not message or isinstance(message, InaccessibleMessage):
        return

    await query.edit_message_text(
        f"🤖 *Requesting new AI time suggestion for event {event_id}...*"
    )
    await _send_suggestion(message, event_id)


async def _send_suggestion(
    message: MaybeInaccessibleMessage, event_id: int
) -> None:
    """Fetch and send AI time suggestion for an event."""
    if isinstance(message, InaccessibleMessage):
        return
    msg = cast(Message, message)

    db_url = settings.db_url or ""
    async for session in get_session(db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            await msg.reply_text("❌ Event not found.")
            await session.close()
            return

        engine = AICoordinationEngine(create_session_factory(db_url))
        suggestion = await engine.suggest_event_time(event_id)
        if "error" in suggestion:
            await msg.reply_text(f"❌ Error: {suggestion['error']}")
            await session.close()
            return

        keyboard = [[
            InlineKeyboardButton(
                "🔄 Request New Suggestion",
                callback_data=f"suggest_time_retry_{event_id}",
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await msg.reply_text(
            f"🤖 *AI Time Suggestion for Event {event_id}*\n\n"
            f"Suggested Time: {suggestion.get('suggested_time', 'TBD')}\n"
            f"Reasoning: {suggestion.get('reasoning', 'N/A')}\n"
            f"Confidence: {suggestion.get('confidence', 0):.2f}\n\n"
            f"Availability Score: "
            f"{suggestion.get('availability_score', 0):.2f}\n"
            f"Reliability Score: {suggestion.get('reliability_score', 0):.2f}",
            reply_markup=reply_markup,
        )
        await session.close()


def create_session_factory(db_url: str):
    """Create session factory for AI coordination engine."""
    from db.connection import create_session
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(db_url)
    return create_session(engine)
