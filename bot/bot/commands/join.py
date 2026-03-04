#!/usr/bin/env python3
"""Join event command handler - mark attendance intent."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from db.models import Event, Log
from db.connection import get_session
from db.users import get_or_create_user_id
from config.settings import settings
from datetime import datetime


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /join command - mark attendance intent."""
    if not update.message:
        return

    user = update.effective_user
    if not user:
        return

    telegram_user_id = user.id
    display_name = user.full_name
    event_id_str = context.args[0] if context.args else None

    if not event_id_str:
        await update.message.reply_text(
            "Usage: /join <event_id>\n\n"
            "Example: /join 123"
        )
        return

    try:
        event_id = int(event_id_str)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    async for session in get_session(settings.db_url):
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await update.message.reply_text("❌ Event not found.")
            await session.close()
            return

        if event.state in ["locked", "completed"]:
            await update.message.reply_text(
                f"❌ Cannot join event {event_id} - it's {event.state}."
            )
            await session.close()
            return

        if telegram_user_id not in event.attendance_list:
            event.attendance_list.append(telegram_user_id)
            user_id = await get_or_create_user_id(
                session,
                telegram_user_id=telegram_user_id,
                display_name=display_name,
            )
            log = Log(
                event_id=event_id,
                user_id=user_id,
                action="join",
                metadata_dict={"timestamp": datetime.utcnow().isoformat()}
            )
            session.add(log)
            await session.commit()

        keyboard = [
            [
                InlineKeyboardButton(
                    "✅ Confirm", callback_data=f"event_confirm_{event_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"event_cancel_{event_id}"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"✅ *Joined event {event_id}!*\n\n"
            f"Type: {event.event_type}\n"
            f"Time: {event.scheduled_time}\n"
            f"State: {event.state}\n\n"
            f"Please confirm your attendance.",
            reply_markup=reply_markup
        )
        await session.close()


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for join buttons."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data

    if data and data.startswith("event_join_"):
        event_id = int(data.replace("event_join_", ""))
        # Create an update object from the callback query
        callback_update = Update(
            update_id=update.update_id,
            callback_query=query
        )
        context.args = [str(event_id)]
        await handle(callback_update, context)
        await query.edit_message_text(
            f"✅ *Joined event {event_id}!*\n\n"
            f"Use /status {event_id} to view event details."
        )
