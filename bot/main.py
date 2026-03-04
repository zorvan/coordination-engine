#!/usr/bin/env python3
"""Main entry point for the Telegram bot."""
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters

from config.settings import Settings
from config.logging import setup_logging


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log full traceback for uncaught update handling errors."""
    logger = logging.getLogger("coord_bot.bot")
    logger.exception("Unhandled Telegram update error. update=%r", 
                     update, 
                     exc_info=context.error)


async def log_telegram_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log every incoming Telegram command update."""
    logger = logging.getLogger("coord_bot.commands")

    message = update.effective_message
    user = update.effective_user
    chat = update.effective_chat
    text = message.text if message else None
    first_token = text.split()[0] if text else None

    logger.info(
        "Telegram command received command=%r user_id=%s username=%r chat_id=%s chat_type=%r text=%r",
        first_token,
        user.id if user else None,
        user.username if user else None,
        chat.id if chat else None,
        chat.type if chat else None,
        text,
    )


def main():
    """Main entry point."""
    settings = Settings()
    logger = setup_logging(settings)
    if not settings.telegram_token:
        raise ValueError("TELEGRAM_TOKEN is not set. Define it in environment or .env.")
    
    application = (
        ApplicationBuilder()
        .token(settings.telegram_token)
        .build()
    )
    application.add_handler(
        MessageHandler(filters.COMMAND, log_telegram_command),
        group=-1,
    )
    application.add_error_handler(on_error)
    
    logger.info("Bot started. Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()
