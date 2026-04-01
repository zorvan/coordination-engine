#!/usr/bin/env python3
from __future__ import annotations

from typing import Any

"""Event details command handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from db.models import Event
from bot.common.attendance import has_attendee
from db.connection import get_session
from config.settings import settings
from bot.common.deeplinks import build_start_link
from bot.common.event_presenters import format_event_details_message


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /event_details command - show detailed event information."""
    if not update.message:
        return
    if not settings.db_url:
        await update.message.reply_text(
            "❌ Database configuration is unavailable."
        )
        return

    user = update.effective_user
    if not user:
        return

    event_id_str = context.args[0] if context.args else None

    if not event_id_str:
        await update.message.reply_text(
            "Usage: /event_details <event_id>\n\n"
            "Examples:\n"
            "/event_details 123\n"
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

        logs = await _get_event_logs(session, event_id)
        constraints = await _get_event_constraints(session, event_id)

        bot_username = context.bot.username if context.bot else None
        user_id = user.id if user else None
        reply_markup = await build_event_details_action_markup(event, user_id, bot_username, session)

        await update.message.reply_text(
            await format_event_details_message(event_id, event, logs, constraints),
            reply_markup=reply_markup
        )
        

async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for event detail actions."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data

    if data and data.startswith("event_details_"):
        event_id = int(data.replace("event_details_", ""))
        await show_details(query, context, event_id)
    elif data and data.startswith("event_logs_"):
        event_id = int(data.replace("event_logs_", ""))
        await show_logs(query, event_id)
    elif data and data.startswith("event_constraints_"):
        event_id = int(data.replace("event_constraints_", ""))
        await show_constraints(query, event_id)
    elif data and data.startswith("event_close_"):
        await query.edit_message_text("✅ Event details closed.")


async def show_details(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Show full event details for callback-based navigation."""
    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await query.edit_message_text("❌ Event not found.")
            return

        logs = await _get_event_logs(session, event_id)
        constraints = await _get_event_constraints(session, event_id)

        bot_username = context.bot.username if context.bot else None
        user_id = query.from_user.id if query.from_user else None
        reply_markup = await build_event_details_action_markup(event, user_id, bot_username, session)

        await query.edit_message_text(
            await format_event_details_message(event_id, event, logs, constraints),
            reply_markup=reply_markup
        )


async def show_logs(query, event_id: int) -> None:
    """Show event logs."""
    from db.models import Log as LogModel
    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(LogModel)
            .where(LogModel.event_id == event_id)
            .order_by(LogModel.timestamp.desc())
        )
        logs = result.scalars().all()

        if not logs:
            await query.edit_message_text(
                f"ℹ️ Event {event_id} has no logs yet."
            )
            
            return

        msg = f"📝 *Event {event_id} Logs*\n\n"
        for log in logs[:10]:
            msg += f"- {log.action} by {log.user_id} at {log.timestamp}\n"

        if len(logs) > 10:
            msg += f"\n... and {len(logs) - 10} more logs"

        keyboard = [
            [
                InlineKeyboardButton(
                    "Back", callback_data=f"event_details_{event_id}"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(msg, reply_markup=reply_markup)
        


async def show_constraints(query, event_id: int) -> None:
    """Show event constraints."""
    from db.models import Constraint as ConstraintModel
    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(ConstraintModel).where(
                ConstraintModel.event_id == event_id
            )
        )
        constraints = result.scalars().all()

        if not constraints:
            await query.edit_message_text(
                f"ℹ️ Event {event_id} has no constraints."
            )
            
            return

        msg = f"🔗 *Event {event_id} Constraints*\n\n"
        for c in constraints:
            msg += f"- User {c.user_id}: "
            if c.target_user_id:
                msg += (
                    f"Join if User {c.target_user_id} joins "
                    f"(confidence: {c.confidence})\n"
                )
            else:
                msg += f"{c.type}\n"

        keyboard = [
            [
                InlineKeyboardButton(
                    "Back", callback_data=f"event_details_{event_id}"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(msg, reply_markup=reply_markup)
        


async def _get_event_logs(session, event_id: int) -> list:
    """Get event logs."""
    from db.models import Log as LogModel
    result = await session.execute(
        select(LogModel).where(LogModel.event_id == event_id)
    )
    return result.scalars().all()


async def _get_event_constraints(session, event_id: int) -> list:
    """Get event constraints."""
    from db.models import Constraint as ConstraintModel
    result = await session.execute(
        select(ConstraintModel).where(
            ConstraintModel.event_id == event_id
        )
    )
    return result.scalars().all()


async def build_event_details_action_markup(
    event: Event, user_id: int | None, bot_username: str | None, session
) -> InlineKeyboardMarkup:
    """Build standard action keyboard for event details view."""
    # Check if user has joined using ParticipantService
    user_joined = False
    if user_id is not None:
        from bot.services import ParticipantService
        participant_service = ParticipantService(session)
        try:
            participant = await participant_service.get_participant(event.event_id, user_id)
            user_joined = participant is not None and participant.status in ['joined', 'confirmed']
        except:
            # Fallback to old logic if service fails
            attendance_list: list[Any] | None = event.attendance_list or []
            user_joined = has_attendee(attendance_list, user_id)
    
    commit_text = "✅ Join" if not user_joined else "✅ Commit"
    keyboard = [
        [
            InlineKeyboardButton(commit_text, callback_data=f"event_confirm_{event.event_id}"),
            InlineKeyboardButton("↩️ Back", callback_data=f"event_back_{event.event_id}"),
        ],
        [
            InlineKeyboardButton("❌ Cancel", callback_data=f"event_cancel_{event.event_id}"),
            InlineKeyboardButton("🔒 Lock", callback_data=f"event_lock_{event.event_id}"),
        ],
        [InlineKeyboardButton("View Logs", callback_data=f"event_logs_{event.event_id}")],
        [
            InlineKeyboardButton(
                "Manage Constraints",
                callback_data=f"event_constraints_{event.event_id}",
            )
        ],
        [InlineKeyboardButton("Close", callback_data=f"event_close_{event.event_id}")],
    ]
    if user_joined:
        keyboard.insert(2, [InlineKeyboardButton("🛠 Modify", callback_data=f"event_modify_{event.event_id}")])
    avail_link = build_start_link(bot_username, f"avail_{event.event_id}")
    feedback_link = build_start_link(bot_username, f"feedback_{event.event_id}")
    if avail_link:
        keyboard.append(
            [InlineKeyboardButton("📥 Set Availability in DM", url=avail_link)]
        )
    if feedback_link:
        keyboard.append(
            [InlineKeyboardButton("⭐ Give Feedback in DM", url=feedback_link)]
        )
    return InlineKeyboardMarkup(keyboard)