#!/usr/bin/env python3
"""Status command handler to show event progress."""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import Event, Log, Constraint
from db.connection import get_session
from config.settings import settings
from bot.common.event_presenters import format_status_message


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /status command - show event progress."""
    if not update.message or not update.effective_user:
        return

    args = context.args or []
    event_id_raw = args[0] if args else None

    if not event_id_raw:
        await update.message.reply_text(
            "Usage: /status <event_id>\n\n"
            "Example: /status 123"
        )
        return

    try:
        event_id = int(event_id_raw)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await update.message.reply_text("❌ Event not found.")
            
            return

        log_count = await _get_log_count(session, event_id)
        constraint_count = await _get_constraint_count(session, event_id)
        await update.message.reply_text(
            await format_status_message(event_id, event, log_count, constraint_count, context.bot)
        )
        


async def _get_log_count(session: AsyncSession, event_id: int) -> int:
    """Get log count for an event."""
    from sqlalchemy import func

    result = await session.execute(
        func.count(Log.__table__.c.log_id).select().where(
            Log.event_id == event_id
        )
    )
    return int(result.scalar_one())


async def _get_constraint_count(session: AsyncSession, event_id: int) -> int:
    """Get constraint count for an event."""
    from sqlalchemy import func

    result = await session.execute(
        func.count(Constraint.__table__.c.constraint_id).select().where(
            Constraint.event_id == event_id
        )
    )
    return int(result.scalar_one())
