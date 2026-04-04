"""Clean Architecture command handlers for Telegram bot commands.

Each handler takes EventApplicationService + Telegram context,
executes the appropriate command/query, and formats the response.
"""

from __future__ import annotations

import logging
from telegram import Update
from telegram.ext import ContextTypes

from coordination_engine.application.dto import (
    ConfirmAttendanceCommand,
    CreateEventCommand,
    JoinEventCommand,
    ModifyEventCommand,
    Result,
    TransitionEventCommand,
)
from coordination_engine.application.services import EventApplicationService
from coordination_engine.infrastructure.llm_adapter import LLMServiceAdapter

logger = logging.getLogger("coord_engine.command_handlers")


# ---------------------------------------------------------------------------
# /join
# ---------------------------------------------------------------------------

async def handle_join_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    telegram_user_id: int,
) -> None:
    """Handle /join command via Clean Architecture."""
    result = await app_service.join_event(
        JoinEventCommand(
            event_id=event_id,
            telegram_user_id=telegram_user_id,
            source="slash",
        )
    )
    if result.success:
        await update.message.reply_text("✅ Joined the event!")
    else:
        await update.message.reply_text(f"❌ {result.errors[0]}")


# ---------------------------------------------------------------------------
# /confirm
# ---------------------------------------------------------------------------

async def handle_confirm_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    telegram_user_id: int,
) -> None:
    """Handle /confirm command via Clean Architecture."""
    result = await app_service.confirm_attendance(
        ConfirmAttendanceCommand(
            event_id=event_id,
            telegram_user_id=telegram_user_id,
        )
    )
    if result.success:
        await update.message.reply_text("✅ Confirmed! You're locked in.")
    else:
        await update.message.reply_text(f"❌ {result.errors[0]}")


# ---------------------------------------------------------------------------
# /lock
# ---------------------------------------------------------------------------

async def handle_lock_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    admin_telegram_id: int,
) -> None:
    """Handle /lock command via Clean Architecture."""
    result = await app_service.transition_event(
        TransitionEventCommand(
            event_id=event_id,
            target_state="locked",
            actor_telegram_user_id=admin_telegram_id,
            reason="Locked via /lock command",
            source="slash",
        )
    )
    if result.success:
        await update.message.reply_text(f"🔒 Event #{event_id} is now locked.")
    else:
        await update.message.reply_text(f"❌ {result.errors[0]}")


# ---------------------------------------------------------------------------
# /cancel
# ---------------------------------------------------------------------------

async def handle_cancel_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    actor_telegram_id: int,
    reason: str = "",
) -> None:
    """Handle event cancellation via Clean Architecture."""
    result = await app_service.transition_event(
        TransitionEventCommand(
            event_id=event_id,
            target_state="cancelled",
            actor_telegram_user_id=actor_telegram_id,
            reason=reason or "Cancelled by organizer",
            source="slash",
        )
    )
    if result.success:
        await update.message.reply_text(f"❌ Event #{event_id} has been cancelled.")
    else:
        await update.message.reply_text(f"❌ {result.errors[0]}")


# ---------------------------------------------------------------------------
# /modify_event
# ---------------------------------------------------------------------------

async def handle_modify_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    event_id: int,
    modifier_telegram_id: int,
    change_text: str,
    llm_service: LLMServiceAdapter | None = None,
) -> None:
    """Handle /modify_event command via Clean Architecture.

    If the user is not the admin, creates a modification request
    (pending approval). If admin, applies changes directly.
    """
    # Get current event
    event_result = await app_service.get_event(event_id)
    if not event_result.success:
        await update.message.reply_text(f"❌ {event_result.errors[0]}")
        return

    event_dto = event_result.data

    # For now, apply modification directly
    # In production: check admin status, create pending request if not admin
    # This is simplified — full implementation would use ModifyEventCommand
    # with LLM-parsed patch

    if llm_service:
        # Parse natural language change into structured patch
        current_draft = {
            "description": event_dto.description,
            "event_type": event_dto.event_type,
            "scheduled_time": event_dto.scheduled_time,
            "duration_minutes": event_dto.duration_minutes,
            "threshold_attendance": event_dto.threshold_attendance,
        }
        patch = await llm_service.infer_modification_patch(current_draft, change_text)

        result = await app_service.modify_event(
            ModifyEventCommand(
                event_id=event_id,
                modifier_telegram_id=modifier_telegram_id,
                description=patch.get("description"),
                event_type=patch.get("event_type"),
                scheduled_time=patch.get("scheduled_time_iso"),
                duration_minutes=patch.get("duration_minutes"),
                threshold_attendance=patch.get("threshold_attendance"),
            )
        )

        if result.success:
            changed = result.data.get("changed_fields", [])
            await update.message.reply_text(
                f"✅ Event #{event_id} updated.\n"
                f"Changed: {', '.join(changed)}"
            )
        else:
            await update.message.reply_text(f"❌ {result.errors[0]}")
    else:
        await update.message.reply_text(
            "⚠️ LLM service unavailable. Use the inline modify flow instead."
        )


# ---------------------------------------------------------------------------
# Create Event (simplified — full version uses FSM)
# ---------------------------------------------------------------------------

async def handle_create_event(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    app_service: EventApplicationService,
    cmd: CreateEventCommand,
) -> Result:
    """Create an event via Clean Architecture."""
    result = await app_service.create_event(cmd)
    if result.success:
        event = result.data
        await update.message.reply_text(
            f"🌱 Event #{event.event_id} created!\n"
            f"State: {event.state}\n"
            f"Description: {event.description[:200]}"
        )
    else:
        await update.message.reply_text(f"❌ {result.errors[0]}")
    return result
