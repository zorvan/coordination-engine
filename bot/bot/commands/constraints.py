#!/usr/bin/env python3
"""View/add/remove constraints command handler."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from db.models import Event, Constraint, User
from db.connection import get_session
from config.settings import settings


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /constraints command - manage constraints."""
    if not update.message or not update.effective_chat:
        return
    
    user_id = update.effective_user.id
    event_id = context.args[0] if context.args else None
    
    if not event_id:
        await update.message.reply_text(
            "Usage: /constraints <event_id> [view|add|remove]\n\n"
            "Examples:\n"
            "/constraints 123 view\n"
            "/constraints 123 add 456 if_joins\n"
            "/constraints 123 remove 1"
        )
        return
    
    try:
        event_id = int(event_id)
        action = context.args[1] if len(context.args) > 1 else "view"
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return
    
    if action == "view":
        await view_constraints(update, event_id)
    elif action == "add":
        await add_constraint(update, event_id, context)
    elif action == "remove":
        await remove_constraint(update, event_id, context)
    else:
        await update.message.reply_text(
            "❌ Unknown action. Use: view, add, or remove"
        )


async def view_constraints(update: Update, event_id: int) -> None:
    """View constraints for an event."""
    async for session in get_session(settings.db_url):
        result = await session.execute(
            Constraint.__table__.select().where(Constraint.event_id == event_id)
        )
        constraints = result.scalars().all()
        
        if not constraints:
            await update.message.reply_text(
                f"ℹ️ Event {event_id} has no constraints yet."
            )
            await session.close()
            return
        
        msg = f"📋 *Constraints for Event {event_id}*\n\n"
        for c in constraints:
            if c.target_user_id:
                msg += f"- User {c.user_id}: 'Join if User {c.target_user_id} joins' (confidence: {c.confidence})\n"
            else:
                msg += f"- User {c.user_id}: {c.type}\n"
        
        await update.message.reply_text(msg)
        await session.close()


async def add_constraint(update: Update, event_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add a constraint to an event."""
    if len(context.args) < 4:
        await update.message.reply_text(
            "Usage: /constraints <event_id> add <target_user_id> <constraint_type>\n"
            "Example: /constraints 123 add 456 if_joins"
        )
        return
    
    try:
        target_user_id = int(context.args[2])
        constraint_type = context.args[3]
    except ValueError:
        await update.message.reply_text("❌ User ID must be a number.")
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
        
        constraint = Constraint(
            user_id=update.effective_user.id,
            target_user_id=target_user_id,
            event_id=event_id,
            type=constraint_type,
            confidence=0.8
        )
        session.add(constraint)
        await session.commit()
        
        await update.message.reply_text(
            f"✅ Constraint added to event {event_id}!\n\n"
            f"Type: {constraint_type}\n"
            f"Target: User {target_user_id}"
        )
        await session.close()


async def remove_constraint(update: Update, event_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Remove a constraint from an event."""
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /constraints <event_id> remove <constraint_id>\n"
            "Example: /constraints 123 remove 1"
        )
        return
    
    try:
        constraint_id = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ Constraint ID must be a number.")
        return
    
    async for session in get_session(settings.db_url):
        result = await session.execute(
            Constraint.__table__.delete().where(
                Constraint.constraint_id == constraint_id,
                Constraint.event_id == event_id
            )
        )
        await session.commit()
        
        if result.rowcount > 0:
            await update.message.reply_text(
                f"✅ Constraint {constraint_id} removed from event {event_id}."
            )
        else:
            await update.message.reply_text(
                f"❌ Constraint {constraint_id} not found for event {event_id}."
            )
        await session.close()