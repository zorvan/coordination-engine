#!/usr/bin/env python3
"""Deadline and auto-lock utilities."""
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import select

from config.settings import settings
from db.connection import get_session
from db.models import Event


async def check_and_lock_expired_events() -> list[dict]:
    """Check for events that have reached their deadline and auto-lock if threshold is met.
    
    Returns:
        List of dicts with event_id and status for each processed event
    """
    if not settings.db_url:
        return []

    results = []
    now = datetime.utcnow()

    async with get_session(settings.db_url) as session:
        events_to_check = (
            await session.execute(
                select(Event).where(
                    Event.state == "confirmed",
                    Event.commit_by.isnot(None),
                    Event.commit_by <= now,
                    Event.locked_at.is_(None),
                )
            )
        ).scalars().all()

        for event in events_to_check:
            try:
                event_id = int(event.event_id)
                result = await _try_auto_lock_event(session, event, now)
                results.append(result)
            except Exception as e:
                results.append({
                    "event_id": int(event.event_id) if event.event_id else 0,
                    "status": "error",
                    "message": str(e),
                })

    return results


async def _try_auto_lock_event(session, event, now: datetime) -> dict:
    """Try to auto-lock a single event.
    
    Returns:
        Dict with event_id, status, and message
    """
    try:
        from bot.common.attendance import parse_attendance

        participants, confirmed = parse_attendance(event.attendance_list or [])
        threshold = int(event.threshold_attendance or 0)
        current_confirmed = len(confirmed)

        if current_confirmed >= threshold:
            from bot.common.attendance import finalize_commitments

            event.state = "locked"
            event.attendance_list, _ = finalize_commitments(event.attendance_list)
            event.locked_at = now
            await session.flush()

            return {
                "event_id": int(event.event_id) if event.event_id else 0,
                "status": "locked",
                "message": f"Auto-locked event {event.event_id} after deadline reached with {current_confirmed}/{threshold} confirmed",
            }
        else:
            return {
                "event_id": int(event.event_id) if event.event_id else 0,
                "status": "not_locked",
                "message": f"Event {event.event_id} not locked: only {current_confirmed}/{threshold} confirmed",
            }
    except Exception as e:
        return {
            "event_id": int(event.event_id) if event.event_id else 0,
            "status": "error",
            "message": str(e),
        }


async def check_deadline_status(event_id: int) -> Optional[dict]:
    """Get deadline status for a specific event.
    
    Returns:
        Dict with deadline info or None if event not found
    """
    if not settings.db_url:
        return None

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(
                select(Event).where(Event.event_id == event_id)
            )
        ).scalar_one_or_none()

        if not event:
            return None

        now = datetime.utcnow()
        commit_by = event.commit_by
        state = str(event.state or "")
        locked_at = event.locked_at

        time_remaining = None
        deadline_reached = False
        is_locked = state == "locked"

        if commit_by:
            time_remaining = commit_by - now
            deadline_reached = time_remaining.total_seconds() <= 0

        return {
            "event_id": int(event.event_id) if event.event_id else 0,
            "state": state,
            "commit_by": commit_by.isoformat() if commit_by else None,
            "deadline_reached": deadline_reached,
            "time_remaining_seconds": int(time_remaining.total_seconds()) if time_remaining else None,
            "is_locked": is_locked,
            "locked_at": locked_at.isoformat() if locked_at else None,
        }