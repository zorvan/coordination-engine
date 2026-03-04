#!/usr/bin/env python3
"""Main entry point for the Telegram bot."""
import asyncio
from telegram.ext import ApplicationBuilder

from config.settings import settings
from config.logging import setup_logging


async def main():
    """Main entry point."""
    setup_logging()
    
    application = (
        ApplicationBuilder()
        .token(settings.telegram_token or "test_token")
        .build()
    )
    
    print("Bot started. Press Ctrl+C to stop.")
    application.run_polling()


if __name__ == "__main__":
    asyncio.run(main())