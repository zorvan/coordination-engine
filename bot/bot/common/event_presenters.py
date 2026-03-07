"""Shared event presentation helpers."""
from typing import Any

from sqlalchemy import select

from bot.common.event_states import STATE_EXPLANATIONS
from bot.common.attendance import parse_attendance_with_status
from db.models import User
from db.connection import get_session
from config.settings import settings


def summarize_description(description: str | None, max_len: int = 400) -> str:
    """Normalize and truncate event description for messages."""
    text = (description or "No description provided").strip()
    if len(text) > max_len:
        return f"{text[:max_len - 3]}..."
    return text


async def attendance_stats_with_usernames(
    attendance: list[Any] | None, session
) -> tuple[int, int, str]:
    """Return interested count, confirmed count, and formatted attendee text with usernames."""
    status_by_user = parse_attendance_with_status(attendance)
    interested_count = sum(
        1 for status in status_by_user.values() if status == "interested"
    )
    committed_count = sum(
        1 for status in status_by_user.values() if status == "committed"
    )
    confirmed_count = sum(
        1 for status in status_by_user.values() if status == "confirmed"
    )

    if not status_by_user:
        return interested_count, confirmed_count, "No attendees yet."

    lines = []
    user_ids = list(status_by_user.keys())
    
    users = {}
    if user_ids:
        result = await session.execute(
            select(User).where(User.telegram_user_id.in_(user_ids))
        )
        for user in result.scalars().all():
            users[user.telegram_user_id] = user
    
    for telegram_user_id in sorted(status_by_user.keys()):
        status = status_by_user[telegram_user_id]
        user = users.get(telegram_user_id)
        username = user.username if user and getattr(user, "username", None) else None
        user_display = f"@{username}" if username else f"[user](tg://user?id={telegram_user_id})"
        icon = {
            "invited": "📨",
            "interested": "•",
            "committed": "⏳",
            "confirmed": "✓",
        }.get(status, "•")
        lines.append(f"{icon} {user_display} ({status})")
    if committed_count:
        lines.append(f"\nCommitted pending lock: {committed_count}")
    return interested_count, confirmed_count, "\n".join(lines)


def attendance_stats(attendance: list[Any] | None) -> tuple[int, int, str]:
    """Return interested count, confirmed count, and formatted attendee text."""
    status_by_user = parse_attendance_with_status(attendance)
    interested_count = sum(
        1 for status in status_by_user.values() if status == "interested"
    )
    committed_count = sum(
        1 for status in status_by_user.values() if status == "committed"
    )
    confirmed_count = sum(
        1 for status in status_by_user.values() if status == "confirmed"
    )

    if not status_by_user:
        return interested_count, confirmed_count, "No attendees yet."

    lines = []
    for telegram_user_id in sorted(status_by_user.keys()):
        status = status_by_user[telegram_user_id]
        icon = {
            "invited": "📨",
            "interested": "•",
            "committed": "⏳",
            "confirmed": "✓",
        }.get(status, "•")
        lines.append(f"{icon} {telegram_user_id} ({status})")
    if committed_count:
        lines.append(f"\nCommitted pending lock: {committed_count}")
    return interested_count, confirmed_count, "\n".join(lines)


