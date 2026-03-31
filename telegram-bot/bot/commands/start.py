#!/usr/bin/env python3
"""Start command handler."""
from telegram import Update
from telegram.ext import ContextTypes

from bot.handlers import feedback


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    if not update.message:
        return

    args = context.args or []
    payload = args[0] if args else ""
    if payload.startswith("avail_"):
        try:
            event_id = int(payload.replace("avail_", ""))
        except ValueError:
            event_id = None
        if event_id is not None:
            await update.message.reply_text(
                f"📥 *Private Availability Mode*\n\n"
                f"Event ID: {event_id}\n\n"
                "Submit your free slots from DM using:\n"
                f"/constraints {event_id} availability "
                "<YYYY-MM-DD HH:MM,YYYY-MM-DD HH:MM>\n\n"
                "Example:\n"
                f"/constraints {event_id} availability "
                "2026-03-20 18:00,2026-03-21 10:30"
            )
            return

    if payload.startswith("feedback_"):
        try:
            event_id = int(payload.replace("feedback_", ""))
        except ValueError:
            event_id = None
        if event_id is not None:
            context.args = [str(event_id)]
            await feedback.collect_feedback(update, context)
            return

    display_name = (
        update.effective_user.full_name
        if update.effective_user
        else "User"
    )

    await update.message.reply_text(
        f"👋 Hello, {display_name}!\n\n"
        "I'm your coordination bot. I help organize group events with "
        "AI-powered scheduling.\n\n"
        "Available commands:\n"
        "/organize_event - Create a new event\n"
        "/events - List recent events with IDs\n"
        "/my_groups - List your groups\n"
        "/profile - View your profile\n"
        "/reputation - Check your reputation\n"
        "/help - Show this help message"
    )
