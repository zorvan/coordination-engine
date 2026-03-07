#!/usr/bin/env python3
"""Modify existing event command handler."""
from __future__ import annotations

from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select

from ai.llm import LLMClient
from bot.common.confirmation import invalidate_confirmations_and_notify
from bot.common.event_access import (
    get_event_organizer_telegram_id,
    get_event_admin_telegram_id,
)
from bot.common.event_notifications import send_event_modification_request_dm
from config.settings import settings
from db.connection import get_session
from db.models import Event
import uuid


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
        admin_id = get_event_admin_telegram_id(event)
        requester_id = int(update.effective_user.id)
        if admin_id is not None and requester_id != admin_id:
            await _submit_modify_request(
                update=update,
                context=context,
                event=event,
                requester_id=requester_id,
                change_text=change_text,
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


async def _submit_modify_request(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    event,
    requester_id: int,
    change_text: str,
) -> None:
    """Submit a modify request when non-admin user requests changes."""
    admin_id = get_event_admin_telegram_id(event)
    if admin_id is None:
        await update.message.reply_text(
            "❌ Could not identify event admin to approve modification request."
        )
        return
    
    request_id = uuid.uuid4().hex[:8]
    pending_key = f"modify_request_{request_id}"
    context.bot_data.setdefault("pending_modify_requests", {})[pending_key] = {
        "event_id": event.event_id,
        "requester_id": requester_id,
        "requester_username": update.effective_user.username or update.effective_user.full_name,
        "change_text": change_text,
        "admin_id": admin_id,
        "created_at": datetime.utcnow().isoformat(),
    }
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"modreq_{request_id}_approve"),
            InlineKeyboardButton("❌ Reject", callback_data=f"modreq_{request_id}_reject"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"📩 *Modify request submitted for admin approval*\n\n"
        f"Event ID: {event.event_id}\n"
        f"Requested by: @{update.effective_user.username or update.effective_user.full_name}\n"
        f"Changes: {change_text}\n\n"
        f"Waiting for admin approval...",
        reply_markup=reply_markup,
    )
    
    adminDM_sent = await send_event_modification_request_dm(
        context=context,
        telegram_user_id=admin_id,
        event_data={
            "description": event.description or "",
            "event_type": event.event_type,
            "scheduled_time": (
                event.scheduled_time.isoformat(timespec="minutes")
                if event.scheduled_time else None
            ),
            "duration_minutes": int(event.duration_minutes or 120),
            "threshold_attendance": int(event.threshold_attendance or 0),
        },
        event_id=int(event.event_id),
        deadline_info="Please review and approve the modification request",
    )
    
    if not adminDM_sent:
        await update.message.reply_text(
            "⚠️ Could not send DM to admin. Please check your privacy settings."
        )


async def handle_modify_request_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle modify request approval/rejection callbacks."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()
    
    data = query.data
    if not data.startswith("modreq_"):
        return
    
    parts = data.split("_")
    if len(parts) != 3:
        return
    
    request_id = parts[1]
    decision = parts[2]
    
    pending_root = context.bot_data.get("pending_modify_requests", {})
    pending = pending_root.get(f"modreq_{request_id}")
    
    if not pending:
        await query.edit_message_text("⚠️ This modify request has expired.")
        return
    
    admin_id = pending.get("admin_id")
    requester_id = pending.get("requester_id")
    event_id = pending.get("event_id")
    change_text = pending.get("change_text")
    
    if query.from_user.id != admin_id:
        await query.answer("Only the event admin can approve/reject this request.", show_alert=True)
        return
    
    pending_root.pop(f"modreq_{request_id}", None)
    
    if decision == "reject":
        await query.edit_message_text(
            f"❌ Modify request for event {event_id} was rejected by admin."
        )
        return
    
    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(select(Event).where(Event.event_id == event_id))
        ).scalar_one_or_none()
        if not event:
            await query.edit_message_text("❌ Event not found.")
            return
        if event.state in {"locked", "completed", "cancelled"}:
            await query.edit_message_text(
                f"❌ Event {event_id} is {event.state}; modification is no longer possible."
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
            await query.edit_message_text(
                "⚠️ No valid event change inferred from your approval."
            )
            return
        
        reconfirm_needed = await invalidate_confirmations_and_notify(
            context=context,
            event=event,
            reason=", ".join(reason_parts) or "event details changed",
        )
        await session.commit()
    
    await query.edit_message_text(
        f"✅ Modify request approved.\n"
        f"Event {event_id} updated.\n"
        f"Changed fields: {', '.join(changed_fields)}\n"
        f"Confirmations reset: {reconfirm_needed}"
    )
    
    await context.bot.send_message(
        chat_id=requester_id,
        text=f"✅ Your modify request for event {event_id} was approved by admin."
    )
