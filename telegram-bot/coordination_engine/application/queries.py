"""Application use cases — query handlers (read operations)."""

from __future__ import annotations

import logging

from coordination_engine.application.dto import (
    EventDTO,
    GetEventQuery,
    GetEventsForGroupQuery,
    GetEventsForUserQuery,
    GetParticipantQuery,
    ParticipantDTO,
    Result,
)
from coordination_engine.domain.repositories import IEventStore
from coordination_engine.domain.value_objects import EventState

logger = logging.getLogger("coord_engine.queries")


class GetEventHandler:
    def __init__(self, store: IEventStore) -> None:
        self._store = store

    async def execute(self, query: GetEventQuery) -> Result:
        try:
            event = await self._store.events.by_id(query.event_id)
            if not event:
                return Result.fail("Event not found.")

            participants = await self._store.participants.by_event(event.event_id or 0)

            return Result.ok(data=EventDTO(
                event_id=event.event_id or 0,
                group_id=event.group_id or 0,
                event_type=event.event_type.value,
                description=event.description,
                organizer_telegram_user_id=event.organizer_telegram_user_id,
                admin_telegram_user_id=event.admin_telegram_user_id,
                scheduled_time=event.scheduled_time,
                duration_minutes=event.duration_minutes,
                threshold_attendance=event.threshold_attendance,
                min_participants=event.min_participants,
                target_participants=event.target_participants,
                state=event.state.value,
                version=event.version,
                locked_at=event.locked_at,
                completed_at=event.completed_at,
                collapse_at=event.collapse_at,
                commit_by=event.commit_by,
                planning_prefs=event.planning_prefs.to_dict(),
                participant_count=len(participants),
                confirmed_count=event.confirmed_count(),
            ))
        except Exception as e:
            logger.exception("Failed to get event")
            return Result.fail(f"Unexpected error: {e}")


class GetEventsForGroupHandler:
    def __init__(self, store: IEventStore) -> None:
        self._store = store

    async def execute(self, query: GetEventsForGroupQuery) -> Result:
        try:
            group = await self._store.groups.by_telegram_id(query.group_telegram_id)
            if not group:
                return Result.fail("Group not found.")

            states = [EventState(s.lower()) for s in query.states]
            events = await self._store.events.by_state(states)
            # Filter by group
            events = [e for e in events if e.group_id == group.group_id]

            return Result.ok(data=[
                EventDTO(
                    event_id=e.event_id or 0,
                    group_id=e.group_id or 0,
                    event_type=e.event_type.value,
                    description=e.description,
                    organizer_telegram_user_id=e.organizer_telegram_user_id,
                    admin_telegram_user_id=e.admin_telegram_user_id,
                    scheduled_time=e.scheduled_time,
                    duration_minutes=e.duration_minutes,
                    threshold_attendance=e.threshold_attendance,
                    min_participants=e.min_participants,
                    target_participants=e.target_participants,
                    state=e.state.value,
                    version=e.version,
                    locked_at=e.locked_at,
                    completed_at=e.completed_at,
                    collapse_at=e.collapse_at,
                    commit_by=e.commit_by,
                    planning_prefs=e.planning_prefs.to_dict(),
                )
                for e in events
            ])
        except Exception as e:
            logger.exception("Failed to get events for group")
            return Result.fail(f"Unexpected error: {e}")


class GetEventsForUserHandler:
    def __init__(self, store: IEventStore) -> None:
        self._store = store

    async def execute(self, query: GetEventsForUserQuery) -> Result:
        try:
            events = await self._store.events.active_for_user(query.telegram_user_id)
            return Result.ok(data=[
                EventDTO(
                    event_id=e.event_id or 0,
                    group_id=e.group_id or 0,
                    event_type=e.event_type.value,
                    description=e.description,
                    organizer_telegram_user_id=e.organizer_telegram_user_id,
                    admin_telegram_user_id=e.admin_telegram_user_id,
                    scheduled_time=e.scheduled_time,
                    duration_minutes=e.duration_minutes,
                    threshold_attendance=e.threshold_attendance,
                    min_participants=e.min_participants,
                    target_participants=e.target_participants,
                    state=e.state.value,
                    version=e.version,
                    locked_at=e.locked_at,
                    completed_at=e.completed_at,
                    collapse_at=e.collapse_at,
                    commit_by=e.commit_by,
                    planning_prefs=e.planning_prefs.to_dict(),
                    participant_count=0,
                    confirmed_count=e.confirmed_count(),
                )
                for e in events
            ])
        except Exception as e:
            logger.exception("Failed to get events for user")
            return Result.fail(f"Unexpected error: {e}")


class GetParticipantHandler:
    def __init__(self, store: IEventStore) -> None:
        self._store = store

    async def execute(self, query: GetParticipantQuery) -> Result:
        try:
            participant = await self._store.participants.by_event_and_user(
                query.event_id, query.telegram_user_id
            )
            if not participant:
                return Result.fail("Participant not found.")

            # Look up user info for display
            user = await self._store.users.by_telegram_id(query.telegram_user_id)

            return Result.ok(data=ParticipantDTO(
                event_id=participant.event_id,
                telegram_user_id=participant.telegram_user_id,
                username=user.username if user else None,
                display_name=user.display_name if user else None,
                status=participant.status.value,
                role=participant.role.value,
                joined_at=participant.joined_at,
                confirmed_at=participant.confirmed_at,
            ))
        except Exception as e:
            logger.exception("Failed to get participant")
            return Result.fail(f"Unexpected error: {e}")
