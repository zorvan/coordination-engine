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
    start, my_groups, profile, reputation, organize_event,
    join, confirm, cancel, constraints, suggest_time, status,
    event_details, events,
)
from bot.handlers import event_flow, feedback, membership, mentions
from ai.llm import LLMClient


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log full traceback for uncaught update handling errors."""
    logger = logging.getLogger("coord_bot.bot")
    logger.exception("Unhandled Telegram update error. update=%r", 
                     update, 
                     exc_info=context.error)


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
    
    application = ApplicationBuilder().token(settings.telegram_token).build()

    # Capture rolling group history first for mention context.
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS, mentions.record_group_history),
        group=-2,
    )

    # Sync group users/members from any group activity before command handling.
    application.add_handler(
        MessageHandler(filters.ChatType.GROUPS, membership.track_group_members),
        group=-1,
    )

    # Mention-driven AI action inference in groups.
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & filters.ChatType.GROUPS,
            mentions.handle_mention,
        ),
        group=0,
    )

    # Register command handlers
    command_map = {
        "start": start.handle,
        "help": start.handle,
        "my_groups": my_groups.handle,
        "profile": profile.handle,
        "reputation": reputation.handle,
        "organize_event": organize_event.handle,
        "organize_event_flexible": organize_event.handle_flexible,
        "join": join.handle,
        "confirm": confirm.handle,
        "cancel": cancel.handle,
        "constraints": constraints.handle,
        "suggest_time": suggest_time.handle,
        "status": status.handle,
        "events": events.handle,
         "event_details": event_details.handle,
        "feedback": feedback.collect_feedback,
    }
    
    for command, handler in command_map.items():
        application.add_handler(CommandHandler(command, handler))

    # Register callback query handlers
    callback_handlers = [
        (r"^event_(type|threshold|duration|final|cancel|cal)_", organize_event.handle_callback),
        (r"^event_(join|confirm|cancel|lock)_", event_flow.handle_event_flow),
        (r"^event_(details|logs|constraints|close)_", event_details.handle_callback),
        (r"^constraint_nl_", constraints.handle_callback),
        (r"^mentionact_", mentions.handle_mention_callback),
        (r"^suggest_time_retry_", suggest_time.handle_callback),
        (r"^feedback_", feedback.handle_feedback_callback),
    ]
    
    for pattern, handler in callback_handlers:
        application.add_handler(CallbackQueryHandler(handler, pattern=pattern))

    # Register text message handler for event creation flow
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, organize_event.handle_message)
    )

    application.add_error_handler(on_error)
    
    logger.info("Bot started. Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    main()
