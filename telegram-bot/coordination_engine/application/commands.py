"""Application use cases — command handlers."""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from coordination_engine.application.dto import (
    AddConstraintCommand,
    CancelAttendanceCommand,
    CancelEventCommand,
    ConfirmAttendanceCommand,
    CreateEventCommand,
    JoinEventCommand,
    ModifyEventCommand,
    Result,
    TransitionEventCommand,
)
from coordination_engine.application.event_bus import EventBus
from coordination_engine.domain.entities import Constraint, Event, PlanningPreferences
from coordination_engine.domain.events import (
    DomainEvent,
    EventCancelled,
    EventCompleted,
    EventCreated,
    EventLocked,
    EventModified,
    EventStateChanged,
    ParticipantCancelled,
    ParticipantConfirmed,
    ParticipantJoined,
    ThresholdReached,
)
from coordination_engine.domain.exceptions import (
    DomainError,
    InvalidTransitionError,
    ThresholdNotMetError,
)
from coordination_engine.domain.repositories import IEventStore
from coordination_engine.domain.services import ParticipantService
from coordination_engine.domain.value_objects import (
    ConstraintType,
    EventState,
    EventType,
    ParticipantRole,
)

logger = logging.getLogger("coord_engine.commands")


def _parse_event_type(value: str) -> EventType:
    try:
        return EventType(value.lower())
    except ValueError:
        return EventType.SOCIAL


def _parse_event_state(value: str) -> EventState:
    try:
        return EventState(value.lower())
    except ValueError:
        raise InvalidTransitionError(f"Unknown state: {value}")


def _parse_constraint_type(value: str) -> ConstraintType:
    try:
        return ConstraintType(value.lower())
    except ValueError:
        raise ValueError(f"Unknown constraint type: {value}")


# ---------------------------------------------------------------------------
# Event Commands
# ---------------------------------------------------------------------------

class CreateEventHandler:
    def __init__(self, store: IEventStore, event_bus: EventBus) -> None:
        self._store = store
        self._event_bus = event_bus

    async def execute(self, cmd: CreateEventCommand) -> Result:
        try:
            group = await self._store.groups.ensure_exists(
                cmd.group_telegram_id,
            )

            event = Event(
                group_id=group.group_id,
                event_type=_parse_event_type(cmd.event_type),
                description=cmd.description[:500] if cmd.description else "",
                organizer_telegram_user_id=cmd.organizer_telegram_id,
                admin_telegram_user_id=cmd.organizer_telegram_id,
                scheduled_time=cmd.scheduled_time,
                commit_by=cmd.commit_by,
                collapse_at=cmd.collapse_at,
                duration_minutes=cmd.duration_minutes,
                threshold_attendance=cmd.threshold_attendance,
                min_participants=cmd.min_participants,
                target_participants=cmd.target_participants,
                planning_prefs=PlanningPreferences.from_dict(cmd.planning_prefs),
                state=EventState.PROPOSED,
            )

            async with self._store as uow:
                event = await uow.events.save(event)

                # Add organizer as participant
                await uow.participants.save(
                    event.add_participant(
                        cmd.organizer_telegram_id,
                        role=ParticipantRole.ORGANIZER,
                        source="command",
                    )
                )

            domain_events: list[DomainEvent] = [
                EventCreated(
                    event_id=event.event_id,
                    organizer_telegram_user_id=cmd.organizer_telegram_id,
                    group_id=group.group_id or 0,
                    description=event.description,
                ),
            ]

            # Check if threshold already met
            reached, count = ParticipantService.check_threshold_reached(event)
            if reached:
                domain_events.append(
                    ThresholdReached(
                        event_id=event.event_id,
                        current_count=count,
                        threshold=event.threshold_attendance,
                    )
                )

            await self._event_bus.publish_many(domain_events)

            return Result.ok(data=event, messages=["Event created."])

        except DomainError as e:
            return Result.fail(str(e))
        except Exception as e:
            logger.exception("Failed to create event")
            return Result.fail(f"Unexpected error: {e}")


