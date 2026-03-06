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
    STATE_EXPLANATIONS,
)
from bot.common.scheduling import find_user_event_conflict
from bot.common.attendance import (
    derive_state_from_attendance,
    finalize_commitments,
    mark_confirmed,
    mark_joined,
    remove_attendee,
    revert_confirmed_to_joined,
)
from datetime import datetime


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
            elif action == "back":
                await handle_back(query, context, event_id)
            elif action == "cancel":
                await handle_cancel(query, context, event_id)
            elif action == "lock":
                await handle_lock(query, context, event_id)


async def handle_join(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle joining an event - transition to interested state."""
    del context
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
        
        new_attendance, changed = mark_joined(
            event.attendance_list,
            telegram_user_id,
        )
        if changed:
            event.attendance_list = new_attendance

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
            [InlineKeyboardButton("✅ Commit", callback_data=f"event_confirm_{event_id}")],
            [InlineKeyboardButton("❌ Cancel", callback_data=f"event_cancel_{event_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Joined event {event_id}!*\n\n"
            f"State: {event.state}\n"
            f"Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unknown state')}\n"
            f"Use /confirm <event_id> to commit attendance.",
            reply_markup=reply_markup
        )
        


async def handle_confirm(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle commit action - move participant to committed stage."""
    del context
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

        new_attendance, _ = mark_confirmed(
            event.attendance_list,
            telegram_user_id,
        )
        event.attendance_list = new_attendance
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
            [InlineKeyboardButton("↩️ Back", callback_data=f"event_back_{event_id}")],
            [InlineKeyboardButton("🔒 Lock Event", callback_data=f"event_lock_{event_id}")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ *Committed to event {event_id}!*\n\n"
            f"State: confirmed\n"
            f"Meaning: {STATE_EXPLANATIONS['confirmed']}\n"
            f"Use /back to revert commitment or /lock to lock the event.",
            reply_markup=reply_markup
        )


async def handle_back(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Revert personal confirmation to interested before lock."""
    del context
    telegram_user_id = query.from_user.id
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        event = (
            await session.execute(select(Event).where(Event.event_id == event_id))
        ).scalar_one_or_none()
        if not event:
            await query.edit_message_text("❌ Event not found.")
            return
        if event.state == "locked":
            await query.edit_message_text("❌ Event is locked. Cannot go back.")
            return

        attendance, had_confirmed = revert_confirmed_to_joined(
            event.attendance_list,
            telegram_user_id,
        )
        if not had_confirmed:
            await query.edit_message_text(
                "ℹ️ You are not confirmed in this event."
            )
            return

        event.attendance_list = attendance
        event.state = derive_state_from_attendance(attendance)
        await session.commit()

    await query.edit_message_text(
        f"↩️ Confirmation reverted for event {event_id}.\n"
        f"State: {event.state}\n"
        "You are now in interested state."
    )
        


async def handle_cancel(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle cancelling attendance for the clicking user."""
    del context
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
        
        attendance, changed = remove_attendee(
            event.attendance_list,
            telegram_user_id,
        )
        if not changed:
            await query.edit_message_text(
                f"❌ You haven't joined event {event_id} yet. Nothing to cancel."
            )
            return
        event.attendance_list = attendance
        if event.state not in {"locked", "completed", "cancelled"}:
            event.state = derive_state_from_attendance(attendance)

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
    del context
    
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
        event.attendance_list, _ = finalize_commitments(event.attendance_list)
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
    del context
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
        
