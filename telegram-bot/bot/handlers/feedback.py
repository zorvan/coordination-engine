#!/usr/bin/env python3
"""Feedback collection handler for post-event ratings."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from db.models import Event, Feedback, User
from db.connection import get_session
from db.users import get_or_create_user_id
from config.settings import settings
from bot.common.rbac import check_event_visibility_and_get_event
from ai.llm import LLMClient
from datetime import datetime
import random


async def collect_feedback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Collect post-event feedback from attendees."""
    if not update.message:
        return

    args = context.args or []
    event_id_str = args[0] if args else None

    if not event_id_str:
        await update.message.reply_text(
            "Usage: /feedback <event_id>\n\n"
            "Example: /feedback 123"
        )
        return

    try:
        event_id = int(event_id_str)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        user_id_num = user.id if user else None
        chat_id = update.effective_chat.id if update.effective_chat else None
        is_visible, event, group, error_msg = (
            await check_event_visibility_and_get_event(
                session, event_id, user_id_num,
                telegram_chat_id=chat_id,
                bot=context.bot,
            )
        )

        if not is_visible:
            await update.message.reply_text(f"❌ {error_msg or 'Event not found.'}")
            return

        if event.state != "completed":
            await update.message.reply_text(
                f"❌ Event {event_id} is not completed yet. "
                "Wait until the event is finished."
            )

            return

        user = update.effective_user
        if not user:
            return

        telegram_user_id = user.id
        display_name = user.full_name
        username = user.username
        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )

        existing = await _get_existing_feedback(session, event_id, user_id)
        if existing:
            await update.message.reply_text(
                "ℹ️ You have already provided feedback for this event."
            )

            return

        # Natural-language feedback mode:
        # /feedback <event_id> <free text...>
        if len(args) > 1:
            free_text = " ".join(args[1:]).strip()
            if not free_text:
                await update.message.reply_text(
                    "❌ Feedback text is empty."
                )
                return
            parsed = await _infer_feedback(event.event_type, free_text)
            await _store_feedback_and_update_reputation(
                session=session,
                event=event,
                user_id=user_id,
                score=float(parsed.get("score", 3.0)),
                weight=float(parsed.get("weight", 0.7)),
                sanitized_comment=str(parsed.get("sanitized_comment", free_text)),
                expertise_adjustments=parsed.get("expertise_adjustments", {}),
            )
            await session.commit()
            await update.message.reply_text(
                "✅ *Feedback Recorded (AI Parsed)*\n\n"
                f"Score: {float(parsed.get('score', 3.0)):.2f}\n"
                f"Weight: {float(parsed.get('weight', 0.7)):.2f}\n"
                f"Comment: {str(parsed.get('sanitized_comment', ''))}"
            )
            return

        keyboard = [
            [
                InlineKeyboardButton(
                    "1 ⭐", callback_data=f"feedback_{event_id}_1"
                ),
                InlineKeyboardButton(
                    "2 ⭐", callback_data=f"feedback_{event_id}_2"
                ),
                InlineKeyboardButton(
                    "3 ⭐", callback_data=f"feedback_{event_id}_3"
                ),
            ],
            [
                InlineKeyboardButton(
                    "4 ⭐", callback_data=f"feedback_{event_id}_4"
                ),
                InlineKeyboardButton(
                    "5 ⭐", callback_data=f"feedback_{event_id}_5"
                ),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"⭐ *Rate Event {event_id}*\n\n"
            f"Type: {event.event_type}\n"
            f"Time: {event.scheduled_time}\n\n"
            "Please rate your experience:",
            reply_markup=reply_markup
        )



async def handle_feedback_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle feedback callback queries."""
    query = update.callback_query
    if not query:
        return
    await query.answer()

    data = query.data

    if data and data.startswith("feedback_"):
        parts = data.split("_")
        if len(parts) >= 3:
            event_id = int(parts[1])
            score = int(parts[2])
            await process_feedback(query, context, event_id, score)


async def process_feedback(
    query, _context: ContextTypes.DEFAULT_TYPE, event_id: int, score: int
) -> None:
    """Process feedback submission."""
    telegram_user_id = query.from_user.id
    display_name = query.from_user.full_name
    username = query.from_user.username

    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        chat_id = getattr(getattr(query, "message", None), "chat_id", None)
        is_visible, event, group, error_msg = (
            await check_event_visibility_and_get_event(
                session, event_id, telegram_user_id,
                telegram_chat_id=chat_id,
                bot=context.bot,
            )
        )

        if not is_visible:
            await query.edit_message_text(f"❌ {error_msg or 'Event not found.'}")
            return

        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )

        await _store_feedback_and_update_reputation(
            session=session,
            event=event,
            user_id=user_id,
            score=float(score),
            weight=1.0,
            sanitized_comment="",
            expertise_adjustments={},
        )
        await session.commit()

        await query.edit_message_text(
            f"⭐ *Thank you for your feedback!*\n\n"
            f"Event {event_id}: {score} out of 5 stars"
        )



async def _get_existing_feedback(session, event_id: int, user_id: int):
    """Check if user already provided feedback."""
    result = await session.execute(
        select(Feedback).where(
            Feedback.event_id == event_id,
            Feedback.user_id == user_id
        )
    )
    return result.scalar_one_or_none()


def generate_random_feedback_request(event_id: int) -> str:
    """Generate a random feedback request message."""
    templates = [
        f"⭐ How was event {event_id}? Please share your feedback!",
        f"🔔 Event {event_id} is complete. Rate your experience!",
        (
            f"📋 What did you think about event {event_id}? "
            "We'd love your feedback!"
        ),
        (
            f"✅ Event {event_id} ended. Your feedback helps us improve!"
        ),
    ]
    return random.choice(templates)


async def _infer_feedback(event_type: str, text: str) -> dict:
    """Infer weighted structured feedback from free text."""
    llm = LLMClient()
    try:
        return await llm.infer_feedback_from_text(event_type, text)
    finally:
        await llm.close()


async def _store_feedback_and_update_reputation(
    session,
    event: Event,
    user_id: int,
    score: float,
    weight: float,
    sanitized_comment: str,
    expertise_adjustments: dict,
) -> None:
    """Persist feedback as a factual record."""
    persisted_comment = (
        f"[score={float(score):.2f}] {sanitized_comment}".strip()
        if sanitized_comment
        else f"[score={float(score):.2f}]"
    )
    feedback = Feedback(
        event_id=event.event_id,
        user_id=user_id,
        score_type="event_quality",
        value=float(max(0.0, min(5.0, score))),
        comment=persisted_comment[:2000],
        timestamp=datetime.utcnow()
    )
    session.add(feedback)
