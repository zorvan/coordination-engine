#!/usr/bin/env python3
"""Cancel attendance command handler with nudges."""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select
from db.models import Event, Log
from db.connection import get_session
from db.users import get_or_create_user_id
from config.settings import settings
from datetime import datetime
from bot.utils.nudges import generate_nudge_message


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /cancel command - cancel attendance with nudges."""
    if not update.message:
        return

    user = update.effective_user
    if not user:
        return

    telegram_user_id = user.id
    display_name = user.full_name
    username = user.username
    event_id_str = context.args[0] if context.args else None

    if not event_id_str:
        await update.message.reply_text(
            "Usage: /cancel <event_id>\n\n"
            "Example: /cancel 123"
        )
        return

    try:
        event_id = int(event_id_str)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await update.message.reply_text("❌ Event not found.")
            return

        if event.state == "locked":
            await update.message.reply_text(
                f"❌ Cannot cancel event {event_id} - it's already locked."
            )
            return

        attendance_list = [
            e for e in event.attendance_list
            if not str(e).startswith(f"{telegram_user_id}:confirmed")
        ]

        if telegram_user_id not in attendance_list:
            await update.message.reply_text(
                f"❌ You haven't joined event {event_id} yet. "
                "Nothing to cancel."
            )
            return

        event.attendance_list = attendance_list
        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )

        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="cancel",
            metadata_dict={"timestamp": datetime.utcnow().isoformat()}
        )
        session.add(log)

        await session.commit()

        nudge_msg = generate_nudge_message(
            event_id, telegram_user_id, event.event_type
        )

        await update.message.reply_text(
            f"❌ *Attendance cancelled for event {event_id}!*\n\n"
            f"{nudge_msg}\n\n"
            f"Event: {event.event_type}\n"
            f"Time: {event.scheduled_time}"
        )


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for cancel buttons."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data

    if data and data.startswith("event_cancel_"):
        event_id = int(data.replace("event_cancel_", ""))
        # Create an update object from the callback query
        callback_update = Update(
            update_id=update.update_id,
            callback_query=query
        )
        context.args = [str(event_id)]
        await handle(callback_update, context)
        await query.edit_message_text(
            f"❌ *Attendance cancelled for event {event_id}!*\n\n"
            "You can rejoin anytime using /join."
        )
