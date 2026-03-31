#!/usr/bin/env python3
"""Private event note command."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from ai.llm import LLMClient
from bot.common.early_feedback import add_early_feedback_signal
from bot.common.event_access import get_event_organizer_telegram_id, is_attendee
from config.settings import settings
from db.connection import get_session
from db.models import Event
from db.users import get_or_create_user_id


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /event_note <event_id> <note text> in private chat."""
    if not update.message or not update.effective_user or not update.effective_chat:
        return
    if update.effective_chat.type != "private":
        await update.message.reply_text(
            "❌ Event notes are private. Use this command in DM with the bot."
        )
        return

    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /event_note <event_id> <note>\n\n"
            "Example: /event_note 12 I can only attend if start is after 18:00"
        )
        return
    try:
        event_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return
    raw_note = " ".join(args[1:]).strip()
    if not raw_note:
        await update.message.reply_text("❌ Note cannot be empty.")
        return

    llm = LLMClient()
    try:
        inferred = await llm.infer_early_feedback_from_text(raw_note)
    finally:
        await llm.close()

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(select(Event).where(Event.event_id == event_id))
        ).scalar_one_or_none()
        if not event:
            await update.message.reply_text("❌ Event not found.")
            return

        requester_tg_id = int(update.effective_user.id)
        organizer_id = get_event_organizer_telegram_id(event)
        if organizer_id is not None and requester_tg_id == organizer_id:
            await update.message.reply_text(
                "❌ Organizer cannot submit attendee private notes."
            )
            return
        if not is_attendee(event, requester_tg_id):
            await update.message.reply_text(
                "❌ Only interested attendees can submit private notes."
            )
            return

        source_user_id = await get_or_create_user_id(
            session,
            telegram_user_id=requester_tg_id,
            display_name=update.effective_user.full_name,
            username=update.effective_user.username,
        )
        # Store note as a private discussion signal targeting organizer for planning context.
        target_user_tg = organizer_id if organizer_id is not None else requester_tg_id
        target_user_id = await get_or_create_user_id(
            session,
            telegram_user_id=target_user_tg,
            display_name=None,
            username=None,
        )
        await add_early_feedback_signal(
            session,
            event_id=event_id,
            source_user_id=source_user_id,
            target_user_id=target_user_id,
            source_type="private_peer",
            signal_type="overall",
            value=float(inferred.get("score", 3.0)),
            weight=float(inferred.get("weight", 0.6)),
            confidence=float(inferred.get("confidence", 0.7)),
            sanitized_comment=str(inferred.get("sanitized_comment", raw_note)),
            is_private=True,
            metadata={"role": "event_note", "raw_text_len": len(raw_note)},
        )
        await session.commit()

    await update.message.reply_text(
        "✅ Private note saved and linked to event planning context."
    )