class ModifyEventHandler:
    def __init__(self, store: IEventStore, event_bus: EventBus) -> None:
        self._store = store
        self._event_bus = event_bus

    async def execute(self, cmd: ModifyEventCommand) -> Result:
        try:
            event = await self._store.events.by_id(cmd.event_id)
            if not event:
                return Result.fail("Event not found.")

            if not event.can_be_modified():
                return Result.fail(f"Event is {event.state.value}; cannot modify.")

            # Map planning_prefs dict if provided
            prefs = None
            if cmd.planning_prefs is not None:
                prefs = PlanningPreferences.from_dict(cmd.planning_prefs)

            changed = event.apply_modification(
                description=cmd.description,
                event_type=_parse_event_type(cmd.event_type) if cmd.event_type else None,
                scheduled_time=cmd.scheduled_time,
                duration_minutes=cmd.duration_minutes,
                threshold_attendance=cmd.threshold_attendance,
                min_participants=cmd.min_participants,
                target_participants=cmd.target_participants,
                planning_prefs=prefs,
            )

            if not changed:
                return Result.fail("No changes detected.")

            await self._store.events.save(event)

            await self._event_bus.publish(
                EventModified(
                    event_id=event.event_id,
                    changed_fields=changed,
                    modifier_telegram_user_id=cmd.modifier_telegram_id,
                )
            )

            return Result.ok(data={"changed_fields": changed})

        except DomainError as e:
            return Result.fail(str(e))
        except Exception as e:
            logger.exception("Failed to modify event")
            return Result.fail(f"Unexpected error: {e}")


class TransitionEventHandler:
    def __init__(self, store: IEventStore, event_bus: EventBus) -> None:
        self._store = store
        self._event_bus = event_bus

    async def execute(self, cmd: TransitionEventCommand) -> Result:
        try:
            event = await self._store.events.by_id(cmd.event_id)
            if not event:
                return Result.fail("Event not found.")

            target_state = _parse_event_state(cmd.target_state)
            transition = event.transition_to(
                target_state,
                actor_telegram_user_id=cmd.actor_telegram_user_id,
                reason=cmd.reason,
                source=cmd.source,
            )

            await self._store.events.save(event)

            async with self._store as uow:
                await uow.state_transitions.record(transition)

            # Map to appropriate domain event
            domain_event: DomainEvent
            if target_state == EventState.LOCKED:
                domain_event = EventLocked(event_id=event.event_id, locked_at=datetime.now(timezone.utc))
            elif target_state == EventState.COMPLETED:
                domain_event = EventCompleted(event_id=event.event_id, completed_at=datetime.now(timezone.utc))
            elif target_state == EventState.CANCELLED:
                domain_event = EventCancelled(event_id=event.event_id, reason=cmd.reason)
            else:
                domain_event = EventStateChanged(
                    event_id=event.event_id,
                    from_state=transition.from_state.value,
                    to_state=transition.to_state.value,
                    actor_telegram_user_id=cmd.actor_telegram_user_id,
                    reason=cmd.reason,
                )

            await self._event_bus.publish(domain_event)

            return Result.ok(data={"state": target_state.value})

        except (DomainError, ThresholdNotMetError, InvalidTransitionError) as e:
            return Result.fail(str(e))
        except Exception as e:
            logger.exception("Failed to transition event")
            return Result.fail(f"Unexpected error: {e}")


class CancelEventHandler:
    def __init__(self, store: IEventStore, event_bus: EventBus) -> None:
        self._store = store
        self._event_bus = event_bus

    async def execute(self, cmd: CancelEventCommand) -> Result:
        transition_cmd = TransitionEventCommand(
            event_id=cmd.event_id,
            target_state="cancelled",
            actor_telegram_user_id=cmd.actor_telegram_user_id,
            reason=cmd.reason,
        )
        handler = TransitionEventHandler(self._store, self._event_bus)
        return await handler.execute(transition_cmd)


# ---------------------------------------------------------------------------
# Participant Commands
# ---------------------------------------------------------------------------

class JoinEventHandler:
    def __init__(self, store: IEventStore, event_bus: EventBus) -> None:
        self._store = store
        self._event_bus = event_bus

    async def execute(self, cmd: JoinEventCommand) -> Result:
        try:
            event = await self._store.events.by_id(cmd.event_id)
            if not event:
                return Result.fail("Event not found.")

            can_join, reason = ParticipantService.can_user_join(event, cmd.telegram_user_id)
            if not can_join:
                return Result.fail(reason)

            role = ParticipantRole.PARTICIPANT
            if cmd.role in {"organizer", "participant", "observer"}:
                role = ParticipantRole(cmd.role)

            participant = event.add_participant(
                cmd.telegram_user_id,
                role=role,
                source=cmd.source,
            )

            await self._store.participants.save(participant)

            await self._event_bus.publish(
                ParticipantJoined(
                    event_id=event.event_id,
                    telegram_user_id=cmd.telegram_user_id,
                    source=cmd.source,
                )
            )

            # Check threshold
            reached, count = ParticipantService.check_threshold_reached(event)
            if reached:
                await self._event_bus.publish(
                    ThresholdReached(
                        event_id=event.event_id,
                        current_count=count,
                        threshold=event.threshold_attendance,
                    )
                )

            return Result.ok(data={"status": participant.status.value})

        except DomainError as e:
            return Result.fail(str(e))
        except Exception as e:
            logger.exception("Failed to join event")
            return Result.fail(f"Unexpected error: {e}")


