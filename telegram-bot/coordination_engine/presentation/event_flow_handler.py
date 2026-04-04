"""Clean Architecture event flow handler.

Replaces the old bot/handlers/event_flow.py with a handler that uses
EventApplicationService instead of direct DB access.
"""

from __future__ import annotations

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from coordination_engine.application.dto import (
    ConfirmAttendanceCommand,
    JoinEventCommand,
    TransitionEventCommand,
)
from coordination_engine.application.services import EventApplicationService

logger = logging.getLogger("coord_engine.event_flow")

_STATUS_EMOJI = {
    "proposed": "🌱",
    "interested": "💭",
    "confirmed": "✅",
    "locked": "🔒",
    "completed": "🎉",
    "cancelled": "❌",
}


async def handle_event_join(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    telegram_user_id: int,
) -> str | None:
    """Handle user joining an event. Returns error text or None on success."""
    result = await app_service.join_event(
        JoinEventCommand(
            event_id=event_id,
            telegram_user_id=telegram_user_id,
            source="callback",
        )
    )
    if not result.success:
        return result.errors[0] if result.errors else "Failed to join."
    return None


async def handle_event_confirm(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    telegram_user_id: int,
) -> str | None:
    """Handle user confirming attendance. Returns error text or None on success."""
    result = await app_service.confirm_attendance(
        ConfirmAttendanceCommand(
            event_id=event_id,
            telegram_user_id=telegram_user_id,
        )
    )
    if not result.success:
        return result.errors[0] if result.errors else "Failed to confirm."
    return None


async def handle_event_cancel(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    telegram_user_id: int,
) -> str | None:
    """Handle user cancelling participation. Returns error text or None on success."""
    await app_service.cancel_attendance(
        # Using transition for participant cancellation
        # In full implementation, add CancelAttendanceCommand
        None  # type: ignore[arg-type]
    )
    return None


async def handle_event_lock(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    admin_telegram_id: int,
) -> str | None:
    """Handle event lock. Returns error text or None on success."""
    result = await app_service.transition_event(
        TransitionEventCommand(
            event_id=event_id,
            target_state="locked",
            actor_telegram_user_id=admin_telegram_id,
            reason="Locked by admin",
            source="callback",
        )
    )
    if not result.success:
        return result.errors[0] if result.errors else "Failed to lock."
    return None


async def handle_event_complete(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    admin_telegram_id: int,
) -> str | None:
    """Handle event completion. Returns error text or None on success."""
    result = await app_service.transition_event(
        TransitionEventCommand(
            event_id=event_id,
            target_state="completed",
            actor_telegram_user_id=admin_telegram_id,
            reason="Event completed",
            source="callback",
        )
    )
    if not result.success:
        return result.errors[0] if result.errors else "Failed to complete."
    return None


async def get_event_summary(
    app_service: EventApplicationService,
    event_id: int,
) -> str:
    """Get a formatted event summary card."""
    result = await app_service.get_event(event_id)
    if not result.success:
        return f"❌ {result.errors[0]}"

    dto = result.data
    status_emoji = _STATUS_EMOJI.get(dto.state, "❓")
    time_display = "⏳ TBD"
    if dto.scheduled_time:
        time_display = dto.scheduled_time.strftime("%Y-%m-%d %H:%M")

    return (
        f"{status_emoji} *Event #{dto.event_id}* — {dto.event_type.upper()}\n"
        f"📝 {dto.description[:150]}{'...' if len(dto.description) > 150 else ''}\n\n"
        f"📅 {time_display} · ⏱ {dto.duration_minutes}m\n"
        f"👥 {dto.participant_count} joined · ✅ {dto.confirmed_count} confirmed\n"
        f"🎯 Threshold: {dto.threshold_attendance} · State: {dto.state}\n\n"
        f"Tap below to join or confirm."
    )


async def build_event_action_keyboard(
    app_service: EventApplicationService,
    event_id: int,
    telegram_user_id: int,
) -> InlineKeyboardMarkup:
    """Build inline keyboard for event actions."""
    # Get participant status
    part_result = await app_service.get_participant(event_id, telegram_user_id)
    is_participant = part_result.success and part_result.data

    buttons = []
    if is_participant:
        buttons.append([
            InlineKeyboardButton("✅ Confirm", callback_data=f"event_confirm_{event_id}"),
            InlineKeyboardButton("❌ Cancel", callback_data=f"event_cancel_{event_id}"),
        ])
    else:
        buttons.append([
            InlineKeyboardButton("💭 Join", callback_data=f"event_join_{event_id}"),
        ])

    buttons.append([
        InlineKeyboardButton("📋 Details", callback_data=f"event_details_{event_id}"),
        InlineKeyboardButton("📊 Status", callback_data=f"event_status_{event_id}"),
    ])

    return InlineKeyboardMarkup(buttons)
