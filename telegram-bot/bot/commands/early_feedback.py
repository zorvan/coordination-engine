#!/usr/bin/env python3
"""Early feedback command handler."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from ai.llm import LLMClient
from bot.common.early_feedback import add_early_feedback_signal
from config.settings import settings
from db.connection import get_session
from db.models import Event
from db.users import get_or_create_user_id, get_user_id_by_username


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /early_feedback <event_id> <@username|telegram_id> <free text>."""
    if not update.message or not update.effective_user:
        return
    if not settings.db_url:
        await update.message.reply_text("❌ Database configuration is unavailable.")
        return

    args = context.args or []
    if len(args) < 3:
        await update.message.reply_text(
            "Usage: /early_feedback <event_id> <@username|telegram_user_id> <text>\n\n"
            "Examples:\n"
            "/early_feedback 12 @alice Always late to pre-event planning\n"
            "/early_feedback 12 123456789 Very cooperative in discussion"
        )
        return

    event_id_raw = args[0]
    target_input = args[1].strip()
    free_text = " ".join(args[2:]).strip()
    if not free_text:
        await update.message.reply_text("❌ Feedback text cannot be empty.")
        return
    try:
        event_id = int(event_id_raw)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    source_type = (
        "private_peer"
        if (update.effective_chat and update.effective_chat.type == "private")
        else "discussion"
    )
    is_private = source_type == "private_peer"

    llm = LLMClient()
    try:
        inferred = await llm.infer_early_feedback_from_text(free_text)
    finally:
        await llm.close()

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(select(Event).where(Event.event_id == event_id))
        ).scalar_one_or_none()
        if not event:
            await update.message.reply_text("❌ Event not found.")
            return

        source_user_id = await get_or_create_user_id(
            session,
            telegram_user_id=update.effective_user.id,
            display_name=update.effective_user.full_name,
            username=update.effective_user.username,
        )

        if target_input.startswith("@"):
            target_user_id = await get_user_id_by_username(session, target_input)
            if target_user_id is None:
                await update.message.reply_text(
                    f"❌ Target user {target_input} was not found."
                )
                return
            target_label = target_input
        else:
            try:
                target_telegram_id = int(target_input)
            except ValueError:
                await update.message.reply_text(
                    "❌ Target must be @username or numeric telegram user id."
                )
                return
            target_user_id = await get_or_create_user_id(
                session,
                telegram_user_id=target_telegram_id,
                display_name=None,
                username=None,
            )
            target_label = str(target_telegram_id)

        await add_early_feedback_signal(
            session,
            event_id=event_id,
            source_user_id=source_user_id,
            target_user_id=target_user_id,
            source_type=source_type,
            signal_type=str(inferred.get("signal_type", "overall")),
            value=float(inferred.get("score", 3.0)),
            weight=float(inferred.get("weight", 0.6)),
            confidence=float(inferred.get("confidence", 0.7)),
            sanitized_comment=str(inferred.get("sanitized_comment", free_text)),
            is_private=is_private,
            metadata={"raw_text_len": len(free_text)},
        )
        await session.commit()

    await update.message.reply_text(
        "✅ Early feedback saved.\n\n"
        f"Event: {event_id}\n"
        f"Target: {target_label}\n"
        f"Source: {source_type}\n"
        f"Signal: {str(inferred.get('signal_type', 'overall'))}\n"
        f"Score: {float(inferred.get('score', 3.0)):.2f}\n"
        f"Weight: {float(inferred.get('weight', 0.6)):.2f}"
    )
