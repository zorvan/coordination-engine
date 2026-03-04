#!/usr/bin/env python3
"""Nudges utility - soft friction messages for the coordination bot."""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def generate_nudge_message(event_id: int, user_id: int, event_type: str) -> str:
    """Generate appropriate nudge message based on context."""
    import random
    
    nudges = [
        f"❗️ {user_id} has cancelled event {event_id}. "
        f"Participation is needed for this {event_type} event.",
        
        f"⚠️ {user_id} stepped away from event {event_id}. "
        "Consider finding a replacement or adjusting plans.",
        
        f"🔔 {user_id} cancelled event {event_id}. "
        "The group may need more attendees to meet the threshold.",
        
        f"⚠️ {user_id} cancelled participation in event {event_id}. "
        "This could affect the event's feasibility.",
        
        f"❗️ {user_id} has left event {event_id}. "
        "Please check if others need to be invited.",
    ]
    
    return random.choice(nudges)


def generate_fallback_warning(event_id: int) -> str:
    """Generate fallback warning when AI is unavailable."""
    return (
        f"⚠️ Event {event_id}: AI scheduling unavailable. "
        "Using rules-based fallback scheduling."
    )


def generate_reliability_warning(user_id: int, reliability_score: float) -> str:
    """Generate reliability warning for users with low reliability."""
    if reliability_score < 0.3:
        return (
            f"⚠️ User {user_id} has low reliability ({reliability_score}). "
            "Consider this when inviting to time-critical events."
        )
    elif reliability_score < 0.5:
        return (
            f"ℹ️ User {user_id} has moderate reliability ({reliability_score}). "
            "Keep this in mind for important events."
        )
    return ""


def generate_deadline_warning(event_id: int, time_remaining: str) -> str:
    """Generate deadline warning for approaching events."""
    return (
        f"⏰ Event {event_id}: Deadline approaching!\n"
        f"Time remaining: {time_remaining}\n"
        "Make sure enough attendees have confirmed."
    )


def generate_lock_warning(event_id: int) -> str:
    """Generate warning when event is being locked."""
    return (
        f"🔒 Event {event_id} is being locked.\n"
        "No further changes to attendance will be allowed."
    )


def generate_threshold_warning(event_id: int, current: int, threshold: int) -> str:
    """Generate warning when attendance is below threshold."""
    return (
        f"⚠️ Event {event_id}: Attendance below threshold!\n"
        f"Current: {current} / Required: {threshold}\n"
        "More attendees needed to lock this event."
    )


def generate_compromise_suggestion(event_id: int, suggestions: list) -> str:
    """Generate compromise suggestion message."""
    msg = f"🔄 Event {event_id} - Suggested compromises:\n"
    for i, suggestion in enumerate(suggestions, 1):
        msg += f"{i}. {suggestion}\n"
    return msg


def get_inline_keyboard_for_event(event_id: int, event_state: str):
    """Get inline keyboard for event actions."""
    buttons = []
    
    if event_state == "proposed":
        buttons.append(InlineKeyboardButton("✅ Confirm", callback_data=f"event_confirm_{event_id}"))
        buttons.append(InlineKeyboardButton("❌ Cancel", callback_data=f"event_cancel_{event_id}"))
    elif event_state == "interested":
        buttons.append(InlineKeyboardButton("✅ Confirm", callback_data=f"event_confirm_{event_id}"))
    
    return InlineKeyboardMarkup([buttons])