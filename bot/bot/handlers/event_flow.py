#!/usr/bin/env python3
"""Event flow state machine handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.models import Event, Log
from db.connection import get_session
from config.settings import settings
from datetime import datetime


class EventFlowStateMachine:
    """State machine for event lifecycle: proposed → interested → confirmed → locked → completed."""
    
    def __init__(self):
        self.states = {
            "proposed": ["interested", "cancelled"],
            "interested": ["confirmed", "cancelled"],
            "confirmed": ["locked", "cancelled"],
            "locked": ["completed", "cancelled"],
            "cancelled": [],
            "completed": [],
        }
    
    def can_transition(self, current_state: str, target_state: str) -> bool:
        """Check if transition is valid."""
        return target_state in self.states.get(current_state, [])
    
    def get_available_transitions(self, current_state: str) -> list:
        """Get list of available transitions."""
        return self.states.get(current_state, [])


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
    user_id = query.from_user.id
    
    db_url = settings.db_url or ""
    async for session in get_session(db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            await session.close()
            return
        
        if event.state not in ["proposed", "interested"]:
            await query.edit_message_text(
                f"❌ Cannot join event {event_id} - it's already {event.state}."
            )
            await session.close()
            return
        
        if user_id not in event.attendance_list:
            event.attendance_list.append(user_id)
        
        event.state = "interested"
        
        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="joined",
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
            f"State: interested\n"
            f"Use /confirm <event_id> to confirm attendance.",
            reply_markup=reply_markup
        )
        await session.close()


async def handle_confirm(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle confirming attendance - transition from interested to confirmed."""
    user_id = query.from_user.id
    
    db_url = settings.db_url or ""
    async for session in get_session(db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            await session.close()
            return
        
        if event.state != "interested":
            await query.edit_message_text(
                f"❌ Cannot confirm event {event_id} - it's {event.state}."
            )
            await session.close()
            return
        
        event.attendance_list = [e for e in event.attendance_list if e != user_id]
        event.attendance_list.append(f"{user_id}:confirmed")
        event.state = "confirmed"
        
        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="confirmed",
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
            f"Use /lock to lock the event.",
            reply_markup=reply_markup
        )
        await session.close()


async def handle_cancel(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle cancelling attendance - transitions to cancelled state."""
    user_id = query.from_user.id
    
    db_url = settings.db_url or ""
    async for session in get_session(db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            await session.close()
            return
        
        event.attendance_list = [
            e for e in event.attendance_list 
            if str(e) != str(user_id) and not str(e).startswith(f"{user_id}:")
        ]
        event.state = "cancelled"
        
        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="cancelled",
            metadata_dict={"timestamp": datetime.utcnow().isoformat()}
        )
        session.add(log)
        await session.commit()
        
        await query.edit_message_text(
            f"❌ *Attendance cancelled for event {event_id}!*\n\n"
            f"State: cancelled"
        )
        await session.close()


async def handle_lock(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Handle locking an event - transition from confirmed to locked."""
    user_id = query.from_user.id
    
    db_url = settings.db_url or ""
    async for session in get_session(db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            await session.close()
            return
        
        if event.state != "confirmed":
            await query.edit_message_text(
                f"❌ Cannot lock event {event_id} - it's {event.state}."
            )
            await session.close()
            return
        
        event.state = "locked"
        event.locked_at = datetime.utcnow()
        
        log = Log(
            event_id=event_id,
            user_id=user_id,
            action="locked",
            metadata_dict={"timestamp": datetime.utcnow().isoformat()}
        )
        session.add(log)
        await session.commit()
        
        await query.edit_message_text(
            f"🔒 *Event {event_id} locked!*\n\n"
            f"State: locked\n"
            f"Locked at: {event.locked_at}"
        )
        await session.close()


async def show_event_details(query, context: ContextTypes.DEFAULT_TYPE, event_id: int) -> None:
    """Show detailed event information."""
    db_url = settings.db_url or ""
    async for session in get_session(db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await query.edit_message_text("❌ Event not found.")
            await session.close()
            return
        
        await query.edit_message_text(
            f"📋 *Event {event_id}*\n\n"
            f"Type: {event.event_type}\n"
            f"Time: {event.scheduled_time}\n"
            f"State: {event.state}\n"
            f"Threshold: {event.threshold_attendance}\n"
            f"Attendees: {len(event.attendance_list)}"
        )
        await session.close()