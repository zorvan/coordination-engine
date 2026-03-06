"""Shared event presentation helpers."""
from typing import Any

from bot.common.event_states import STATE_EXPLANATIONS


def summarize_description(description: str | None, max_len: int = 400) -> str:
    """Normalize and truncate event description for messages."""
    text = (description or "No description provided").strip()
    if len(text) > max_len:
        return f"{text[:max_len - 3]}..."
    return text


def attendance_stats(attendance: list[Any] | None) -> tuple[int, int, str]:
    """Return interested count, confirmed count, and formatted attendee text."""
    records = attendance or []
    confirmed_count = sum(
        1 for item in records if str(item).endswith(":confirmed")
    )
    interested_count = len(records) - confirmed_count

    if not records:
        return interested_count, confirmed_count, "No attendees yet."

    lines = []
    for item in records:
        text = str(item)
        if text.endswith(":confirmed"):
            lines.append(f"✓ {text.replace(':confirmed', '')}")
        else:
            lines.append(f"- {text}")
    return interested_count, confirmed_count, "\n".join(lines)


def format_event_details_message(
    event_id: int, event: Any, logs: list[Any], constraints: list[Any]
) -> str:
    """Build consistent detailed event info with early-stage progress."""
    attendance = event.attendance_list or []
    interested_count, confirmed_count, attendees_text = attendance_stats(attendance)
    threshold = event.threshold_attendance or 0
    needed = max(threshold - confirmed_count, 0)
    availability_count = sum(
        1 for c in constraints if str(getattr(c, "type", "")).startswith("available:")
    )

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

    return (
        f"📋 *Event {event_id} Details*\n\n"
        f"Type: {event.event_type}\n"
        f"Description: {event.description or 'N/A'}\n"
        f"Time: {event.scheduled_time or 'TBD'}\n"
        f"Duration: {event.duration_minutes or 120} minutes\n"
        f"Threshold: {threshold}\n"
        f"State: {event.state}\n"
        f"State Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unknown state')}\n"
        f"AI Score: {event.ai_score:.2f}\n"
        f"Created: {event.created_at}\n"
        f"Locked: {event.locked_at or 'N/A'}\n"
        f"Completed: {event.completed_at or 'N/A'}\n\n"
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


def format_status_message(
    event_id: int, event: Any, log_count: int, constraint_count: int
) -> str:
    """Build consistent event status message."""
    description = summarize_description(event.description, max_len=400)
    return (
        f"📊 *Event {event_id} Status*\n\n"
        f"Type: {event.event_type}\n"
        f"Description: {description}\n"
        f"Time: {event.scheduled_time}\n"
        f"Duration: {event.duration_minutes or 120} minutes\n"
        f"Threshold: {event.threshold_attendance}\n"
        f"State: {event.state}\n"
        f"State Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unknown state')}\n"
        f"AI Score: {event.ai_score:.2f}\n\n"
        f"Attendees: {len(event.attendance_list)}\n"
        f"Logs: {log_count}\n"
        f"Constraints: {constraint_count}\n"
        f"Created: {event.created_at}"
    )
