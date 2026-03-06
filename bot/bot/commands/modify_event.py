#!/usr/bin/env python3
"""Modify existing event command handler."""
from __future__ import annotations

from datetime import datetime

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from ai.llm import LLMClient
from bot.common.confirmation import invalidate_confirmations_and_notify
from bot.common.event_access import get_event_organizer_telegram_id
from config.settings import settings
from db.connection import get_session
from db.models import Event


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /modify_event <event_id> <free text patch>."""
    if not update.message or not update.effective_user:
        return
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /modify_event <event_id> <changes>\n\n"
            "Example: /modify_event 12 change time to 2026-03-08 18:30 and threshold to 5"
        )
        return
    try:
        event_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return
    change_text = " ".join(args[1:]).strip()
    if not change_text:
        await update.message.reply_text("❌ Change text cannot be empty.")
        return

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(select(Event).where(Event.event_id == event_id))
        ).scalar_one_or_none()
        if not event:
            await update.message.reply_text("❌ Event not found.")
            return
        if event.state in {"locked", "completed", "cancelled"}:
            await update.message.reply_text(
                f"❌ Event {event_id} is {event.state}; modification is not allowed."
            )
            return
        organizer_id = get_event_organizer_telegram_id(event)
        requester_id = int(update.effective_user.id)
        if organizer_id is not None and requester_id != organizer_id:
            await update.message.reply_text(
                f"❌ Only the event organizer can modify event {event_id}."
            )
            return

        draft = {
            "description": event.description or "",
            "event_type": event.event_type,
            "scheduled_time": (
                event.scheduled_time.isoformat(timespec="minutes")
                if event.scheduled_time else None
            ),
            "duration_minutes": int(event.duration_minutes or 120),
            "threshold_attendance": int(event.threshold_attendance or 0),
            "scheduling_mode": "fixed" if event.scheduled_time else "flexible",
        }
        llm = LLMClient()
        try:
            patch = await llm.infer_event_draft_patch(draft, change_text)
        finally:
            await llm.close()

        changed_fields: list[str] = []
        reason_parts: list[str] = []

        description = patch.get("description")
        if isinstance(description, str) and description.strip():
            next_description = description.strip()[:500]
            if next_description != (event.description or ""):
                event.description = next_description
                changed_fields.append("description")
                reason_parts.append("description changed")

        event_type = patch.get("event_type")
        if isinstance(event_type, str):
            normalized = event_type.strip().lower()
            if normalized in {"social", "sports", "work"} and normalized != event.event_type:
                event.event_type = normalized
                changed_fields.append("event_type")
                reason_parts.append("event type changed")

        threshold = patch.get("threshold_attendance")
        if threshold is not None:
            try:
                value = int(threshold)
                if value >= 1 and value != int(event.threshold_attendance or 0):
                    event.threshold_attendance = value
                    changed_fields.append("threshold_attendance")
                    reason_parts.append("threshold changed")
            except (TypeError, ValueError):
                pass

        duration = patch.get("duration_minutes")
        if duration is not None:
            try:
                value = int(duration)
                if 1 <= value <= 720 and value != int(event.duration_minutes or 120):
                    event.duration_minutes = value
                    changed_fields.append("duration_minutes")
                    reason_parts.append("duration changed")
            except (TypeError, ValueError):
                pass

        if bool(patch.get("clear_time")) and event.scheduled_time is not None:
            event.scheduled_time = None
            changed_fields.append("scheduled_time")
            reason_parts.append("time cleared")

        scheduled_time_iso = patch.get("scheduled_time_iso")
        if scheduled_time_iso is not None:
            try:
                parsed = datetime.fromisoformat(str(scheduled_time_iso).strip())
                if event.scheduled_time != parsed:
                    event.scheduled_time = parsed
                    changed_fields.append("scheduled_time")
                    reason_parts.append("time changed")
            except ValueError:
                pass

        if not changed_fields:
            await update.message.reply_text(
                "⚠️ No valid event change inferred from your message."
            )
            return

        reconfirm_needed = await invalidate_confirmations_and_notify(
            context=context,
            event=event,
            reason=", ".join(reason_parts) or "event details changed",
        )
        await session.commit()

    await update.message.reply_text(
        "✅ Event updated.\n"
        f"Changed fields: {', '.join(changed_fields)}\n"
        f"Confirmations reset: {reconfirm_needed}"
    )
