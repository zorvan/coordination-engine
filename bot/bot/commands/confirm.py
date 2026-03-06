#!/usr/bin/env python3
"""Confirm event command handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from db.models import Event, Log
from db.connection import get_session
from db.users import get_or_create_user_id
from config.settings import settings
from bot.common.scheduling import find_user_event_conflict
from bot.common.attendance import mark_confirmed
from datetime import datetime


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /confirm|/interested command - mark attendance commitment."""
    message = update.effective_message
    if not message:
        return

    user = update.effective_user
    if not user:
        return

    telegram_user_id = user.id
    display_name = user.full_name
    username = user.username
    event_id_str = context.args[0] if context.args else None

    if not event_id_str:
        await message.reply_text(
            "Usage: /confirm <event_id>\n\n"
            "Example: /confirm 123"
        )
        return

    try:
        event_id = int(event_id_str)
    except ValueError:
        await message.reply_text("❌ Event ID must be a number.")
        return

    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await message.reply_text("❌ Event not found.")
            return

        if event.state == "locked":
            await message.reply_text(
                f"❌ Cannot confirm event {event_id} - it's already locked."
            )
            return

        if event.state in ["completed", "cancelled"]:
            await message.reply_text(
                f"❌ Cannot confirm event {event_id} - it's {event.state}."
            )
            return

        conflict = await find_user_event_conflict(
            session=session,
            telegram_user_id=telegram_user_id,
            start_time=event.scheduled_time,
            duration_minutes=event.duration_minutes,
            ignore_event_id=event.event_id,
        )
        if conflict:
            await message.reply_text(
                "❌ You have a conflicting event.\n"
                f"Conflicting Event ID: {conflict.event_id}\n"
                f"Time: {conflict.scheduled_time}\n"
                f"Duration: {conflict.duration_minutes or 120} minutes"
            )
            return

        new_attendance, _ = mark_confirmed(
            event.attendance_list,
            telegram_user_id,
        )
        event.attendance_list = new_attendance
        event.state = "confirmed"
        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )

        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="confirm",
            metadata_dict={"timestamp": datetime.utcnow().isoformat()}
        )
        session.add(log)
        await session.commit()

        reply_markup = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "↩️ Back", callback_data=f"event_back_{event_id}"
                    ),
                    InlineKeyboardButton(
                        "🔒 Lock Event", callback_data=f"event_lock_{event_id}"
                    ),
                ]
            ]
        )
        await message.reply_text(
            f"✅ *Committed to event {event_id}!*\n\n"
            f"Type: {event.event_type}\n"
            f"Time: {event.scheduled_time}\n"
            f"State: {event.state}\n"
            f"Use /back {event_id} to revert commitment before lock.",
            reply_markup=reply_markup,
        )
        


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for confirm buttons."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data

    if data and data.startswith("event_confirm_"):
        event_id = int(data.replace("event_confirm_", ""))
        # Create an update object from the callback query
        callback_update = Update(
            update_id=update.update_id,
            callback_query=query
        )
        context.args = [str(event_id)]
        await handle(callback_update, context)
        await query.edit_message_text(
            f"✅ *Committed to event {event_id}!*\n\n"
            f"Use /status {event_id} to view event progress."
        )
