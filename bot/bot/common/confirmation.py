"""Confirmation invalidation helpers."""
from __future__ import annotations

from typing import Any

from bot.common.attendance import parse_attendance_with_status

def _extract_confirmed_telegram_ids(attendance_list: list[Any] | None) -> list[int]:
    """Extract committed/final-confirmed telegram user ids from attendance entries."""
    confirmed: list[int] = []
    for telegram_user_id, status in parse_attendance_with_status(attendance_list).items():
        if status in {"committed", "confirmed"}:
            confirmed.append(telegram_user_id)
    return confirmed


def _to_interested_attendance(attendance_list: list[Any] | None) -> list[str]:
    """Convert all attendance markers into interested stage."""
    return [
        f"{telegram_user_id}:interested"
        for telegram_user_id in sorted(parse_attendance_with_status(attendance_list).keys())
    ]


async def invalidate_confirmations_and_notify(
    *,
    context,
    event,
    reason: str,
) -> int:
    """Reset confirmations to interested state and notify previously confirmed users."""
    confirmed_ids = _extract_confirmed_telegram_ids(event.attendance_list)
    if not confirmed_ids:
        return 0

    event.attendance_list = _to_interested_attendance(event.attendance_list)
    event.state = "interested" if event.attendance_list else "proposed"

    message = (
        f"🔁 Event {event.event_id} changed before lock.\n"
        f"Reason: {reason}\n\n"
        "Your previous confirmation was reset. "
        f"Please reconfirm with /confirm {event.event_id}."
    )
    for telegram_user_id in confirmed_ids:
        try:
            await context.bot.send_message(chat_id=telegram_user_id, text=message)
        except Exception:
            # User may not have started bot or blocked DM.
            continue
    return len(confirmed_ids)
