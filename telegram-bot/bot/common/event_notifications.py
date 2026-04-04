#!/usr/bin/env python3
"""Private event notification helpers."""
from __future__ import annotations

import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.common.deeplinks import build_start_link
from bot.common.event_presenters import format_user_display
from bot.common.event_formatters import (
    format_date_preset,
    format_time_window,
    format_location_type,
    format_budget_level,
    format_transport_mode,
    format_scheduled_time,
    format_duration,
)
from config.settings import settings


# Date preset labels for display purposes
DATE_PRESET_LABELS = {
    "today": "Today",
    "tomorrow": "Tomorrow",
    "weekend": "Weekend",
    "nextweek": "Next Week",
}


logger = logging.getLogger("coord_bot.event_notifications")


def build_event_invitation_keyboard(
    bot_username: str | None, event_id: int
) -> InlineKeyboardMarkup:
    """Build inline keyboard for event invitation DM."""
    rows: list[list[InlineKeyboardButton]] = []

    rows.append([
        InlineKeyboardButton("✅ Join", callback_data=f"event_join_{event_id}"),
        InlineKeyboardButton("❌ Cancel", callback_data=f"event_cancel_{event_id}"),
    ])

    rows.append([
        InlineKeyboardButton("📅 Set Availability", url=build_start_link(bot_username, f"avail_{event_id}")),
    ])

    rows.append([
        InlineKeyboardButton("❓ Need Help", url=build_start_link(bot_username, f"help_{event_id}")),
    ])

    return InlineKeyboardMarkup(rows)


def build_event_modification_keyboard(
    bot_username: str | None, event_id: int, request_id: str | None = None
) -> InlineKeyboardMarkup:
    """Build inline keyboard for event modification in DM."""
    rows: list[list[InlineKeyboardButton]] = []

    rows.append([
        InlineKeyboardButton("📅 Modify Availability", url=build_start_link(bot_username, f"avail_{event_id}")),
        InlineKeyboardButton("📝 Contact Organizer", url=build_start_link(bot_username, f"contact_{event_id}")),
    ])

    if request_id:
        rows.append([
            InlineKeyboardButton("✅ Approve", callback_data=f"modreq_{request_id}_approve"),
            InlineKeyboardButton("❌ Reject", callback_data=f"modreq_{request_id}_reject"),
        ])

    return InlineKeyboardMarkup(rows)


