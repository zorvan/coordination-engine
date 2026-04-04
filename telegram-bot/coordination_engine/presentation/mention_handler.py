"""Clean Architecture mention handler.

Replaces the monolithic bot/handlers/mentions.py with a service-based
handler that uses ILLMService and EventApplicationService.
"""

from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from coordination_engine.application.dto import (
    AddConstraintCommand,
    CreateEventCommand,
)
from coordination_engine.application.ports import ILLMService
from coordination_engine.application.services import EventApplicationService
from coordination_engine.infrastructure.persistence import SQLAlchemyEventStore

logger = logging.getLogger("coord_engine.mention_handler")

HISTORY_LIMIT = 40
MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_]{5,32})")


class MentionHandler:
    """Handles @bot mentions using LLM inference and application services."""

    def __init__(
        self,
        app_service: EventApplicationService,
        llm_service: ILLMService,
        event_store: SQLAlchemyEventStore,
    ) -> None:
        self._app = app_service
        self._llm = llm_service
        self._store = event_store

    async def handle(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_text: str,
        chat_id: int,
        user_id: int,
        username: str | None,
        history: list[dict[str, Any]] | None = None,
    ) -> None:
        """Process a bot mention and dispatch to the appropriate action."""
        # Step 1: Infer intent via LLM
        inference = await self._llm.infer_mention_action(
            text=message_text,
            history=history,
        )

        action_type = inference.get("action_type", "opinion")
        event_id = inference.get("event_id")
        target_username = inference.get("target_username")
        constraint_type = inference.get("constraint_type")

        logger.debug(
            "Mention inference: action=%s, event_id=%s, user=%s",
            action_type,
            event_id,
            user_id,
        )

        # Step 2: Dispatch to appropriate handler
        if action_type in {"organize_event", "organize_event_flexible"}:
            await self._handle_organize(
                update, context, message_text, chat_id, user_id,
                scheduling_mode=action_type,
                history=history,
            )
            return

        if action_type == "opinion":
            await self._handle_opinion(
                update, context, message_text, chat_id, user_id,
                response=inference.get("assistant_response", ""),
            )
            return

        if action_type == "constraint_add" and target_username and constraint_type:
            await self._handle_constraint(
                update, context, chat_id, user_id, event_id,
                target_username=target_username,
                constraint_type=constraint_type,
            )
            return

        if action_type in {"join", "confirm", "cancel", "lock"} and event_id:
            await self._handle_event_action(
                update, context, action_type, event_id, user_id,
            )
            return

        if action_type == "status":
            await self._handle_status(update, context, event_id, chat_id)
            return

        if action_type == "event_details" and event_id:
            await self._handle_details(update, context, event_id)
            return

        # Fallback
        response = inference.get("assistant_response", "")
        if response:
            await update.message.reply_text(f"🤖 {response}")
        else:
            await self._handle_opinion(update, context, message_text, chat_id, user_id)

    async def _handle_organize(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_text: str,
        chat_id: int,
        user_id: int,
        scheduling_mode: str,
        history: list[dict[str, Any]] | None = None,
    ) -> None:
        """Create an event from LLM-inferred draft."""
        draft = await self._llm.infer_event_draft(
            message_text=message_text,
            history=history,
            scheduling_mode=scheduling_mode,
        )

        description = draft.get("description", message_text or "Group planned event")
        if isinstance(description, str) and description.strip():
            description = description.strip()[:500]
        else:
            # Not enough info — start interactive flow
            await update.message.reply_text(
                "🗓 I'd love to help organize! What would you like to plan?\n\n"
                "Tell me about the event and I'll set it up for you."
            )
            return

        # Save inferred constraints
        inferred_constraints = draft.get("inferred_constraints", [])

        result = await self._app.create_event(
            CreateEventCommand(
                group_telegram_id=chat_id,
                organizer_telegram_id=user_id,
                event_type=draft.get("event_type", "social"),
                description=description,
                scheduled_time=_parse_iso(draft.get("scheduled_time")),
                duration_minutes=draft.get("duration_minutes", 120),
                threshold_attendance=draft.get("threshold_attendance", 3),
                scheduling_mode=scheduling_mode,
                planning_prefs={
                    k: v for k, v in {
                        "location_type": draft.get("location_type"),
                        "budget_level": draft.get("budget_level"),
                        "transport_mode": draft.get("transport_mode"),
                        "date_preset": draft.get("date_preset"),
                        "time_window": draft.get("time_window"),
                    }.items()
                    if v is not None
                },
            )
        )

        if result.success:
            event = result.data
            await update.message.reply_text(
                f"🌱 *Event #{event.event_id} created!*\n\n"
                f"{description[:200]}\n\n"
                f"📅 {event.scheduled_time or 'TBD'} · ⏱ {event.duration_minutes}m\n"
                f"🎯 Threshold: {event.threshold_attendance}\n\n"
                f"Tap below to respond.",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("✅ Join", callback_data=f"event_join_{event.event_id}")],
                    [InlineKeyboardButton("📋 Details", callback_data=f"event_details_{event.event_id}")],
                ]),
                parse_mode="Markdown",
            )

            # Persist inferred constraints
            if isinstance(inferred_constraints, list):
                for ic in inferred_constraints:
                    if not isinstance(ic, dict):
                        continue
                    ctype = str(ic.get("constraint_type", "")).strip().lower()
                    target = str(ic.get("target_username", "")).strip()
                    if ctype in {"if_joins", "if_attends", "unless_joins"} and target:
                        await self._app.add_constraint(
                            AddConstraintCommand(
                                event_id=event.event_id,
                                user_telegram_id=user_id,
                                target_username=target,
                                constraint_type=ctype,
                                confidence=0.6,
                            )
                        )
        else:
            await update.message.reply_text(f"❌ {result.errors[0]}")

    async def _handle_opinion(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        message_text: str,
        chat_id: int,
        user_id: int,
        response: str = "",
    ) -> None:
        """Handle opinion/general mention."""
        if not response:
            response = (
                "I'm here to help coordinate events! "
                "Mention me with a request like "
                "'let's organize a game night' or 'join the board game event'."
            )

        # Check if user might be trying to organize
        lowered = message_text.lower()
        wants_event = any(
            kw in lowered
            for kw in ("let's", "let us", "we should", "how about", "organize", "meet")
        )

        if wants_event:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("🗓 Create event from this", callback_data="mention_start_organize")],
                [InlineKeyboardButton("📋 See current events", callback_data="mention_show_status")],
            ])
            await update.message.reply_text(
                f"🤖 {response}\n\n"
                "_Want me to turn this into an event, or see what's already planned?_",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(f"🤖 {response}")

    async def _handle_constraint(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        user_id: int,
        event_id: int | None,
        target_username: str,
        constraint_type: str,
    ) -> None:
        """Handle constraint addition."""
        if not event_id:
            # Need to find active event
            result = await self._app.get_events_for_group(chat_id)
            if result.success and result.data:
                event_id = result.data[0].event_id
            else:
                await update.message.reply_text(
                    "❌ No active events found. Which event should I add this constraint to?"
                )
                return

        if not event_id:
            await update.message.reply_text("❌ Could not find event.")
            return

        result = await self._app.add_constraint(
            AddConstraintCommand(
                event_id=event_id,
                user_telegram_id=user_id,
                target_username=target_username,
                constraint_type=constraint_type,
            )
        )

        if result.success:
            await update.message.reply_text(
                f"✅ Constraint saved for event #{event_id}.\n"
                f"Type: {constraint_type} → {target_username}"
            )
        else:
            await update.message.reply_text(f"❌ {result.errors[0]}")

    async def _handle_event_action(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        action_type: str,
        event_id: int,
        user_id: int,
    ) -> None:
        """Handle join/confirm/cancel/lock via mention."""
        # Delegate to command handlers
        from coordination_engine.presentation.command_handlers import (
            handle_join_command,
            handle_confirm_command,
            handle_lock_command,
        )

        if action_type == "join":
            await handle_join_command(
                update, context, self._app, event_id, user_id
            )
        elif action_type == "confirm":
            await handle_confirm_command(
                update, context, self._app, event_id, user_id
            )
        elif action_type == "lock":
            await handle_lock_command(
                update, context, self._app, event_id, user_id
            )
        elif action_type == "cancel":
            # For participant cancellation
            await update.message.reply_text(
                "To cancel your participation, use the inline Cancel button on the event."
            )

    async def _handle_status(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        event_id: int | None,
        chat_id: int,
    ) -> None:
        """Show event status."""
        from coordination_engine.presentation.presenters import (
            format_event_card,
            format_event_list,
        )
        if event_id:
            result = await self._app.get_event(event_id)
            if result.success:
                text = format_event_card(result.data)
                await update.message.reply_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text(f"❌ {result.errors[0]}")
        else:
            # Show all active events for group
            result = await self._app.get_events_for_group(chat_id)
            if result.success and result.data:
                text = format_event_list(result.data, "Active Events")
                await update.message.reply_text(text, parse_mode="Markdown")
            else:
                await update.message.reply_text("📋 No active events in this group.")

    async def _handle_details(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        event_id: int,
    ) -> None:
        """Show event details."""
        from coordination_engine.presentation.presenters import format_event_details
        result = await self._app.get_event(event_id)
        if result.success:
            text = format_event_details(result.data)
            await update.message.reply_text(text, parse_mode="Markdown")
        else:
            await update.message.reply_text(f"❌ {result.errors[0]}")


def _parse_iso(value: Any) -> datetime | None:
    """Parse ISO datetime string safely."""
    if not value or not isinstance(value, str):
        return None
    try:
        return datetime.fromisoformat(value.strip())
    except (ValueError, TypeError):
        return None
