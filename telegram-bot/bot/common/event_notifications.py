#!/usr/bin/env python3
"""Private event notification helpers."""
from __future__ import annotations

import logging
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from bot.common.deeplinks import build_start_link
from bot.common.event_presenters import format_user_display
from config.settings import settings


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

    scheduled_time = (
        str(event_data.get("scheduled_time", "TBD")).replace("T", " ")
        if event_data.get("scheduled_time")
        else "TBD (flexible scheduling)"
    )

    invitees = event_data.get("invitees", [])
    invite_all = bool(event_data.get("invite_all_members"))
    invitees_summary = (
        "all group members"
        if invite_all else f"{len(invitees)} users"
    )

    location_text = str(event_data.get("location_type", "any")).replace("_", " ").title()
    budget_text = str(event_data.get("budget_level", "any")).replace("_", " ").title()
    transport_text = str(event_data.get("transport_mode", "any")).replace("_", " ").title()
    date_preset_text = str(event_data.get("date_preset", "custom")).title()
    time_window_text = str(event_data.get("time_window", "custom")).title()

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
        await context.bot.send_message(
            chat_id=telegram_user_id,
            text=(
                f"✨ *Event Invitation*\n\n"
                f"Event ID: {event_id}\n"
                f"Organized by: {organizer_text}\n"
                f"Type: {event_data.get('event_type', 'N/A')}\n"
                f"Description: {escaped_description}\n"
                f"Time: {scheduled_time}\n"
                f"Date Preset: {date_preset_text}\n"
                f"Time Window: {time_window_text}\n"
                f"Duration: {event_data.get('duration_minutes', 120)} minutes\n"
                f"Location Type: {location_text}\n"
                f"Budget: {budget_text}\n"
                f"Transport: {transport_text}\n"
                f"Threshold: {event_data.get('threshold_attendance', 'N/A')}\n"
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

    location_text = str(event_data.get("location_type", "any")).replace("_", " ").title()

    try:
        await context.bot.send_message(
            chat_id=telegram_user_id,
            text=(
                f"📅 *Event Modification Request*\n\n"
                f"Event ID: {event_id}\n"
                f"Description: {event_data.get('description', 'N/A')}\n"
                f"Time: {scheduled_time}\n"
                f"Location: {location_text}\n\n"
                f"Deadline: {deadline_info}\n\n"
                "Please review the event and let the organizer know if you can attend "
                "or if you need to modify your availability."
            ),
            reply_markup=build_event_modification_keyboard(bot_username, event_id, request_id),
        )
        logger.info(f"Event modification request DM sent to user {telegram_user_id} for event {event_id}")
        return True
    except Exception as e:
        logger.error(f"Failed to send event modification request DM to user {telegram_user_id}: {e}", exc_info=True)
        return False
