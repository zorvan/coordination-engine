#!/usr/bin/env python3
"""Main entry point for the Telegram bot."""
import asyncio
import logging
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from config.settings import Settings
from config.logging import setup_logging
from bot.commands import (
    start,
    my_groups,
    profile,
    reputation,
    organize_event,
    join,
    confirm,
    cancel,
    constraints,
    suggest_time,
    status,
    event_details,
    events,
)
from bot.handlers import event_flow, feedback
from ai.llm import LLMClient


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


async def check_llm_availability(logger: logging.Logger) -> None:
    """Check LLM availability on startup and log status."""
    llm = LLMClient()
    try:
        is_available, message = await llm.check_availability()
        if is_available:
            logger.info("Startup LLM check: %s", message)
        else:
            logger.warning("Startup LLM check: %s", message)
    finally:
        await llm.close()


def main():
    """Main entry point."""
    settings = Settings()
    logger = setup_logging(settings)
    if not settings.telegram_token:
        raise ValueError("TELEGRAM_TOKEN is not set. Define it in environment or .env.")

    asyncio.run(check_llm_availability(logger))
    
    application = (
        ApplicationBuilder()
        .token(settings.telegram_token)
        .build()
    )

    # Command logging runs before all regular command handlers.
    application.add_handler(
        MessageHandler(filters.COMMAND, log_telegram_command),
        group=-1,
    )

    # Commands
    application.add_handler(CommandHandler("start", start.handle))
    application.add_handler(CommandHandler("help", start.handle))
    application.add_handler(CommandHandler("my_groups", my_groups.handle))
    application.add_handler(CommandHandler("mygroups", my_groups.handle))
    application.add_handler(CommandHandler("profile", profile.handle))
    application.add_handler(CommandHandler("reputation", reputation.handle))
    application.add_handler(CommandHandler("organize_event", organize_event.handle))
    application.add_handler(CommandHandler("join", join.handle))
    application.add_handler(CommandHandler("confirm", confirm.handle))
    application.add_handler(CommandHandler("cancel", cancel.handle))
    application.add_handler(CommandHandler("constraints", constraints.handle))
    application.add_handler(CommandHandler("suggest_time", suggest_time.handle))
    application.add_handler(CommandHandler("status", status.handle))
    application.add_handler(CommandHandler("events", events.handle))
    application.add_handler(CommandHandler("event_details", event_details.handle))
    application.add_handler(CommandHandler("feedback", feedback.collect_feedback))

    # Callback queries
    application.add_handler(
        CallbackQueryHandler(organize_event.handle_callback, pattern=r"^event_(type|threshold|final|cancel)_")
    )
    application.add_handler(
        CallbackQueryHandler(event_flow.handle_event_flow, pattern=r"^event_(join|confirm|cancel|lock)_")
    )
    application.add_handler(
        CallbackQueryHandler(event_details.handle_callback, pattern=r"^event_(logs|constraints|close)_")
    )
    application.add_handler(
        CallbackQueryHandler(suggest_time.handle_callback, pattern=r"^suggest_time_retry_")
    )
    application.add_handler(
        CallbackQueryHandler(feedback.handle_feedback_callback, pattern=r"^feedback_")
    )

    # Non-command messages used by the event creation flow.
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, organize_event.handle_message)
    )

    application.add_error_handler(on_error)
    
    logger.info("Bot started. Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()
