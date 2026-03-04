#!/usr/bin/env python3
"""My Groups command handler."""
from telegram import Update
from telegram.ext import ContextTypes


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /my_groups command."""
    await update.message.reply_text(
        "📋 *Your Groups*\n\n"
        "• No groups yet.\n\n"
        "Add me to a group to start coordinating events!"
    )
