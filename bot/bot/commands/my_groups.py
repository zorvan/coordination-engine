#!/usr/bin/env python3
"""My Groups command handler."""
from telegram import Update
from telegram.ext import ContextTypes


async def handle(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /my_groups command."""
    if not update.message:
        return

    await update.message.reply_text(
        "📋 *Your Groups*\n\n"
        "• No groups yet.\n\n"
        "Add me to a group to start coordinating events!"
    )
