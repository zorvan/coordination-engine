#!/usr/bin/env python3
"""Reputation command handler."""
from telegram import Update
from telegram.ext import ContextTypes


async def handle(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /reputation command."""
    if not update.message:
        return

    await update.message.reply_text(
        "⭐ *Your Reputation*\n\n"
        "- No reputation data yet.\n\n"
        "Reputation updates after event participation."
    )
