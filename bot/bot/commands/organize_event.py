#!/usr/bin/env python3
"""Organize event command handler."""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters

from config.settings import settings
from db.connection import create_session, create_engine
from db.models import Event, Group


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /organize_event command - start event creation flow."""
    if not update.message or not update.effective_chat:
        return
    
    chat_id = update.effective_chat.id
    
    engine = create_engine(settings.db_url)
    Session = create_session(engine)
    
    async with Session() as session:
        result = await session.execute(
            Group.__table__.select().where(Group.telegram_group_id == chat_id)
        )
        group = result.scalar_one_or_none()
    
    if not group:
        await update.message.reply_text(
            "❌ This command can only be used in a group context."
        )
        return
    
    context.user_data["event_flow"] = {
        "stage": "type",
        "group_id": group.group_id,
        "data": {}
    }
    
    keyboard = [
        [InlineKeyboardButton("Social", callback_data="event_type_social")],
        [InlineKeyboardButton("Sports", callback_data="event_type_sports")],
        [InlineKeyboardButton("Work", callback_data="event_type_work")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "📋 *Event Type*\n\n"
        "What type of event would you like to organize?",
        reply_markup=reply_markup
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for event type selection."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    event_flow = context.user_data.get("event_flow", {})
    
    if data.startswith("event_type_"):
        event_type = data.replace("event_type_", "")
        event_flow["stage"] = "time"
        event_flow["data"]["event_type"] = event_type
        context.user_data["event_flow"] = event_flow
        
        await query.edit_message_text(
            f"📅 *Event Type: {event_type}*\n\n"
            "Now enter the scheduled time for the event.\n"
            "Format: YYYY-MM-DD HH:MM (e.g., 2026-03-15 18:00)"
        )
    
    elif data.startswith("event_threshold_"):
        threshold = int(data.replace("event_threshold_", ""))
        event_flow["stage"] = "invitees"
        event_flow["data"]["threshold_attendance"] = threshold
        context.user_data["event_flow"] = event_flow
        
        await query.edit_message_text(
            f"✅ *Threshold: {threshold}*\n\n"
            "Now enter the invitees (user IDs, comma-separated).\n"
            "Example: 123456789,987654321"
        )
    
    elif data.startswith("event_final_"):
        await finalize_event(query, context)
    
    elif data.startswith("event_cancel_"):
        context.user_data.pop("event_flow", None)
        await query.edit_message_text("❌ Event creation cancelled.")


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages during event creation flow."""
    event_flow = context.user_data.get("event_flow", {})
    
    if not event_flow:
        return
    
    stage = event_flow.get("stage")
    user_id = update.effective_user.id
    
    if stage == "time":
        try:
            scheduled_time = datetime.strptime(update.message.text.strip(), "%Y-%m-%d %H:%M")
            event_flow["stage"] = "threshold"
            event_flow["data"]["scheduled_time"] = scheduled_time.isoformat()
            context.user_data["event_flow"] = event_flow
            
            keyboard = [
                [InlineKeyboardButton("3", callback_data="event_threshold_3")],
                [InlineKeyboardButton("5", callback_data="event_threshold_5")],
                [InlineKeyboardButton("8", callback_data="event_threshold_8")],
                [InlineKeyboardButton("10", callback_data="event_threshold_10")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⏱️ *Time: {scheduled_time}*\n\n"
                "What is the minimum attendance threshold?",
                reply_markup=reply_markup
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid date format. Please use: YYYY-MM-DD HH:MM"
            )
    
    elif stage == "invitees":
        try:
            invitees = [int(x.strip()) for x in update.message.text.split(",") if x.strip()]
            event_flow["stage"] = "final"
            event_flow["data"]["invitees"] = invitees
            event_flow["data"]["creator"] = user_id
            context.user_data["event_flow"] = event_flow
            
            data = event_flow["data"]
            keyboard = [
                [InlineKeyboardButton("✅ Confirm", callback_data="event_final_yes")],
                [InlineKeyboardButton("❌ Cancel", callback_data="event_cancel_no")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"✨ *Event Summary*\n\n"
                f"Type: {data.get('event_type', 'N/A')}\n"
                f"Time: {data.get('scheduled_time', 'N/A')}\n"
                f"Threshold: {data.get('threshold_attendance', 'N/A')}\n"
                f"Invitees: {len(invitees)} users\n\n"
                "Create this event?",
                reply_markup=reply_markup
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid user IDs. Please enter comma-separated numeric IDs."
            )


async def finalize_event(query, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Finalize and create the event in database."""
    event_flow = context.user_data.get("event_flow", {})
    data = event_flow.get("data", {})
    
    engine = create_engine(settings.db_url)
    Session = create_session(engine)
    
    async with Session() as session:
        event = Event(
            group_id=data.get("group_id"),
            event_type=data.get("event_type", "general"),
            scheduled_time=datetime.fromisoformat(data.get("scheduled_time")),
            threshold_attendance=data.get("threshold_attendance", 5),
            attendance_list=[data.get("creator", query.from_user.id)],
            state="proposed",
        )
        session.add(event)
        await session.commit()
    
    context.user_data.pop("event_flow", None)
    
    keyboard = [
        [InlineKeyboardButton("View Event", callback_data=f"event_details_1")],
        [InlineKeyboardButton("Join", callback_data="event_join_1")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"✅ *Event Created!*\n\n"
        f"Type: {data.get('event_type', 'N/A')}\n"
        f"Time: {data.get('scheduled_time', 'N/A')}\n"
        f"Threshold: {data.get('threshold_attendance', 'N/A')}\n"
        f"Invitees: {len(data.get('invitees', []))} users",
        reply_markup=reply_markup
    )