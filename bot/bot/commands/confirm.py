#!/usr/bin/env python3
"""Confirm event command handler."""
from telegram import Update
from telegram.ext import ContextTypes
from db.models import Event, Log
from db.connection import get_session
from config.settings import settings
from datetime import datetime


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /confirm command - confirm attendance intent."""
    if not update.message:
        return
    
    user_id = update.effective_user.id
    event_id = context.args[0] if context.args else None
    
    if not event_id:
        await update.message.reply_text(
            "Usage: /confirm <event_id>\n\n"
            "Example: /confirm 123"
        )
        return
    
    try:
        event_id = int(event_id)
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return
    
    async for session in get_session(settings.db_url):
        result = await session.execute(
            Event.__table__.select().where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await update.message.reply_text("❌ Event not found.")
            await session.close()
            return
        
        if event.state == "locked":
            await update.message.reply_text(
                f"❌ Cannot confirm event {event_id} - it's already locked."
            )
            await session.close()
            return
        
        if user_id not in event.attendance_list:
            await update.message.reply_text(
                f"❌ You haven't joined event {event_id} yet. Use /join first."
            )
            await session.close()
            return
        
        if "confirmed" not in event.attendance_list:
            event.attendance_list = [e for e in event.attendance_list if e != user_id]
            event.attendance_list.append(f"{user_id}:confirmed")
            
            log = Log(
                event_id=event_id,
                user_id=user_id,
                action="confirmed",
                metadata_dict={"timestamp": datetime.utcnow().isoformat()}
            )
            session.add(log)
            await session.commit()
        
        await update.message.reply_text(
            f"✅ *Confirmed attendance for event {event_id}!*\n\n"
            f"Type: {event.event_type}\n"
            f"Time: {event.scheduled_time}\n"
            f"State: {event.state}"
        )
        await session.close()


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for confirm buttons."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("event_confirm_"):
        event_id = int(data.replace("event_confirm_", ""))
        context.args = [str(event_id)]
        await handle(query, context)
        await query.edit_message_text(
            f"✅ *Confirmed attendance for event {event_id}!*\n\n"
            f"Use /status {event_id} to view event progress."
        )