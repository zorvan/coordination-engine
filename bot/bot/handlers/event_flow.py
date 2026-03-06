#!/usr/bin/env python3
"""Event flow state machine handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select
from db.models import Event, Log
from db.connection import get_session
from db.users import get_or_create_user_id
from config.settings import settings
from bot.common.event_states import (
    EVENT_STATE_TRANSITIONS,
    STATE_EXPLANATIONS,
    can_transition,
)
from bot.common.scheduling import find_user_event_conflict
from datetime import datetime


def _derive_state_from_attendance(event: Event) -> str:
    """Derive non-terminal state from current attendance markers."""
    records = event.attendance_list or []
    if any(str(item).endswith(":confirmed") for item in records):
        return "confirmed"
    if records:
        return "interested"
    return "proposed"


async def handle_event_flow(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Main event flow handler - routes to state-specific handlers."""
    query = update.callback_query
    
    if not query or not query.data:
        return
    
    await query.answer()
    
    data = query.data
    
    if data.startswith("event_"):
        parts = data.split("_")
        if len(parts) >= 3:
            event_id = int(parts[-1])
            action = "_".join(parts[1:-1])
            
            if action == "join":
                await handle_join(query, context, event_id)
            elif action == "confirm":
                await handle_confirm(query, context, event_id)
            elif action == "cancel":
                await handle_cancel(query, context, event_id)
            elif action == "lock":
                await handle_lock(query, context, event_id)


