#!/usr/bin/env python3
"""Profile command handler."""
from telegram import Update
from telegram.ext import ContextTypes


async def handle(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /profile command."""
    if not update.message:
        return

    await update.message.reply_text(
        "👤 *Your Profile*\n\n"
        "- No profile data yet.\n\n"
        "Profile information will appear after event participation."
    )
