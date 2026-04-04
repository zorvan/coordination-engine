#!/usr/bin/env python3
"""Events command handler - list recent events as clickable buttons."""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select

from config.settings import settings
from db.connection import get_session
from db.models import Event, Group
from bot.common.rbac import check_group_membership


async def handle(update: Update, _context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /events command - list recent events as clickable buttons."""
    if not update.message or not update.effective_chat:
        return

    chat = update.effective_chat
    is_group_chat = chat.type in {"group", "supergroup"}
    db_url = settings.db_url or ""
    user_id = update.effective_user.id if update.effective_user else None

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

        # Filter events by group membership for group chats
        if is_group_chat and user_id:
            filtered_rows = []
            for event, group in rows:
                if group:
                    is_member, _ = await check_group_membership(
                        session, group.group_id, user_id,
                        telegram_chat_id=chat.id
                    )
                    if is_member:
                        filtered_rows.append((event, group))
                else:
                    # Events without group: skip in group chat
                    continue
            rows = filtered_rows

        if not rows:
            await update.message.reply_text(
                "ℹ️ No events found in this group.\n\n"
                "You may not be a member yet. Contact a group admin."
            )
            return

        title = (
            f"📋 *Recent Events in {chat.title or 'this group'}*"
            if is_group_chat
            else "📋 *Recent Events*"
        )

        # Build message text with brief event info
        lines = [title, ""]
        
        # Build keyboard with event buttons
        keyboard = []
        
        for event, group in rows:
            group_name = (
                group.group_name[:20]
                if group and group.group_name
                else "Private" if group else "Unknown"
            )
            time_str = event.scheduled_time.strftime("%m-%d %H:%M") if event.scheduled_time else "TBD"
            
            # Three-word description for button text
            words = (event.description or "Event").split()[:3]
            short_desc = " ".join(words)
            
            # Escape underscores for safe Markdown
            short_desc_escaped = short_desc.replace("_", "\\_")
            group_name_escaped = group_name.replace("_", "\\_")
            state_escaped = event.state.replace("_", "\\_")
            
            # Add brief info to message text
            lines.append(f"• ID `{event.event_id}` | {short_desc_escaped} | {time_str} | {state_escaped}")
            
            # Add button for this event
            keyboard.append([
                InlineKeyboardButton(
                    f"📅 {short_desc} (#{event.event_id})",
                    callback_data=f"menu_event_select_{event.event_id}"
                )
            ])
        
        # Add back to menu button
        keyboard.append([
            InlineKeyboardButton("🏠 Main Menu", callback_data="menu_main"),
        ])
        
        lines.append("")
        lines.append("💡 *Tap any event above to view details*")

        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown",
        )
