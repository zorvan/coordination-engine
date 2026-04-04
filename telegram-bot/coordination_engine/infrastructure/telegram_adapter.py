"""Telegram messaging adapter — implements IMessageService and INotificationService."""

from __future__ import annotations

import logging
from typing import Any

from telegram.ext import ContextTypes

from coordination_engine.application.ports import (
    IMessageService,
    INotificationService,
)

logger = logging.getLogger("coord_engine.telegram_adapter")


class TelegramMessageService(IMessageService):
    """Adapter around python-telegram-bot ContextTypes.DEFAULT_TYPE."""

    def __init__(self, context: ContextTypes.DEFAULT_TYPE) -> None:
        self._context = context

    async def send_to_user(
        self,
        telegram_user_id: int,
        text: str,
        *,
        parse_mode: str = "Markdown",
        reply_markup: Any = None,
    ) -> bool:
        try:
            await self._context.bot.send_message(
                chat_id=telegram_user_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
            )
            return True
        except Exception as e:
            logger.warning("Failed to send DM to %s: %s", telegram_user_id, e)
            return False

    async def send_to_chat(
        self,
        chat_id: int,
        text: str,
        *,
        parse_mode: str = "Markdown",
        reply_markup: Any = None,
        reply_to_message_id: int | None = None,
    ) -> bool:
        try:
            await self._context.bot.send_message(
                chat_id=chat_id,
                text=text,
                parse_mode=parse_mode,
                reply_markup=reply_markup,
                reply_to_message_id=reply_to_message_id,
            )
            return True
        except Exception as e:
            logger.warning("Failed to send to chat %s: %s", chat_id, e)
            return False


class TelegramNotificationService(INotificationService):
    """Implements notification port using Telegram messages."""

    def __init__(
        self,
        message_service: IMessageService,
        event_store: Any,  # IEventStore — avoids circular import
    ) -> None:
        self._msg = message_service
        self._store = event_store

    async def notify_event_created(self, event_id: int, organizer_id: int) -> None:
        # Group announcement handled by materialization service
        pass

    async def notify_event_modified(
        self, event_id: int, changed_fields: list[str]
    ) -> None:
        # Notify all attendees
        try:
            participants = await self._store.participants.by_event(event_id)
            fields_str = ", ".join(changed_fields)
            for p in participants:
                await self._msg.send_to_user(
                    p.telegram_user_id,
                    f"⚠️ Event #{event_id} was modified.\n"
                    f"Changed: {fields_str}\n"
                    f"Please reconfirm your attendance.",
                )
        except Exception:
            logger.exception("Failed to notify modification")

    async def notify_participant_joined(
        self, event_id: int, telegram_user_id: int
    ) -> None:
        # Group announcement handled by materialization service
        pass

    async def notify_threshold_reached(
        self, event_id: int, count: int, threshold: int
    ) -> None:
        # Group announcement handled by materialization service
        pass

    async def notify_event_locked(self, event_id: int) -> None:
        # Group announcement handled by materialization service
        pass

    async def notify_event_completed(self, event_id: int) -> None:
        # Memory collection handled separately
        pass

    async def notify_event_cancelled(self, event_id: int, reason: str) -> None:
        try:
            participants = await self._store.participants.by_event(event_id)
            for p in participants:
                await self._msg.send_to_user(
                    p.telegram_user_id,
                    f"❌ Event #{event_id} has been cancelled.\n"
                    f"Reason: {reason or 'No reason provided'}",
                )
        except Exception:
            logger.exception("Failed to notify cancellation")

    async def request_memory_collection(self, event_id: int) -> None:
        # Scheduled job handles this
        pass