async def format_event_details_message(
    event_id: int, event: Any, logs: list[Any], constraints: list[Any]
) -> str:
    """Build consistent detailed event info with early-stage progress."""
    attendance = event.attendance_list or []
    
    if settings.db_url:
        async with get_session(settings.db_url) as session:
            interested_count, confirmed_count, attendees_text = await attendance_stats_with_usernames(attendance, session)
    else:
        interested_count, confirmed_count, attendees_text = attendance_stats(attendance)
    threshold = event.threshold_attendance or 0
    needed = max(threshold - confirmed_count, 0)
    availability_count = sum(
        1 for c in constraints if str(getattr(c, "type", "")).startswith("available:")
    )
    planning_prefs = (
        event.planning_prefs
        if isinstance(getattr(event, "planning_prefs", None), dict)
        else {}
    )
    location_type = str(planning_prefs.get("location_type", "n/a")).replace("_", " ")
    budget_level = str(planning_prefs.get("budget_level", "n/a")).replace("_", " ")
    transport_mode = str(planning_prefs.get("transport_mode", "n/a")).replace("_", " ")
    time_window = str(planning_prefs.get("time_window", "n/a"))
    date_preset = str(planning_prefs.get("date_preset", "n/a"))

    next_step = "Run /join <event_id> to gather interest."
    if event.scheduled_time is None:
        next_step = (
            "No time selected yet. Collect availability via "
            f"/constraints {event_id} availability <YYYY-MM-DD HH:MM, ...> "
            f"then run /suggest_time {event_id}."
        )
    elif event.state == "interested":
        next_step = "Members should run /confirm <event_id>."
    elif event.state == "confirmed":
        next_step = "Organizer can lock the event when ready."
    elif event.state in {"locked", "completed", "cancelled"}:
        next_step = "Event is in a terminal/locked stage."

    admin_id = getattr(event, "admin_telegram_user_id", None)
    admin_text = "N/A"
    if admin_id and settings.db_url:
        try:
            async with get_session(settings.db_url) as session:
                admin_user = (
                    await session.execute(
                        select(User).where(User.telegram_user_id == int(admin_id))
                    )
                ).scalar_one_or_none()
                if admin_user and getattr(admin_user, "username", None):
                    admin_text = f"@{admin_user.username}"
                elif admin_id:
                    admin_text = f"[user](tg://user?id={admin_id})"
        except Exception:
            admin_text = str(admin_id)
    
    return (
        f"📋 *Event {event_id} Details*\n\n"
        f"Type: {event.event_type}\n"
        f"Description: {event.description or 'N/A'}\n"
        f"Time: {event.scheduled_time or 'TBD'}\n"
        f"Commit-By: {event.commit_by or 'N/A'}\n"
        f"Date Preset: {date_preset}\n"
        f"Time Window: {time_window}\n"
        f"Location Type: {location_type}\n"
        f"Budget: {budget_level}\n"
        f"Transport: {transport_mode}\n"
        f"Duration: {event.duration_minutes or 120} minutes\n"
        f"Threshold: {threshold}\n"
        f"State: {event.state}\n"
        f"State Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unknown state')}\n"
        f"AI Score: {event.ai_score:.2f}\n"
        f"Created: {event.created_at}\n"
        f"Locked: {event.locked_at or 'N/A'}\n"
        f"Completed: {event.completed_at or 'N/A'}\n\n"
        f"Admin: {admin_text}\n\n"
        f"Progress:\n"
        f"- Interested: {interested_count}\n"
        f"- Confirmed: {confirmed_count}\n"
        f"- Needed to reach threshold: {needed}\n"
        f"- Availability slots: {availability_count}\n\n"
        f"Attendees ({len(attendance)}):\n{attendees_text}\n\n"
        f"Logs: {len(logs)}\n"
        f"Constraints: {len(constraints)}\n\n"
        f"Next step: {next_step}"
    )


async def format_status_message(
    event_id: int, event: Any, log_count: int, constraint_count: int
) -> str:
    """Build consistent event status message."""
    description = summarize_description(event.description, max_len=400)
    planning_prefs = (
        event.planning_prefs
        if isinstance(getattr(event, "planning_prefs", None), dict)
        else {}
    )
    location_type = str(planning_prefs.get("location_type", "n/a")).replace("_", " ")
    budget_level = str(planning_prefs.get("budget_level", "n/a")).replace("_", " ")
    transport_mode = str(planning_prefs.get("transport_mode", "n/a")).replace("_", " ")
    time_window = str(planning_prefs.get("time_window", "n/a"))
    date_preset = str(planning_prefs.get("date_preset", "n/a"))
    admin_id = getattr(event, "admin_telegram_user_id", None)
    admin_text = "N/A"
    if admin_id and settings.db_url:
        try:
            async with get_session(settings.db_url) as session:
                admin_user = (
                    await session.execute(
                        select(User).where(User.telegram_user_id == int(admin_id))
                    )
                ).scalar_one_or_none()
                if admin_user and getattr(admin_user, "username", None):
                    admin_text = f"@{admin_user.username}"
                elif admin_id:
                    admin_text = f"[user](tg://user?id={admin_id})"
        except Exception:
            admin_text = str(admin_id)
    
    return (
        f"📊 *Event {event_id} Status*\n\n"
        f"Type: {event.event_type}\n"
        f"Description: {description}\n"
        f"Time: {event.scheduled_time}\n"
        f"Commit-By: {event.commit_by or 'N/A'}\n"
        f"Date Preset: {date_preset}\n"
        f"Time Window: {time_window}\n"
        f"Location Type: {location_type}\n"
        f"Budget: {budget_level}\n"
        f"Transport: {transport_mode}\n"
        f"Duration: {event.duration_minutes or 120} minutes\n"
        f"Threshold: {event.threshold_attendance}\n"
        f"State: {event.state}\n"
        f"State Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unknown state')}\n"
        f"AI Score: {event.ai_score:.2f}\n\n"
        f"Admin: {admin_text}\n\n"
        f"Attendees: {len(event.attendance_list)}\n"
        f"Logs: {log_count}\n"
        f"Constraints: {constraint_count}\n"
        f"Created: {event.created_at}"
    )
