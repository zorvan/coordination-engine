#!/usr/bin/env python3
"""Organize event command handler."""
from datetime import datetime
from typing import Any
from telegram import (
    Update,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes
from sqlalchemy import select

from config.settings import settings
from db.connection import create_session, create_engine
from db.models import Event, Group


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /organize_event command - start event creation flow."""
    if not update.message or not update.effective_chat:
        return

    chat = update.effective_chat
    chat_type = chat.type
    if chat_type not in {"group", "supergroup"}:
        await update.message.reply_text(
            "❌ This command can only be used in a Telegram group."
        )
        return

    chat_id = chat.id
    chat_title = chat.title or str(chat_id)
    telegram_user_id = (
        update.effective_user.id if update.effective_user else None
    )

    engine = create_engine(settings.db_url)
    Session = create_session(engine)

    async with Session() as session:
        result = await session.execute(
            select(Group).where(Group.telegram_group_id == chat_id)
        )
        group = result.scalar_one_or_none()

        if not group:
            group = Group(
                telegram_group_id=chat_id,
                group_name=chat_title,
                member_list=[telegram_user_id] if telegram_user_id else [],
            )
            session.add(group)
            await session.commit()
            await session.refresh(group)
        else:
            changed = False
            if chat_title and group.group_name != chat_title:
                group.group_name = chat_title
                changed = True

            current_members = group.member_list or []
            if telegram_user_id and telegram_user_id not in current_members:
                group.member_list = [*current_members, telegram_user_id]
                changed = True

            if changed:
                await session.commit()


    if context.user_data is None:
        await update.message.reply_text("❌ User session data is unavailable.")
        return

    context.user_data["event_flow"] = {
        "stage": "type",
        "group_id": group.group_id,
        "data": {},
    }

    keyboard = [
        [InlineKeyboardButton("Social", callback_data="event_type_social")],
        [InlineKeyboardButton("Sports", callback_data="event_type_sports")],
        [InlineKeyboardButton("Work", callback_data="event_type_work")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "📋 *Event Type*\n\n"
        "What type of event would you like to organize?",
        reply_markup=reply_markup,
    )


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for event type selection."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data

    if context.user_data is None:
        await query.edit_message_text("❌ User session data is unavailable.")
        return

    event_flow_raw = context.user_data.get("event_flow")
    event_flow: dict[str, Any] = (
        event_flow_raw if isinstance(event_flow_raw, dict) else {}
    )
    flow_data = event_flow.get("data")
    if not isinstance(flow_data, dict):
        flow_data = {}
        event_flow["data"] = flow_data

    if data and data.startswith("event_type_"):
        event_type = data.replace("event_type_", "")
        event_flow["stage"] = "time"
        flow_data["event_type"] = event_type
        context.user_data["event_flow"] = event_flow

        await query.edit_message_text(
            f"📅 *Event Type: {event_type}*\n\n"
            "Now enter the scheduled time for the event.\n"
            "Format: YYYY-MM-DD HH:MM (e.g., 2026-03-15 18:00)"
        )

    elif data and data.startswith("event_threshold_"):
        threshold = int(data.replace("event_threshold_", ""))
        event_flow["stage"] = "invitees"
        flow_data["threshold_attendance"] = threshold
        context.user_data["event_flow"] = event_flow

        await query.edit_message_text(
            f"✅ *Threshold: {threshold}*\n\n"
            "Now enter the invitees (user IDs, comma-separated).\n"
            "Example: 123456789,987654321"
        )

    elif data and data.startswith("event_final_"):
        await finalize_event(query, context)

    elif data and data.startswith("event_cancel_"):
        context.user_data.pop("event_flow", None)
        await query.edit_message_text("❌ Event creation cancelled.")


async def handle_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle text messages during event creation flow."""
    if not update.message or not update.effective_user:
        return

    if context.user_data is None:
        return

    event_flow_raw = context.user_data.get("event_flow")
    if not isinstance(event_flow_raw, dict) or not event_flow_raw:
        return

    event_flow: dict[str, Any] = event_flow_raw
    flow_data = event_flow.get("data")
    if not isinstance(flow_data, dict):
        flow_data = {}
        event_flow["data"] = flow_data

    stage = event_flow.get("stage")
    user_id = update.effective_user.id

    if stage == "time":
        text = update.message.text
        if text is None:
            await update.message.reply_text(
                "❌ Please send time as text in format: YYYY-MM-DD HH:MM"
            )
            return

        try:
            scheduled_time = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M")
            event_flow["stage"] = "threshold"
            flow_data["scheduled_time"] = scheduled_time.isoformat()
            context.user_data["event_flow"] = event_flow

            keyboard = [
                [
                    InlineKeyboardButton(
                        "3", callback_data="event_threshold_3"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "5", callback_data="event_threshold_5"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "8", callback_data="event_threshold_8"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "10", callback_data="event_threshold_10"
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"⏱️ *Time: {scheduled_time}*\n\n"
                "What is the minimum attendance threshold?",
                reply_markup=reply_markup,
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format. Please use: YYYY-MM-DD HH:MM"
            )

    elif stage == "invitees":
        text = update.message.text
        if text is None:
            await update.message.reply_text(
                "❌ Invalid user IDs. Please enter comma-separated numeric IDs."
            )
            return

        try:
            invitees = [int(x.strip()) for x in text.split(",") if x.strip()]
            event_flow["stage"] = "final"
            flow_data["invitees"] = invitees
            flow_data["creator"] = user_id
            context.user_data["event_flow"] = event_flow

            data = flow_data
            keyboard = [
                [
                    InlineKeyboardButton(
                        "✅ Confirm", callback_data="event_final_yes"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "❌ Cancel", callback_data="event_cancel_no"
                    )
                ],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await update.message.reply_text(
                f"✨ *Event Summary*\n\n"
                f"Type: {data.get('event_type', 'N/A')}\n"
                f"Time: {data.get('scheduled_time', 'N/A')}\n"
                f"Threshold: {data.get('threshold_attendance', 'N/A')}\n"
                f"Invitees: {len(invitees)} users\n\n"
                "Create this event?",
                reply_markup=reply_markup,
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid user IDs. Please enter comma-separated numeric IDs."
            )


async def finalize_event(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Finalize and create the event in database."""
    if context.user_data is None:
        await query.edit_message_text("❌ User session data is unavailable.")
        return

    event_flow_raw = context.user_data.get("event_flow")
    if not isinstance(event_flow_raw, dict):
        await query.edit_message_text("❌ Event flow not found.")
        return

    event_flow: dict[str, Any] = event_flow_raw
    data_raw = event_flow.get("data")
    if not isinstance(data_raw, dict):
        await query.edit_message_text("❌ Event flow data is invalid.")
        return
    data: dict[str, Any] = data_raw

    scheduled_time_raw = data.get("scheduled_time")
    if not isinstance(scheduled_time_raw, str):
        await query.edit_message_text("❌ Event time is missing.")
        return

    group_id = event_flow.get("group_id")
    if not isinstance(group_id, int):
        await query.edit_message_text("❌ Group context is missing.")
        return

    engine = create_engine(settings.db_url)
    Session = create_session(engine)

    async with Session() as session:
        event = Event(
            group_id=group_id,
            event_type=data.get("event_type", "general"),
            scheduled_time=datetime.fromisoformat(scheduled_time_raw),
            threshold_attendance=data.get("threshold_attendance", 5),
            attendance_list=[data.get("creator", query.from_user.id)],
            state="proposed",
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

    context.user_data.pop("event_flow", None)

    keyboard = [
        [
            InlineKeyboardButton(
                "View Event", callback_data=f"event_details_{event.event_id}"
            )
        ],
        [InlineKeyboardButton("Join", callback_data=f"event_join_{event.event_id}")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        f"✅ *Event Created!*\n\n"
        f"Type: {data.get('event_type', 'N/A')}\n"
        f"Time: {data.get('scheduled_time', 'N/A')}\n"
        f"Threshold: {data.get('threshold_attendance', 'N/A')}\n"
        f"Invitees: {len(data.get('invitees', []))} users",
        reply_markup=reply_markup,
    )
