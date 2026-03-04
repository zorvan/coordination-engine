#!/usr/bin/env python3
"""Event details command handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.models import Event
from db.connection import get_session
from config.settings import settings


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /event_details command - show detailed event information."""
    if not update.message:
        return

    user = update.effective_user
    if not user:
        return

    event_id_str = context.args[0] if context.args else None

    if not event_id_str:
        await update.message.reply_text(
            "Usage: /event_details <event_id>\n\n"
            "Example: /event_details 123"
        )
        return

    try:
        event_id = int(event_id_str)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    async for session in get_session(settings.db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()

        if not event:
            await update.message.reply_text("❌ Event not found.")
            await session.close()
            return

        logs = await _get_event_logs(session, event_id)
        constraints = await _get_event_constraints(session, event_id)

        keyboard = [
            [
                InlineKeyboardButton(
                    "View Logs", callback_data=f"event_logs_{event_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Manage Constraints",
                    callback_data=f"event_constraints_{event_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    "Close", callback_data=f"event_close_{event_id}"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        attendees = []
        for att in event.attendance_list:
            if str(att).endswith(":confirmed"):
                attendees.append(f"✓ {str(att).replace(':confirmed', '')}")
            else:
                attendees.append(f"- {att}")

        attendees_text = "\n".join(attendees)
        await update.message.reply_text(
            f"📋 *Event {event_id} Details*\n\n"
            f"Type: {event.event_type}\n"
            f"Time: {event.scheduled_time}\n"
            f"Threshold: {event.threshold_attendance}\n"
            f"State: {event.state}\n"
            f"AI Score: {event.ai_score:.2f}\n"
            f"Created: {event.created_at}\n"
            f"Locked: {event.locked_at or 'N/A'}\n"
            f"Completed: {event.completed_at or 'N/A'}\n\n"
            f"Attendees ({len(event.attendance_list)}):\n"
            f"{attendees_text}\n\n"
            f"Logs: {len(logs)}\n"
            f"Constraints: {len(constraints)}",
            reply_markup=reply_markup
        )
        await session.close()


async def handle_callback(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for event detail actions."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data

    if data and data.startswith("event_logs_"):
        event_id = int(data.replace("event_logs_", ""))
        await show_logs(query, event_id)
    elif data and data.startswith("event_constraints_"):
        event_id = int(data.replace("event_constraints_", ""))
        await show_constraints(query, event_id)
    elif data and data.startswith("event_close_"):
        await query.edit_message_text("✅ Event details closed.")


async def show_logs(query, event_id: int) -> None:
    """Show event logs."""
    from db.models import Log as LogModel
    async for session in get_session(settings.db_url):
        result = await session.execute(
            LogModel.__table__.select()
            .where(LogModel.event_id == event_id)
            .order_by(LogModel.timestamp.desc())
        )
        logs = result.scalars().all()

        if not logs:
            await query.edit_message_text(
                f"ℹ️ Event {event_id} has no logs yet."
            )
            await session.close()
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
        await session.close()


async def show_constraints(query, event_id: int) -> None:
    """Show event constraints."""
    from db.models import Constraint as ConstraintModel
    async for session in get_session(settings.db_url):
        result = await session.execute(
            ConstraintModel.__table__.select().where(
                ConstraintModel.event_id == event_id
            )
        )
        constraints = result.scalars().all()

        if not constraints:
            await query.edit_message_text(
                f"ℹ️ Event {event_id} has no constraints."
            )
            await session.close()
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
        await session.close()


async def _get_event_logs(session, event_id: int) -> list:
    """Get event logs."""
    from db.models import Log as LogModel
    result = await session.execute(
        LogModel.__table__.select().where(LogModel.event_id == event_id)
    )
    return result.scalars().all()


async def _get_event_constraints(session, event_id: int) -> list:
    """Get event constraints."""
    from db.models import Constraint as ConstraintModel
    result = await session.execute(
        ConstraintModel.__table__.select().where(
            ConstraintModel.event_id == event_id
        )
    )
    return result.scalars().all()
