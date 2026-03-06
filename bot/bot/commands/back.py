#!/usr/bin/env python3
"""Back/unconfirm command handler."""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from config.settings import settings
from db.connection import get_session
from db.models import Event, Log
from db.users import get_or_create_user_id
from bot.common.attendance import (
    derive_state_from_attendance,
    revert_confirmed_to_joined,
)
from datetime import datetime


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /back <event_id> to revert personal confirmation to interested."""
    message = update.effective_message
    if not message or not update.effective_user:
        return
    args = context.args or []
    if not args:
        await message.reply_text("Usage: /back <event_id>")
        return
    try:
        event_id = int(args[0])
    except ValueError:
        await message.reply_text("❌ Event ID must be a number.")
        return

    telegram_user_id = update.effective_user.id
    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(select(Event).where(Event.event_id == event_id))
        ).scalar_one_or_none()
        if not event:
            await message.reply_text("❌ Event not found.")
            return
        if event.state == "locked":
            await message.reply_text("❌ Event is locked. Cannot go back.")
            return

        attendance, had_confirmed = revert_confirmed_to_joined(
            event.attendance_list,
            telegram_user_id,
        )
        if not had_confirmed:
            await message.reply_text(
                "ℹ️ You are not confirmed in this event."
            )
            return

        event.attendance_list = attendance
        event.state = derive_state_from_attendance(attendance)

        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=update.effective_user.full_name,
            username=update.effective_user.username,
        )
        session.add(
            Log(
                event_id=event_id,
                user_id=user_id,
                action="cancel",
                metadata_dict={
                    "timestamp": datetime.utcnow().isoformat(),
                    "sub_action": "back_unconfirm",
                },
            )
        )
        await session.commit()

    await message.reply_text(
        f"↩️ Your confirmation for event {event_id} was reverted.\n"
        f"Current event state: {event.state}\n"
        f"You can recommit with /confirm {event_id}."
    )
