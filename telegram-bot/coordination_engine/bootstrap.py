"""Application bootstrap — wires all layers together."""

from __future__ import annotations

import logging
from typing import Any

from coordination_engine.application.event_bus import EventBus
from coordination_engine.application.services import EventApplicationService
from coordination_engine.infrastructure.persistence import create_event_store
from coordination_engine.shared.container import Container

logger = logging.getLogger("coord_engine.bootstrap")


def build_container(
    database_url: str,
    telegram_context: Any,  # telegram.ext.ContextTypes.DEFAULT_TYPE
    llm_client: Any,  # ai.llm.LLMClient
    notification_service: Any,  # INotificationService implementation
) -> Container:
    """Build and configure the DI container.

    This is the composition root — the only place that knows about all
    concrete implementations.
    """
    container = Container()

    # -- Infrastructure --
    event_store = create_event_store(database_url)
    container.register_instance("event_store", event_store)

    event_bus = EventBus()
    container.register_instance("event_bus", event_bus)

    # -- Message service --
    from coordination_engine.infrastructure.telegram_adapter import (
        TelegramMessageService,
    )
    msg_service = TelegramMessageService(telegram_context)
    container.register_instance("message_service", msg_service)

    # -- LLM service --
    from coordination_engine.infrastructure.llm_adapter import LLMServiceAdapter
    llm_service = LLMServiceAdapter(llm_client)
    container.register_instance("llm_service", llm_service)

    # -- Notification service --
    container.register_instance("notification_service", notification_service)

    # -- Application service --
    app_service = EventApplicationService(
        store=event_store,
        event_bus=event_bus,
        notifications=notification_service,
    )
    app_service.initialize()  # Wire domain event → notification handlers
    container.register_instance("app_service", app_service)

    return container


async def shutdown_container(container: Container) -> None:
    """Graceful shutdown — close DB connections, cancel jobs, etc."""
    try:
        event_store = container.resolve("event_store")
        if hasattr(event_store, "close"):
            await event_store.close()
    except Exception:
        logger.exception("Error during shutdown")
