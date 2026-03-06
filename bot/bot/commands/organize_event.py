#!/usr/bin/env python3
"""Organize event command handler."""
from calendar import Calendar, month_name
from datetime import datetime
import re
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
from bot.common.deeplinks import build_start_link
from bot.common.keyboards import build_threshold_markup
from bot.common.scheduling import find_user_event_conflict
from db.connection import get_session
from db.models import Event, Group


CALENDAR_WEEKDAYS = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
TELEGRAM_HANDLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


def build_calendar_markup(year: int, month: int) -> InlineKeyboardMarkup:
    """Build month-view inline calendar keyboard."""
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [InlineKeyboardButton(
            f"{month_name[month]} {year}", callback_data="event_cal_ignore"
        )]
    )
    rows.append(
        [
            InlineKeyboardButton(day, callback_data="event_cal_ignore")
            for day in CALENDAR_WEEKDAYS
        ]
    )

    cal = Calendar(firstweekday=0)
    for week in cal.monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(
                    InlineKeyboardButton(" ", callback_data="event_cal_ignore")
                )
            else:
                row.append(
                    InlineKeyboardButton(
                        str(day),
                        callback_data=f"event_cal_day_{year}_{month}_{day}",
                    )
                )
        rows.append(row)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    rows.append(
        [
            InlineKeyboardButton(
                "◀️",
                callback_data=f"event_cal_nav_{prev_year}_{prev_month}",
            ),
            InlineKeyboardButton(" ", callback_data="event_cal_ignore"),
            InlineKeyboardButton(
                "▶️",
                callback_data=f"event_cal_nav_{next_year}_{next_month}",
            ),
        ]
    )

    return InlineKeyboardMarkup(rows)


def parse_invitee_handles(raw_text: str) -> list[str]:
    """Parse comma-separated @handles and return normalized unique handles."""
    handles: list[str] = []
    seen: set[str] = set()
    tokens = [token.strip() for token in raw_text.split(",") if token.strip()]
    if not tokens:
        raise ValueError("No handles provided")

    for token in tokens:
        if not token.startswith("@"):
            raise ValueError("Handle must start with @")

        handle = token[1:]
        if not TELEGRAM_HANDLE_PATTERN.fullmatch(handle):
            raise ValueError("Invalid Telegram handle")

        normalized = f"@{handle.lower()}"
        if normalized not in seen:
            seen.add(normalized)
            handles.append(normalized)

    return handles


def parse_invitee_input(raw_text: str) -> tuple[list[str], bool]:
    """Parse invitee input and support @all shortcut."""
    normalized = raw_text.strip().lower()
    if normalized == "@all":
        return ["@all"], True
    return parse_invitee_handles(raw_text), False


def build_event_type_markup() -> InlineKeyboardMarkup:
    """Build event type selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("Social", callback_data="event_type_social")],
        [InlineKeyboardButton("Sports", callback_data="event_type_sports")],
        [InlineKeyboardButton("Work", callback_data="event_type_work")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_duration_markup() -> InlineKeyboardMarkup:
    """Build duration selection keyboard."""
    keyboard = [
        [InlineKeyboardButton("30 min", callback_data="event_duration_30")],
        [InlineKeyboardButton("60 min", callback_data="event_duration_60")],
        [InlineKeyboardButton("90 min", callback_data="event_duration_90")],
        [InlineKeyboardButton("120 min", callback_data="event_duration_120")],
        [InlineKeyboardButton("180 min", callback_data="event_duration_180")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /organize_event command - start event creation flow."""
    await _start_event_flow(update, context, scheduling_mode="fixed")