class ConfirmAttendanceHandler:
    def __init__(self, store: IEventStore, event_bus: EventBus) -> None:
        self._store = store
        self._event_bus = event_bus

    async def execute(self, cmd: ConfirmAttendanceCommand) -> Result:
        try:
            event = await self._store.events.by_id(cmd.event_id)
            if not event:
                return Result.fail("Event not found.")

            can_confirm, reason = ParticipantService.can_user_confirm(event, cmd.telegram_user_id)
            if not can_confirm:
                return Result.fail(reason)

            participant = event.get_participant(cmd.telegram_user_id)
            if not participant:
                return Result.fail("Not a participant.")

            participant.confirm()
            await self._store.participants.save(participant)

            await self._event_bus.publish(
                ParticipantConfirmed(
                    event_id=event.event_id,
                    telegram_user_id=cmd.telegram_user_id,
                )
            )

            reached, count = ParticipantService.check_threshold_reached(event)
            if reached:
                await self._event_bus.publish(
                    ThresholdReached(
                        event_id=event.event_id,
                        current_count=count,
                        threshold=event.threshold_attendance,
                    )
                )

            return Result.ok(data={"status": participant.status.value})

        except DomainError as e:
            return Result.fail(str(e))
        except Exception as e:
            logger.exception("Failed to confirm attendance")
            return Result.fail(f"Unexpected error: {e}")


class CancelAttendanceHandler:
    def __init__(self, store: IEventStore, event_bus: EventBus) -> None:
        self._store = store
        self._event_bus = event_bus

    async def execute(self, cmd: CancelAttendanceCommand) -> Result:
        try:
            event = await self._store.events.by_id(cmd.event_id)
            if not event:
                return Result.fail("Event not found.")

            can_cancel, reason = ParticipantService.can_user_cancel(event, cmd.telegram_user_id)
            if not can_cancel:
                return Result.fail(reason)

            participant = event.get_participant(cmd.telegram_user_id)
            if not participant:
                return Result.fail("Not a participant.")

            participant.cancel()
            await self._store.participants.save(participant)

            await self._event_bus.publish(
                ParticipantCancelled(
                    event_id=event.event_id,
                    telegram_user_id=cmd.telegram_user_id,
                    reason=cmd.reason,
                )
            )

            return Result.ok(data={"status": participant.status.value})

        except DomainError as e:
            return Result.fail(str(e))
        except Exception as e:
            logger.exception("Failed to cancel attendance")
            return Result.fail(f"Unexpected error: {e}")


# ---------------------------------------------------------------------------
# Constraint Commands
# ---------------------------------------------------------------------------

class AddConstraintHandler:
    def __init__(self, store: IEventStore, event_bus: EventBus) -> None:
        self._store = store
        self._event_bus = event_bus

    async def execute(self, cmd: AddConstraintCommand) -> Result:
        try:
            event = await self._store.events.by_id(cmd.event_id)
            if not event:
                return Result.fail("Event not found.")

            user = await self._store.users.get_or_create_by_telegram(
                cmd.user_telegram_id,
            )

            target_user = await self._store.users.by_username(
                cmd.target_username.lstrip("@")
            )
            if not target_user:
                return Result.fail(f"Target user @{cmd.target_username} not found.")

            constraint = Constraint(
                user_id=user.user_id,
                target_user_id=target_user.user_id,
                event_id=event.event_id,
                type=_parse_constraint_type(cmd.constraint_type),
                confidence=cmd.confidence,
            )

            await self._store.constraints.save(constraint)

            return Result.ok(data={"constraint_id": constraint.constraint_id})

        except DomainError as e:
            return Result.fail(str(e))
        except Exception as e:
            logger.exception("Failed to add constraint")
            return Result.fail(f"Unexpected error: {e}")
