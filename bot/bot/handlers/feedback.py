#!/usr/bin/env python3
"""Feedback collection handler for post-event ratings."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from db.models import Event, Feedback
from db.connection import get_session
from db.users import get_or_create_user_id
from config.settings import settings
from datetime import datetime
import random


async def collect_feedback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Collect post-event feedback from attendees."""
    if not update.message:
        return

    event_id_str = context.args[0] if context.args else None

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
    async for session in get_session(db_url):
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await update.message.reply_text("❌ Event not found.")
            await session.close()
            return

        if event.state != "completed":
            await update.message.reply_text(
                f"❌ Event {event_id} is not completed yet. "
                "Wait until the event is finished."
            )
            await session.close()
            return

        user = update.effective_user
        if not user:
            return

        telegram_user_id = user.id
        display_name = user.full_name
        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
        )

        existing = await _get_existing_feedback(session, event_id, user_id)
        if existing:
            await update.message.reply_text(
                "ℹ️ You have already provided feedback for this event."
            )
            await session.close()
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
        await session.close()


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
    
    db_url = settings.db_url or ""
    async for session in get_session(db_url):
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            await session.close()
            return

        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
        )
        
        feedback = Feedback(
            event_id=event_id,
            user_id=user_id,
            score_type="event_quality",
            value=float(score),
            timestamp=datetime.utcnow()
        )
        session.add(feedback)

        await session.commit()
        
        await query.edit_message_text(
            f"⭐ *Thank you for your feedback!*\n\n"
            f"Event {event_id}: {score} out of 5 stars"
        )
        await session.close()


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
