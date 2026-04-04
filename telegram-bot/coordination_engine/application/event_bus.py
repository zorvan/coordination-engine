"""Event bus — publish/subscribe for domain events."""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import Awaitable, Callable

from coordination_engine.domain.events import DomainEvent

logger = logging.getLogger("coord_engine.event_bus")

EventHandler = Callable[[DomainEvent], Awaitable[None]]


class EventBus:
    """In-process event bus for domain events.

    Handlers subscribe to specific event types. Publishing
    dispatches to all matching handlers concurrently.
    """

    def __init__(self) -> None:
        self._handlers: dict[type[DomainEvent], list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type[DomainEvent], handler: EventHandler) -> None:
        self._handlers[event_type].append(handler)

    def subscribe_all(self, handler: EventHandler) -> None:
        """Subscribe to ALL events (catch-all)."""
        self._handlers[DomainEvent].append(handler)  # type: ignore[arg-type]

    async def publish(self, event: DomainEvent) -> None:
        handlers = list(self._handlers.get(type(event), []))
        catch_all = self._handlers.get(DomainEvent, [])
        all_handlers = [*handlers, *catch_all]

        for handler in all_handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception("Event handler failed for %s", type(event).__name__)

    async def publish_many(self, events: list[DomainEvent]) -> None:
        for event in events:
            await self.publish(event)
