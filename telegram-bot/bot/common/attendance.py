"""Shared attendance/state transition helpers.

NOTE: This module handles the LEGACY attendance_list JSON column.
The current system uses the event_participants table with ParticipantStatus enum.
Legacy status 'committed' is mapped to 'confirmed' for consistency.
"""
from __future__ import annotations

from typing import Any

# Legacy statuses (for attendance_list JSON column)
# 'committed' is legacy - mapped to 'confirmed' in new system
ATTENDEE_STATUSES = ("invited", "interested", "confirmed")
ACTIVE_ATTENDEE_STATUSES = {"interested", "confirmed"}
PRE_LOCK_CONFIRMED_STATUSES = {"confirmed"}


def _normalize_attendee_status(raw_status: str | None) -> str | None:
    """Normalize and validate attendee status tokens."""
    if raw_status is None:
        return "interested"
    status = str(raw_status).strip().lower()
    # Map legacy 'committed' to 'confirmed'
    if status == "committed":
        status = "confirmed"
    if status in ATTENDEE_STATUSES:
        return status
    return None


def _parse_attendance_item(item: Any) -> tuple[int | None, str | None]:
    """Parse attendance item into (telegram_user_id, status)."""
    token = str(item).strip()
    if not token:
        return None, None

    if ":" not in token:
        if token.isdigit():
            return int(token), "interested"
        return None, None

    uid_raw, raw_status = token.split(":", 1)
    if not uid_raw.isdigit():
        return None, None
    status = _normalize_attendee_status(raw_status)
    if status is None:
        return None, None
    return int(uid_raw), status


def _serialize_attendee(telegram_user_id: int, status: str) -> str:
    """Serialize attendee to compact canonical marker."""
    return f"{telegram_user_id}:{status}"


def _attendance_to_status_map(attendance_list: list[Any] | None) -> dict[int, str]:
    """Parse attendance markers into a deduplicated status map by user ID."""
    status_by_user: dict[int, str] = {}
    for item in attendance_list or []:
        telegram_user_id, status = _parse_attendance_item(item)
        if telegram_user_id is None or status is None:
            continue
        status_by_user[telegram_user_id] = status
    return status_by_user


def _status_map_to_attendance(status_by_user: dict[int, str]) -> list[str]:
    """Convert status map into stable sorted attendance markers."""
    return [
        _serialize_attendee(telegram_user_id, status_by_user[telegram_user_id])
        for telegram_user_id in sorted(status_by_user.keys())
    ]


def derive_state_from_attendance(attendance_list: list[Any] | None) -> str:
    """Derive non-terminal state from attendance markers."""
    status_by_user = _attendance_to_status_map(attendance_list)
    statuses = set(status_by_user.values())
    if statuses & PRE_LOCK_CONFIRMED_STATUSES:
        return "confirmed"
    if statuses & ACTIVE_ATTENDEE_STATUSES:
        return "interested"
    return "proposed"


def has_attendee(attendance_list: list[Any] | None, telegram_user_id: int) -> bool:
    """Check whether user exists in attendance markers."""
    return int(telegram_user_id) in _attendance_to_status_map(attendance_list)


def has_confirmed(attendance_list: list[Any] | None, telegram_user_id: int) -> bool:
    """Check whether user has confirmed marker."""
    status = _attendance_to_status_map(attendance_list).get(int(telegram_user_id))
    return status in PRE_LOCK_CONFIRMED_STATUSES


def mark_joined(attendance_list: list[Any] | None, telegram_user_id: int) -> tuple[list[Any], bool]:
    """Ensure user is joined; return (new_attendance, changed)."""
    status_by_user = _attendance_to_status_map(attendance_list)
    telegram_user_id = int(telegram_user_id)
    current = status_by_user.get(telegram_user_id)
    if current in {"interested", "confirmed"}:
        return _status_map_to_attendance(status_by_user), False
    status_by_user[telegram_user_id] = "interested"
    return _status_map_to_attendance(status_by_user), True


def mark_confirmed(attendance_list: list[Any] | None, telegram_user_id: int) -> tuple[list[Any], bool]:
    """Ensure user is confirmed; return (new_attendance, changed)."""
    status_by_user = _attendance_to_status_map(attendance_list)
    telegram_user_id = int(telegram_user_id)
    current = status_by_user.get(telegram_user_id)
    if current in PRE_LOCK_CONFIRMED_STATUSES:
        return _status_map_to_attendance(status_by_user), False
    status_by_user[telegram_user_id] = "confirmed"
    return _status_map_to_attendance(status_by_user), True


def finalize_commitments(attendance_list: list[Any] | None) -> tuple[list[Any], bool]:
    """Promote interested/joined attendees to confirmed on lock."""
    status_by_user = _attendance_to_status_map(attendance_list)
    changed = False
    for telegram_user_id, status in list(status_by_user.items()):
        if status == "interested":
            status_by_user[telegram_user_id] = "confirmed"
            changed = True
    return _status_map_to_attendance(status_by_user), changed


def revert_confirmed_to_joined(
    attendance_list: list[Any] | None,
    telegram_user_id: int,
) -> tuple[list[Any], bool]:
    """Revert confirmed marker to interested."""
    status_by_user = _attendance_to_status_map(attendance_list)
    telegram_user_id = int(telegram_user_id)
    current = status_by_user.get(telegram_user_id)
    if current not in PRE_LOCK_CONFIRMED_STATUSES:
        return _status_map_to_attendance(status_by_user), False
    status_by_user[telegram_user_id] = "interested"
    return _status_map_to_attendance(status_by_user), True


def remove_attendee(attendance_list: list[Any] | None, telegram_user_id: int) -> tuple[list[Any], bool]:
    """Remove all attendance markers for user."""
    status_by_user = _attendance_to_status_map(attendance_list)
    telegram_user_id = int(telegram_user_id)
    if telegram_user_id not in status_by_user:
        return _status_map_to_attendance(status_by_user), False
    del status_by_user[telegram_user_id]
    return _status_map_to_attendance(status_by_user), True


def parse_attendance(attendance_list: list[Any] | None) -> tuple[set[int], set[int]]:
    """Return participant ids and confirmed participant ids."""
    status_by_user = _attendance_to_status_map(attendance_list)
    participants = set(status_by_user.keys())
    confirmed = {
        telegram_user_id
        for telegram_user_id, status in status_by_user.items()
        if status in PRE_LOCK_CONFIRMED_STATUSES
    }
    return participants, confirmed


def parse_attendance_with_status(attendance_list: list[Any] | None) -> dict[int, str]:
    """Return normalized attendee status map keyed by telegram user id."""
    return _attendance_to_status_map(attendance_list)
