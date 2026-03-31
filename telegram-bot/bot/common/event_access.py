"""Access helpers for event organizer/attendee checks."""
from __future__ import annotations

from typing import Any

from bot.common.attendance import parse_attendance


def attendance_telegram_ids(attendance_list: list[Any] | None) -> set[int]:
    """Return unique telegram user IDs from attendance markers."""
    participants, _ = parse_attendance(attendance_list)
    return participants


def get_event_organizer_telegram_id(event) -> int | None:
    """Resolve organizer ID from explicit field or fallback to first attendee."""
    organizer = getattr(event, "organizer_telegram_user_id", None)
    if organizer:
        return int(organizer)
    attendance = list(event.attendance_list or [])
    if not attendance:
        return None
    token = str(attendance[0]).split(":", 1)[0]
    if token.isdigit():
        return int(token)
    return None


def get_event_admin_telegram_id(event) -> int | None:
    """Resolve admin ID from explicit field or fallback to organizer."""
    admin = getattr(event, "admin_telegram_user_id", None)
    if admin:
        return int(admin)
    return get_event_organizer_telegram_id(event)


def is_attendee(event, telegram_user_id: int) -> bool:
    """Check whether user is in attendance markers."""
    return int(telegram_user_id) in attendance_telegram_ids(event.attendance_list)
