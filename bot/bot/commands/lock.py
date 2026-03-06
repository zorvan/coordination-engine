#!/usr/bin/env python3
"""Lock event command handler."""
from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from bot.common.event_states import STATE_EXPLANATIONS
from bot.common.attendance import finalize_commitments
from config.settings import settings
from db.connection import get_session
from db.models import Event


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /lock command - finalize a confirmed event."""
    if not update.message:
        return

    event_id_raw = context.args[0] if context.args else None
    if not event_id_raw:
        await update.message.reply_text(
            "Usage: /lock <event_id>\n\n"
            "Example: /lock 123"
        )
        return

    try:
        event_id = int(event_id_raw)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    if not settings.db_url:
        await update.message.reply_text("❌ Database configuration is unavailable.")
        return

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(
                select(Event).where(Event.event_id == event_id)
            )
        ).scalar_one_or_none()
        if not event:
            await update.message.reply_text("❌ Event not found.")
            return

        if event.state != "confirmed":
            await update.message.reply_text(
                f"❌ Cannot lock event {event_id}.\n"
                f"Current state: {event.state}\n"
                f"Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unavailable')}\n"
                "You can lock only when state is 'confirmed'."
            )
            return

        event.state = "locked"
        event.attendance_list, _ = finalize_commitments(event.attendance_list)
        event.locked_at = datetime.utcnow()
        await session.commit()

    await update.message.reply_text(
        f"🔒 Event {event_id} locked.\n"
        f"State: locked\n"
        f"Meaning: {STATE_EXPLANATIONS['locked']}"
    )
