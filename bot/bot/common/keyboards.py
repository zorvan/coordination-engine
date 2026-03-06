"""Shared inline keyboard builders."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_threshold_markup() -> InlineKeyboardMarkup:
    """Build standard threshold choices keyboard."""
    keyboard = [
        [InlineKeyboardButton("2", callback_data="event_threshold_2")],
        [InlineKeyboardButton("3", callback_data="event_threshold_3")],
        [InlineKeyboardButton("5", callback_data="event_threshold_5")],
        [InlineKeyboardButton("8", callback_data="event_threshold_8")],
        [InlineKeyboardButton("13", callback_data="event_threshold_13")],
    ]
    return InlineKeyboardMarkup(keyboard)

