"""Inline buttons utility for Telegram bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def make_inline_keyboard(buttons: list) -> InlineKeyboardMarkup:
    """Create inline keyboard markup from button list."""
    return InlineKeyboardMarkup([buttons])
