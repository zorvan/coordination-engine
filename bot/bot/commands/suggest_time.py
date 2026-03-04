#!/usr/bin/env python3
"""Suggest time command handler for AI time suggestions."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.models import Event
from db.connection import get_session
from config.settings import settings
from ai.core import AICoordinationEngine


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /suggest_time command - request AI time suggestions."""
    if not update.message or not update.effective_user:
        return
    
    event_id = context.args[0] if context.args else None
    
    if not event_id:
        await update.message.reply_text(
            "Usage: /suggest_time <event_id>\n\n"
            "Example: /suggest_time 123"
        )
        return
    
    try:
        event_id = int(event_id)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return
    
    db_url = settings.db_url or ""
    async for session in get_session(db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await update.message.reply_text("❌ Event not found.")
            await session.close()
            return
        
        engine = AICoordinationEngine(create_session_factory(db_url))
        result = await engine.suggest_event_time(event_id)
        
        if "error" in result:
            await update.message.reply_text(f"❌ Error: {result['error']}")
            await session.close()
            return
        
        keyboard = [
            [InlineKeyboardButton("🔄 Request New Suggestion", callback_data=f"suggest_time_retry_{event_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"🤖 *AI Time Suggestion for Event {event_id}*\n\n"
            f"Suggested Time: {result.get('suggested_time', 'TBD')}\n"
            f"Reasoning: {result.get('reasoning', 'N/A')}\n"
            f"Confidence: {result.get('confidence', 0):.2f}\n\n"
            f"Availability Score: {result.get('availability_score', 0):.2f}\n"
            f"Reliability Score: {result.get('reliability_score', 0):.2f}",
            reply_markup=reply_markup
        )
        await session.close()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for suggest_time buttons."""
    query = update.callback_query
    if not query:
        return
    await query.answer()
    
    data = query.data
    
    if data.startswith("suggest_time_retry_"):
        event_id = int(data.replace("suggest_time_retry_", ""))
        context.args = [str(event_id)]
        await handle(query, context)
        if query.message:
            await query.edit_message_text(
                f"🤖 *Requesting new AI time suggestion for event {event_id}...*\n\n"
            )


def create_session_factory(db_url: str):
    """Create session factory for AI coordination engine."""
    from db.connection import create_session
    from sqlalchemy.ext.asyncio import create_async_engine
    engine = create_async_engine(db_url)
    return create_session(engine)