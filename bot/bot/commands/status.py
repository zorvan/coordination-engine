#!/usr/bin/env python3
"""Status command handler to show event progress."""
from telegram import Update
from telegram.ext import ContextTypes
from db.models import Event, Log, Constraint
from db.connection import get_session
from config.settings import settings


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show event progress."""
    if not update.message:
        return
    
    user_id = update.effective_user.id
    event_id = context.args[0] if context.args else None
    
    if not event_id:
        await update.message.reply_text(
            "Usage: /status <event_id>\n\n"
            "Example: /status 123"
        )
        return
    
    try:
        event_id = int(event_id)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return
    
    async for session in get_session(settings.db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await update.message.reply_text("❌ Event not found.")
            await session.close()
            return
        
        log_count = await _get_log_count(session, event_id)
        constraint_count = await _get_constraint_count(session, event_id)
        
        await update.message.reply_text(
            f"📊 *Event {event_id} Status*\n\n"
            f"Type: {event.event_type}\n"
            f"Time: {event.scheduled_time}\n"
            f"Threshold: {event.threshold_attendance}\n"
            f"State: {event.state}\n"
            f"AI Score: {event.ai_score:.2f}\n\n"
            f"Attendees: {len(event.attendance_list)}\n"
            f"Logs: {log_count}\n"
            f"Constraints: {constraint_count}\n"
            f"Created: {event.created_at}"
        )
        await session.close()


async def _get_log_count(session, event_id: int) -> int:
    """Get log count for an event."""
    from sqlalchemy import func
    result = await session.execute(
        func.count(Log.__table__.c.log_id).select().where(Log.event_id == event_id)
    )
    return result.scalar()


async def _get_constraint_count(session, event_id: int) -> int:
    """Get constraint count for an event."""
    from sqlalchemy import func
    result = await session.execute(
        func.count(Constraint.__table__.c.constraint_id).select().where(Constraint.event_id == event_id)
    )
    return result.scalar()