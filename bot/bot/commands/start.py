#!/usr/bin/env python3
"""Start command handler."""
from telegram import Update
from telegram.ext import ContextTypes


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /start command."""
    display_name = update.effective_user.full_name if update.effective_user else "User"
    
    await update.message.reply_text(
        f"👋 Hello, {display_name}!\n\n"
        "I'm your coordination bot. I help organize group events with AI-powered scheduling.\n\n"
        "Available commands:\n"
        "/organize_event - Create a new event\n"
        "/my_groups - List your groups\n"
        "/profile - View your profile\n"
        "/reputation - Check your reputation\n"
        "/help - Show this help message"
    )