async def handle_flexible(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /organize_event_flexible command - no initial date/time."""
    await _start_event_flow(update, context, scheduling_mode="flexible")


async def _start_event_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    scheduling_mode: str,
) -> None:
    """Initialize event creation flow for fixed or flexible scheduling."""
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

    if not settings.db_url:
        await update.message.reply_text(
            "❌ Database configuration is unavailable.")
        return

    async with get_session(settings.db_url) as session:
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
        "stage": "description",
        "group_id": group.group_id,
        "data": {"scheduling_mode": scheduling_mode},
    }

    await update.message.reply_text(
        "📝 *Event Description*\n\n"
        "Send a short description for the event.\n"
        f"Mode: {'Fixed date/time' if scheduling_mode == 'fixed' else 'Flexible (collect availability first)'}\n\n"
        "Example: Friendly football match at the central field.",
    )


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for event creation flow."""
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
    if not event_flow:
        await query.edit_message_text(
            "❌ Event setup session expired. Please run /organize_event again."
        )
        return
    flow_data = event_flow.get("data")
    if not isinstance(flow_data, dict):
        flow_data = {}
        event_flow["data"] = flow_data

    if data and data.startswith("event_type_"):
        event_type = data.replace("event_type_", "")
        scheduling_mode = str(flow_data.get("scheduling_mode", "fixed"))
        flow_data["event_type"] = event_type
        context.user_data["event_flow"] = event_flow
        if scheduling_mode == "flexible":
            event_flow["stage"] = "threshold"
            context.user_data["event_flow"] = event_flow
            await query.edit_message_text(
                f"📅 *Event Type: {event_type}*\n\n"
                "Flexible mode selected.\n"
                "No fixed date/time now. Attendees can add availability slots later with:\n"
                "/constraints <event_id> availability <YYYY-MM-DD HH:MM, ...>\n\n"
                "Set minimum attendance threshold:",
                reply_markup=build_threshold_markup(),
            )
        else:
            event_flow["stage"] = "date"
            context.user_data["event_flow"] = event_flow
            now = datetime.now()
            calendar_markup = build_calendar_markup(now.year, now.month)
            await query.edit_message_text(
                f"📅 *Event Type: {event_type}*\n\n"
                "Select a date from the inline calendar:",
                reply_markup=calendar_markup,
            )

    elif data and data.startswith("event_cal_"):
        await handle_calendar_callback(query, context, event_flow, flow_data)

    elif data and data.startswith("event_threshold_"):
        threshold = int(data.replace("event_threshold_", ""))
        event_flow["stage"] = "duration"
        flow_data["threshold_attendance"] = threshold
        context.user_data["event_flow"] = event_flow

        await query.edit_message_text(
            f"✅ *Threshold: {threshold}*\n\n"
            "Select event duration:",
            reply_markup=build_duration_markup(),
        )

    elif data and data.startswith("event_duration_"):
        duration = int(data.replace("event_duration_", ""))
        event_flow["stage"] = "invitees"
        flow_data["duration_minutes"] = duration
        context.user_data["event_flow"] = event_flow

        await query.edit_message_text(
            f"⏳ *Duration: {duration} minutes*\n\n"
            "Now enter invitee handles (comma-separated).\n"
            "Example: @alice, @bob_builder\n"
            "Or use: @all"
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

    if stage == "description":
        text = update.message.text
        if not text or not text.strip():
            await update.message.reply_text(
                "❌ Description cannot be empty. Please send a short description."
            )
            return
        description = text.strip()
        if len(description) > 500:
            await update.message.reply_text(
                "❌ Description is too long. Keep it under 500 characters."
            )
            return

        flow_data["description"] = description
        event_flow["stage"] = "type"
        context.user_data["event_flow"] = event_flow
        scheduling_mode = str(flow_data.get("scheduling_mode", "fixed"))

        await update.message.reply_text(
            "📋 *Event Type*\n\n"
            "What type of event would you like to organize?\n"
            f"Mode: {'Fixed date/time' if scheduling_mode == 'fixed' else 'Flexible (collect availability first)'}",
            reply_markup=build_event_type_markup(),
        )

    elif stage == "time":
        text = update.message.text
        if text is None:
            await update.message.reply_text(
                "❌ Please send time as text in format: HH:MM"
            )
            return

        scheduled_date = flow_data.get("scheduled_date")
        if not isinstance(scheduled_date, str):
            await update.message.reply_text(
                "❌ Event date is missing. Please reselect date from calendar."
            )
            return

        try:
            parsed_time = datetime.strptime(text.strip(), "%H:%M").time()
            parsed_date = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
            scheduled_time = datetime.combine(parsed_date, parsed_time)
            event_flow["stage"] = "threshold"
            flow_data["scheduled_time"] = scheduled_time.isoformat()
            context.user_data["event_flow"] = event_flow

            await update.message.reply_text(
                f"⏱️ *Time: {scheduled_time.strftime('%Y-%m-%d %H:%M')}*\n\n"
                "What is the minimum attendance threshold?",
                reply_markup=build_threshold_markup(),
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid time format. Please use: HH:MM"
            )

    elif stage == "invitees":
        text = update.message.text
        if text is None:
            await update.message.reply_text(
                "❌ Invalid input. Please enter comma-separated handles like @alice, @bob."
            )
            return

        try:
            invitees, invite_all = parse_invitee_input(text)
            event_flow["stage"] = "final"
            flow_data["invitees"] = invitees
            flow_data["invite_all_members"] = invite_all
            flow_data["creator"] = user_id
            context.user_data["event_flow"] = event_flow

            data = flow_data
            scheduled_time = str(data.get("scheduled_time", "N/A")).replace(
                "T", " "
            )
            invitees_summary = (
                "all group members"
                if invite_all else f"{len(invitees)} users"
            )
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
                f"Description: {data.get('description', 'N/A')}\n"
                f"Time: {scheduled_time}\n"
                f"Duration: {data.get('duration_minutes', 120)} minutes\n"
                f"Mode: {data.get('scheduling_mode', 'fixed')}\n"
                f"Threshold: {data.get('threshold_attendance', 'N/A')}\n"
                f"Invitees: {invitees_summary}\n\n"
                "Create this event?",
                reply_markup=reply_markup,
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid handle list. Use comma-separated @handles.\n"
                "Example: @alice, @bob_builder\n"
                "Or use: @all"
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
    scheduling_mode = str(data.get("scheduling_mode", "fixed"))
    if scheduling_mode != "flexible" and not isinstance(scheduled_time_raw, str):
        await query.edit_message_text("❌ Event time is missing.")
        return

    group_id = event_flow.get("group_id")
    if not isinstance(group_id, int):
        await query.edit_message_text("❌ Group context is missing.")
        return

    async with get_session(settings.db_url) as session:
        candidate_time = (
            datetime.fromisoformat(scheduled_time_raw)
            if isinstance(scheduled_time_raw, str)
            else None
        )
        duration_minutes = int(data.get("duration_minutes", 120))
        creator_id = int(data.get("creator", query.from_user.id))
        conflict = await find_user_event_conflict(
            session=session,
            telegram_user_id=creator_id,
            start_time=candidate_time,
            duration_minutes=duration_minutes,
        )
        if conflict:
            await query.edit_message_text(
                "❌ Creator has a conflicting event.\n"
                f"Conflicting Event ID: {conflict.event_id}\n"
                f"Time: {conflict.scheduled_time}\n"
                f"Duration: {conflict.duration_minutes or 120} minutes"
            )
            return

        event = Event(
            group_id=group_id,
            event_type=data.get("event_type", "general"),
            description=data.get("description"),
            scheduled_time=candidate_time,
            duration_minutes=duration_minutes,
            threshold_attendance=data.get("threshold_attendance", 5),
            attendance_list=[creator_id],
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
    bot_username = query.bot.username if query.bot else None
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
    reply_markup = InlineKeyboardMarkup(keyboard)
    scheduled_time = (
        str(data.get("scheduled_time", "TBD")).replace("T", " ")
        if data.get("scheduled_time")
        else "TBD (flexible scheduling)"
    )
    invitees_summary = (
        "all group members"
        if data.get("invite_all_members")
        else f"{len(data.get('invitees', []))} users"
    )

    await query.edit_message_text(
        f"✅ *Event Created!*\n\n"
        f"Event ID: {event.event_id}\n"
        f"Type: {data.get('event_type', 'N/A')}\n"
        f"Description: {data.get('description', 'N/A')}\n"
        f"Time: {scheduled_time}\n"
        f"Duration: {data.get('duration_minutes', 120)} minutes\n"
        f"Mode: {scheduling_mode}\n"
        f"Threshold: {data.get('threshold_attendance', 'N/A')}\n"
        f"Invitees: {invitees_summary}"
        + (
            "\n\nFlexible flow tip:\n"
            "Each attendee can add availability slots with:\n"
            f"/constraints {event.event_id} availability <YYYY-MM-DD HH:MM, ...>"
            if scheduling_mode == "flexible"
            else ""
        ),
        reply_markup=reply_markup,
    )


async def handle_calendar_callback(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    event_flow: dict[str, Any],
    flow_data: dict[str, Any],
) -> None:
    """Handle inline calendar callbacks for date selection."""
    data = query.data
    if not data:
        return

    if data == "event_cal_ignore":
        return

    if data.startswith("event_cal_nav_") or data.startswith("event_cal_open_"):
        parts = data.split("_")
        if len(parts) < 5:
            return
        try:
            year = int(parts[-2])
            month = int(parts[-1])
            if month < 1 or month > 12:
                return
        except ValueError:
            return

        event_type = str(flow_data.get("event_type", "N/A"))
        await query.edit_message_text(
            f"📅 *Event Type: {event_type}*\n\n"
            "Select a date from the inline calendar:",
            reply_markup=build_calendar_markup(year, month),
        )
        return

    if data.startswith("event_cal_day_"):
        parts = data.split("_")
        if len(parts) != 6:
            return
        try:
            year = int(parts[3])
            month = int(parts[4])
            day = int(parts[5])
            selected = datetime(year, month, day)
        except ValueError:
            return

        selected_date = selected.strftime("%Y-%m-%d")
        flow_data["scheduled_date"] = selected_date
        event_flow["stage"] = "time"
        context.user_data["event_flow"] = event_flow

        await query.edit_message_text(
            f"📆 *Date selected: {selected_date}*\n\n"
            "Now send the event time.\n"
            "Format: HH:MM (e.g., 18:00)\n\n"
            "If needed, change date:",
            reply_markup=InlineKeyboardMarkup(
                [[
                    InlineKeyboardButton(
                        "📅 Change Date",
                        callback_data=f"event_cal_open_{year}_{month}",
                    )
                ]]
            ),
        )
