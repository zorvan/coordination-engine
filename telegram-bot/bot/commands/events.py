#!/usr/bin/env python3
"""Events command handler - list recent events with IDs."""
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from config.settings import settings
from db.connection import get_session
from db.models import Event, Group


async def handle(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /events command - list recent events and event IDs."""
    if not update.message or not update.effective_chat:
        return

    chat = update.effective_chat
    is_group_chat = chat.type in {"group", "supergroup"}
    db_url = settings.db_url or ""

    async with get_session(db_url) as session:
        query = (
            select(Event, Group)
            .join(Group, Event.group_id == Group.group_id, isouter=True)
            .order_by(Event.created_at.desc())
            .limit(20)
        )

        if is_group_chat:
            query = query.where(Group.telegram_group_id == chat.id)

        result = await session.execute(query)
        rows = result.all()

        if not rows:
            await update.message.reply_text("ℹ️ No events found.")

            return

        title = (
            f"📋 *Recent Events in {chat.title or 'this group'}*"
            if is_group_chat
            else "📋 *Recent Events*"
        )
        lines = [title, ""]

        for event, group in rows:
            group_name = (
                group.group_name
                if group and group.group_name
                else str(group.telegram_group_id) if group else "Unknown Group"
            )
            description = (event.description or "No description").strip()
            if len(description) > 80:
                description = f"{description[:77]}..."
            lines.append(
                f"• ID `{event.event_id}` | {event.event_type} | {event.state}"
            )
            lines.append(
                f"  Group: {group_name} | Time: {event.scheduled_time or 'TBD'} | "
                f"Duration: {event.duration_minutes or 120}m"
            )
            lines.append(f"  Description: {description}")

        await update.message.reply_text("\n".join(lines))

        return
