"""Application services — orchestrate commands + domain events → notifications.

These are the facades the presentation layer talks to.
"""

from __future__ import annotations

import logging

from coordination_engine.application.commands import (
    AddConstraintHandler,
    CancelAttendanceHandler,
    ConfirmAttendanceHandler,
    CreateEventHandler,
    JoinEventHandler,
    ModifyEventHandler,
    TransitionEventHandler,
)
from coordination_engine.application.dto import (
    AddConstraintCommand,
    CancelAttendanceCommand,
    ConfirmAttendanceCommand,
    CreateEventCommand,
    JoinEventCommand,
    ModifyEventCommand,
    Result,
    TransitionEventCommand,
)
from coordination_engine.application.event_bus import EventBus
from coordination_engine.application.ports import (
    INotificationService,
)
from coordination_engine.application.queries import (
    GetEventHandler,
    GetEventsForGroupHandler,
    GetEventsForUserHandler,
    GetParticipantHandler,
)
from coordination_engine.application.dto import (
    GetEventQuery,
    GetEventsForGroupQuery,
    GetEventsForUserQuery,
    GetParticipantQuery,
)
from coordination_engine.domain.events import (
    EventCancelled,
    EventCompleted,
    EventCreated,
    EventLocked,
    EventModified,
    ParticipantCancelled,
    ParticipantConfirmed,
    ParticipantJoined,
    ThresholdReached,
)
from coordination_engine.domain.repositories import IEventStore

logger = logging.getLogger("coord_engine.app_services")


class EventApplicationService:
    """Facade for event-related use cases.

    The presentation layer (bot handlers) calls methods on this service
    rather than directly invoking command/query handlers.
    """

    def __init__(
        self,
        store: IEventStore,
        event_bus: EventBus,
        notifications: INotificationService,
    ) -> None:
        self._create_handler = CreateEventHandler(store, event_bus)
        self._modify_handler = ModifyEventHandler(store, event_bus)
        self._transition_handler = TransitionEventHandler(store, event_bus)
        self._join_handler = JoinEventHandler(store, event_bus)
        self._confirm_handler = ConfirmAttendanceHandler(store, event_bus)
        self._cancel_attendance_handler = CancelAttendanceHandler(store, event_bus)
        self._constraint_handler = AddConstraintHandler(store, event_bus)
        self._get_handler = GetEventHandler(store)
        self._get_group_handler = GetEventsForGroupHandler(store)
        self._get_user_handler = GetEventsForUserHandler(store)
        self._get_participant_handler = GetParticipantHandler(store)
        self._notifications = notifications
        self._store = store
        self._event_bus = event_bus

    # -- Commands --

    async def create_event(self, cmd: CreateEventCommand) -> Result:
        result = await self._create_handler.execute(cmd)
        return result

    async def modify_event(self, cmd: ModifyEventCommand) -> Result:
        return await self._modify_handler.execute(cmd)

    async def transition_event(self, cmd: TransitionEventCommand) -> Result:
        return await self._transition_handler.execute(cmd)

    async def join_event(self, cmd: JoinEventCommand) -> Result:
        return await self._join_handler.execute(cmd)

    async def confirm_attendance(self, cmd: ConfirmAttendanceCommand) -> Result:
        return await self._confirm_handler.execute(cmd)

    async def cancel_attendance(self, cmd: CancelAttendanceCommand) -> Result:
        return await self._cancel_attendance_handler.execute(cmd)

    async def add_constraint(self, cmd: AddConstraintCommand) -> Result:
        return await self._constraint_handler.execute(cmd)

    # -- Queries --

    async def get_event(self, event_id: int) -> Result:
        return await self._get_handler.execute(GetEventQuery(event_id=event_id))

    async def get_events_for_group(
        self, group_telegram_id: int, states: list[str] | None = None
    ) -> Result:
        return await self._get_group_handler.execute(
            GetEventsForGroupQuery(
                group_telegram_id=group_telegram_id,
                states=states or ["proposed", "interested", "confirmed", "locked"],
            )
        )

    async def get_events_for_user(self, telegram_user_id: int) -> Result:
        return await self._get_user_handler.execute(
            GetEventsForUserQuery(telegram_user_id=telegram_user_id)
        )

    async def get_participant(self, event_id: int, telegram_user_id: int) -> Result:
        return await self._get_participant_handler.execute(
            GetParticipantQuery(event_id=event_id, telegram_user_id=telegram_user_id)
        )

    # -- Domain event → notification wiring --

    def _setup_event_handlers(self) -> None:
        self._event_bus.subscribe(EventCreated, self._on_event_created)
        self._event_bus.subscribe(EventModified, self._on_event_modified)
        self._event_bus.subscribe(EventLocked, self._on_event_locked)
        self._event_bus.subscribe(EventCompleted, self._on_event_completed)
        self._event_bus.subscribe(EventCancelled, self._on_event_cancelled)
        self._event_bus.subscribe(ParticipantJoined, self._on_participant_joined)
        self._event_bus.subscribe(ParticipantConfirmed, self._on_participant_confirmed)
        self._event_bus.subscribe(ParticipantCancelled, self._on_participant_cancelled)
        self._event_bus.subscribe(ThresholdReached, self._on_threshold_reached)

    async def _on_event_created(self, event: EventCreated) -> None:
        await self._notifications.notify_event_created(
            event.event_id, event.organizer_telegram_user_id
        )

    async def _on_event_modified(self, event: EventModified) -> None:
        await self._notifications.notify_event_modified(
            event.event_id, event.changed_fields
        )

    async def _on_event_locked(self, event: EventLocked) -> None:
        await self._notifications.notify_event_locked(event.event_id)

    async def _on_event_completed(self, event: EventCompleted) -> None:
        await self._notifications.notify_event_completed(event.event_id)
        await self._notifications.request_memory_collection(event.event_id)

    async def _on_event_cancelled(self, event: EventCancelled) -> None:
        await self._notifications.notify_event_cancelled(event.event_id, event.reason)

    async def _on_participant_joined(self, event: ParticipantJoined) -> None:
        await self._notifications.notify_participant_joined(
            event.event_id, event.telegram_user_id
        )

    async def _on_participant_confirmed(self, event: ParticipantConfirmed) -> None:
        pass  # Handled through threshold check

    async def _on_participant_cancelled(self, event: ParticipantCancelled) -> None:
        pass  # Private notification to organizer only

    async def _on_threshold_reached(self, event: ThresholdReached) -> None:
        await self._notifications.notify_threshold_reached(
            event.event_id, event.current_count, event.threshold
        )

    def initialize(self) -> None:
        """Wire domain event → notification handlers."""
        self._setup_event_handlers()