async def send_event_invitation_dm(
    context: ContextTypes.DEFAULT_TYPE,
    telegram_user_id: int,
    event_data: dict[str, Any],
    event_id: int,
) -> bool:
    """Send event invitation to user via private DM.

    Args:
        context: Telegram context
        telegram_user_id: User's Telegram ID
        event_data: Event details
        event_id: Event ID

    Returns:
        True if DM sent successfully, False otherwise
    """
    if not context.bot:
        return False

    bot_username = context.bot.username

    # Use human-readable formatters
    scheduled_time = format_scheduled_time(
        event_data.get("scheduled_time"),
        include_flexible_note=True
    )

    invitees = event_data.get("invitees", [])
    invite_all = bool(event_data.get("invite_all_members"))
    invitees_summary = (
        "all group members"
        if invite_all else f"{len(invitees)} users"
    )

    # Use human-readable formatters for planning preferences
    location_text = format_location_type(event_data.get("location_type"))
    budget_text = format_budget_level(event_data.get("budget_level"))
    transport_text = format_transport_mode(event_data.get("transport_mode"))
    date_preset_text = format_date_preset(event_data.get("date_preset"))
    time_window_text = format_time_window(event_data.get("time_window"))

    # Escape description for Markdown (avoid parsing errors with special chars)
    description_raw = event_data.get("description", "N/A")
    escaped_description = (
        str(description_raw)
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
    )

    # Format organizer as clickable mention - fetch from DB if not in event_data
    organizer_text = "N/A"
    organizer_user_id = event_data.get("organizer_telegram_user_id")
    organizer_username = event_data.get("organizer_username")
    organizer_display_name = event_data.get("organizer_display_name")

    # If username not provided, try to fetch from database
    if organizer_user_id and not organizer_username:
        try:
            from db.connection import get_session
            from db.models import User
            from sqlalchemy import select
            async with get_session(settings.db_url) as session:
                org_user = (
                    await session.execute(
                        select(User).where(User.telegram_user_id == int(organizer_user_id))
                    )
                ).scalar_one_or_none()
                if org_user:
                    organizer_username = getattr(org_user, "username", None)
                    organizer_display_name = getattr(org_user, "display_name", None)
        except Exception:
            pass  # Use whatever we have

    if organizer_user_id:
        organizer_text = format_user_display(
            telegram_user_id=organizer_user_id,
            username=organizer_username,
            display_name=organizer_display_name,
        )

    try:
        # Escape formatted text for Markdown safety
        scheduled_time_escaped = str(scheduled_time).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
        date_preset_escaped = str(date_preset_text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
        time_window_escaped = str(time_window_text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
        duration_escaped = str(format_duration(event_data.get('duration_minutes'))).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
        location_escaped = str(location_text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
        budget_escaped = str(budget_text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
        transport_escaped = str(transport_text).replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("]", "\\]")
        
        await context.bot.send_message(
            chat_id=telegram_user_id,
            text=(
                f"✨ *Event Invitation*\n\n"
                f"Event ID: {event_id}\n"
                f"Organized by: {organizer_text}\n"
                f"Type: {event_data.get('event_type', 'Not specified')}\n"
                f"Description: {escaped_description}\n"
                f"Time: {scheduled_time_escaped}\n"
                f"Date Preset: {date_preset_escaped}\n"
                f"Time Window: {time_window_escaped}\n"
                f"Duration: {duration_escaped}\n"
                f"Location Type: {location_escaped}\n"
                f"Budget: {budget_escaped}\n"
                f"Transport: {transport_escaped}\n"
                f"Threshold: {event_data.get('threshold_attendance', 'Not set')}\n"
                f"Invitees: {invitees_summary}"
            ),
            reply_markup=build_event_invitation_keyboard(bot_username, event_id),
            parse_mode="Markdown",
        )
        logger.info(f"Event invitation DM sent to user {telegram_user_id} for event {event_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send event invitation DM to user {telegram_user_id}: {e}", exc_info=True)
        return False


async def send_event_modification_request_dm(
    context: ContextTypes.DEFAULT_TYPE,
    telegram_user_id: int,
    event_data: dict[str, Any],
    event_id: int,
    deadline_info: str,
    request_id: str | None = None,
) -> bool:
    """Send event modification request to user via private DM.

    Args:
        context: Telegram context
        telegram_user_id: User's Telegram ID
        event_data: Event details
        event_id: Event ID
        deadline_info: Deadline information text

    Returns:
        True if DM sent successfully, False otherwise
    """
    if not context.bot:
        return False

    bot_username = context.bot.username

    scheduled_time = (
        str(event_data.get("scheduled_time", "TBD")).replace("T", " ")
        if event_data.get("scheduled_time")
        else "TBD (flexible scheduling)"
    )

    location_type_val = event_data.get("location_type")
    location_text = location_type_val.replace("_", " ").title() if location_type_val else "As discussed"

    change_text = event_data.get("change_text", "")
    requester = event_data.get("requester", "Unknown")

    escaped_change = (
        str(change_text)
        .replace("[", "\\[")
        .replace("]", "\\]")
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
    )[:500]

    try:
        await context.bot.send_message(
            chat_id=telegram_user_id,
            text=(
                f"🔧 *Event Modification Request*\n\n"
                f"Event ID: `{event_id}`\n"
                f"Requested by: {requester}\n"
                f"Description: {event_data.get('description', 'N/A')}\n"
                f"Time: {scheduled_time}\n"
                f"Location: {location_text}\n\n"
                f"*Requested changes:*\n{escaped_change}\n\n"
                f"⏰ {deadline_info}\n\n"
                "Please review and approve or reject the requested changes."
            ),
            reply_markup=build_event_modification_keyboard(bot_username, event_id, request_id),
            parse_mode="Markdown",
        )
        logger.info(f"Event modification request DM sent to user {telegram_user_id} for event {event_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send event modification request DM to user {telegram_user_id}: {e}", exc_info=True)
        return False
