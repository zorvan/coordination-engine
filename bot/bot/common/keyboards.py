"""Shared inline keyboard builders."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def build_threshold_markup(
    back_callback: str | None = None,
) -> InlineKeyboardMarkup:
    """Build compact threshold choices keyboard."""
    options = [
        ("2", "event_threshold_2"),
        ("3", "event_threshold_3"),
        ("5", "event_threshold_5"),
        ("8", "event_threshold_8"),
        ("13", "event_threshold_13"),
    ]
    keyboard: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for index, (label, callback_data) in enumerate(options):
        row.append(InlineKeyboardButton(label, callback_data=callback_data))
        if len(row) == 2 or index == len(options) - 1:
            keyboard.append(row)
            row = []
    if back_callback:
        keyboard.append(
            [InlineKeyboardButton("✏️ Edit Previous", callback_data=back_callback)]
        )
    return InlineKeyboardMarkup(keyboard)