async def handle_join(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle joining an event - transition to interested state."""
    telegram_user_id = query.from_user.id
    display_name = query.from_user.full_name
    username = query.from_user.username
    
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            
            return
        
        if event.state in ["locked", "completed", "cancelled"]:
            await query.edit_message_text(
                f"❌ Cannot join event {event_id}.\n"
                f"Current state: {event.state}\n"
                f"Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unavailable')}"
            )
            
            return

        conflict = await find_user_event_conflict(
            session=session,
            telegram_user_id=telegram_user_id,
            start_time=event.scheduled_time,
            duration_minutes=event.duration_minutes,
            ignore_event_id=event.event_id,
        )
        if conflict:
            await query.edit_message_text(
                "❌ You have a conflicting event.\n"
                f"Conflicting Event ID: {conflict.event_id}\n"
                f"Time: {conflict.scheduled_time}\n"
                f"Duration: {conflict.duration_minutes or 120} minutes"
            )
            return
        
        already_present = any(
            str(att) == str(telegram_user_id)
            or str(att).startswith(f"{telegram_user_id}:")
            for att in (event.attendance_list or [])
        )
        if not already_present:
            event.attendance_list.append(telegram_user_id)

        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )
        
        if event.state == "proposed":
            event.state = "interested"
        
        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="join",
            metadata_dict={"timestamp": datetime.utcnow().isoformat()}
        )
        session.add(log)
        await session.commit()
        
        keyboard = [
            [InlineKeyboardButton("✅ Confirm", callback_data=f"event_confirm_{event_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"event_cancel_{event_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Joined event {event_id}!*\n\n"
            f"State: {event.state}\n"
            f"Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unknown state')}\n"
            f"Use /confirm <event_id> to confirm attendance.",
            reply_markup=reply_markup
        )
        


async def handle_confirm(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle confirming attendance - transition from interested to confirmed."""
    telegram_user_id = query.from_user.id
    display_name = query.from_user.full_name
    username = query.from_user.username
    
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            
            return
        
        if event.state in ["locked", "completed", "cancelled"]:
            await query.edit_message_text(
                f"❌ Cannot confirm event {event_id}.\n"
                f"Current state: {event.state}\n"
                f"Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unavailable')}\n"
                "You can confirm only before the event is locked/completed/cancelled."
            )
            
            return

        conflict = await find_user_event_conflict(
            session=session,
            telegram_user_id=telegram_user_id,
            start_time=event.scheduled_time,
            duration_minutes=event.duration_minutes,
            ignore_event_id=event.event_id,
        )
        if conflict:
            await query.edit_message_text(
                "❌ You have a conflicting event.\n"
                f"Conflicting Event ID: {conflict.event_id}\n"
                f"Time: {conflict.scheduled_time}\n"
                f"Duration: {conflict.duration_minutes or 120} minutes"
            )
            return

        attendance = event.attendance_list or []
        has_joined = any(
            str(att) == str(telegram_user_id)
            or str(att).startswith(f"{telegram_user_id}:")
            for att in attendance
        )
        if not has_joined:
            event.attendance_list.append(telegram_user_id)
            attendance = event.attendance_list

        already_confirmed = any(
            str(att).startswith(f"{telegram_user_id}:confirmed")
            for att in attendance
        )
        if not already_confirmed:
            event.attendance_list = [
                e for e in attendance if str(e) != str(telegram_user_id)
            ]
            event.attendance_list.append(f"{telegram_user_id}:confirmed")
        event.state = "confirmed"

        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )
        
        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="confirm",
            metadata_dict={"timestamp": datetime.utcnow().isoformat()}
        )
        session.add(log)
        await session.commit()
        
        keyboard = [
            [InlineKeyboardButton("🔒 Lock Event", callback_data=f"event_lock_{event_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Confirmed attendance for event {event_id}!*\n\n"
            f"State: confirmed\n"
            f"Meaning: {STATE_EXPLANATIONS['confirmed']}\n"
            f"Use /lock to lock the event.",
            reply_markup=reply_markup
        )
        


async def handle_cancel(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle cancelling attendance for the clicking user."""
    telegram_user_id = query.from_user.id
    display_name = query.from_user.full_name
    username = query.from_user.username
    
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            
            return
        
        before = list(event.attendance_list or [])
        event.attendance_list = [
            e for e in before
            if str(e) != str(telegram_user_id)
            and not str(e).startswith(f"{telegram_user_id}:")
        ]
        if len(event.attendance_list) == len(before):
            await query.edit_message_text(
                f"❌ You haven't joined event {event_id} yet. Nothing to cancel."
            )
            return
        if event.state not in {"locked", "completed", "cancelled"}:
            event.state = _derive_state_from_attendance(event)

        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=telegram_user_id,
            display_name=display_name,
            username=username,
        )
        
        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="cancel",
            metadata_dict={"timestamp": datetime.utcnow().isoformat()}
        )
        session.add(log)
        await session.commit()
        
        await query.edit_message_text(
            f"❌ *Attendance cancelled for event {event_id}!*\n\n"
            f"State: {event.state}\n"
            f"Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unknown state')}"
        )
        


async def handle_lock(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle locking an event - transition from confirmed to locked."""
    user_id = query.from_user.id
    
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            
            return
        
        if event.state != "confirmed":
            await query.edit_message_text(
                f"❌ Cannot lock event {event_id}.\n"
                f"Current state: {event.state}\n"
                f"Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unavailable')}\n"
                "You can lock only when state is 'confirmed'."
            )
            
            return
        
        event.state = "locked"
        event.locked_at = datetime.utcnow()
        
        await session.commit()
        
        await query.edit_message_text(
            f"🔒 *Event {event_id} locked!*\n\n"
            f"State: locked\n"
            f"Meaning: {STATE_EXPLANATIONS['locked']}\n"
            f"Locked at: {event.locked_at}"
        )
        


async def show_event_details(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Show detailed event information."""
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            
            return
        
        await query.edit_message_text(
            f"📋 *Event {event_id}*\n\n"
            f"Type: {event.event_type}\n"
            f"Time: {event.scheduled_time}\n"
            f"State: {event.state}\n"
            f"Threshold: {event.threshold_attendance}\n"
            f"Attendees: {len(event.attendance_list)}"
        )
        
