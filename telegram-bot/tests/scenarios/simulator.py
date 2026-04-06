"""
Scenario simulator for long-running event journeys.

This layer uses the real domain services with a live async test database so
scenario tests can model repeated user interactions over time instead of only
isolated unit calls.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from bot.common.confirmation import invalidate_confirmations_and_notify
from bot.services.event_lifecycle_service import EventLifecycleService
from bot.services.event_memory_service import EventMemoryService
from bot.services.group_event_type_stats_service import GroupEventTypeStatsService
from bot.services.participant_service import ParticipantService
from bot.services.waitlist_service import WaitlistService
from db.models import Constraint, Event, EventMemory, EventParticipant, Group, ParticipantStatus, User
from db.users import get_or_create_user_id


class ScenarioBot:
    """Minimal bot double that records sent messages."""

    def __init__(self, username: str = "test_bot") -> None:
        self.username = username
        self.sent_messages: list[dict[str, Any]] = []

    async def send_message(self, chat_id: int, text: str, **kwargs: Any) -> None:
        self.sent_messages.append({"chat_id": chat_id, "text": text, **kwargs})

    async def get_chat(self, target: Any) -> Any:
        raise RuntimeError(f"ScenarioBot cannot resolve Telegram chat for {target!r}")


@dataclass
class ScenarioContext:
    """Minimal context object for notification helpers."""

    bot: ScenarioBot


class EventScenarioSimulator:
    """High-level helper for executable event-journey scenarios."""

    def __init__(self, session) -> None:
        self.session = session
        self.bot = ScenarioBot()
        self.context = ScenarioContext(bot=self.bot)

    async def create_user(
        self,
        username: str,
        *,
        display_name: str | None = None,
        telegram_user_id: int,
    ) -> User:
        user = User(
            telegram_user_id=telegram_user_id,
            username=username,
            display_name=display_name or username,
        )
        self.session.add(user)
        await self.session.flush()
        return user

    async def create_group(
        self,
        name: str,
        *,
        telegram_group_id: int,
        members: list[User],
    ) -> Group:
        group = Group(
            telegram_group_id=telegram_group_id,
            group_name=name,
            member_list=[int(member.telegram_user_id) for member in members],
        )
        self.session.add(group)
        await self.session.flush()
        return group

    async def create_event(
        self,
        *,
        group: Group,
        organizer: User,
        event_type: str,
        description: str,
        scheduled_time: datetime | None,
        min_participants: int,
        target_participants: int,
        duration_minutes: int = 120,
        state: str = "proposed",
    ) -> Event:
        event = Event(
            group_id=group.group_id,
            event_type=event_type,
            description=description,
            organizer_telegram_user_id=organizer.telegram_user_id,
            admin_telegram_user_id=organizer.telegram_user_id,
            scheduled_time=scheduled_time,
            duration_minutes=duration_minutes,
            min_participants=min_participants,
            target_participants=target_participants,
            state=state,
        )
        self.session.add(event)
        await self.session.flush()
        return event

    async def fetch_event(self, event_id: int) -> Event:
        result = await self.session.execute(
            select(Event)
            .execution_options(populate_existing=True)
            .options(
                selectinload(Event.participants),
                selectinload(Event.waitlist),
                selectinload(Event.memories),
            )
            .where(Event.event_id == event_id)
        )
        return result.scalar_one()

    async def participant_rows(self, event_id: int) -> list[EventParticipant]:
        result = await self.session.execute(
            select(EventParticipant)
            .where(EventParticipant.event_id == event_id)
            .order_by(EventParticipant.telegram_user_id)
        )
        return list(result.scalars().all())

    async def join(self, event_id: int, user: User, *, role: str = "participant") -> Event:
        participant_service = ParticipantService(self.session)
        await participant_service.join(
            event_id=event_id,
            telegram_user_id=int(user.telegram_user_id),
            source="scenario",
            role=role,
        )
        event = await self.fetch_event(event_id)
        if event.state == "proposed":
            lifecycle = EventLifecycleService(self.bot, self.session)
            event, _ = await lifecycle.transition_with_lifecycle(
                event_id=event_id,
                target_state="interested",
                actor_telegram_user_id=int(user.telegram_user_id),
                source="scenario",
                reason="Scenario join",
            )
        await self.session.commit()
        return await self.fetch_event(event_id)

    async def confirm(self, event_id: int, user: User) -> Event:
        participant_service = ParticipantService(self.session)
        await participant_service.confirm(
            event_id=event_id,
            telegram_user_id=int(user.telegram_user_id),
            source="scenario",
        )
        event = await self.fetch_event(event_id)
        if event.state != "confirmed":
            lifecycle = EventLifecycleService(self.bot, self.session)
            event, _ = await lifecycle.transition_with_lifecycle(
                event_id=event_id,
                target_state="confirmed",
                actor_telegram_user_id=int(user.telegram_user_id),
                source="scenario",
                reason="Scenario confirm",
            )
        await self.session.commit()
        return await self.fetch_event(event_id)

    async def uncommit(self, event_id: int, user: User) -> Event:
        participant_service = ParticipantService(self.session)
        await participant_service.unconfirm(
            event_id=event_id,
            telegram_user_id=int(user.telegram_user_id),
            source="scenario",
        )
        event = await self.fetch_event(event_id)
        confirmed_count = await participant_service.get_confirmed_count(event_id)
        active_count = sum(
            1
            for participant in event.participants
            if participant.status in {ParticipantStatus.joined, ParticipantStatus.confirmed}
        )
        if event.state == "confirmed" and confirmed_count == 0:
            lifecycle = EventLifecycleService(self.bot, self.session)
            target_state = "interested" if active_count > 0 else "proposed"
            event, _ = await lifecycle.transition_with_lifecycle(
                event_id=event_id,
                target_state=target_state,
                actor_telegram_user_id=int(user.telegram_user_id),
                source="scenario",
                reason="Scenario uncommit",
            )
        await self.session.commit()
        return await self.fetch_event(event_id)

    async def exit(self, event_id: int, user: User) -> Event:
        participant_service = ParticipantService(self.session)
        await participant_service.cancel(
            event_id=event_id,
            telegram_user_id=int(user.telegram_user_id),
            source="scenario",
        )
        waitlist_service = WaitlistService(self.session, self.bot)
        await waitlist_service.trigger_auto_fill(event_id)

        event = await self.fetch_event(event_id)
        confirmed_count = await participant_service.get_confirmed_count(event_id)
        active_count = sum(
            1
            for participant in event.participants
            if participant.status in {ParticipantStatus.joined, ParticipantStatus.confirmed}
        )
        if event.state == "confirmed" and confirmed_count == 0:
            lifecycle = EventLifecycleService(self.bot, self.session)
            target_state = "interested" if active_count > 0 else "proposed"
            event, _ = await lifecycle.transition_with_lifecycle(
                event_id=event_id,
                target_state=target_state,
                actor_telegram_user_id=int(user.telegram_user_id),
                source="scenario",
                reason="Scenario exit",
            )

        await self.session.commit()
        return await self.fetch_event(event_id)

    async def lock(self, event_id: int, actor: User) -> Event:
        lifecycle = EventLifecycleService(self.bot, self.session)
        await lifecycle.transition_with_lifecycle(
            event_id=event_id,
            target_state="locked",
            actor_telegram_user_id=int(actor.telegram_user_id),
            source="scenario",
            reason="Scenario lock",
            expected_version=(await self.fetch_event(event_id)).version,
        )
        participant_service = ParticipantService(self.session)
        await participant_service.finalize_commitments(event_id)
        await self.session.commit()
        return await self.fetch_event(event_id)

    async def cancel_event(self, event_id: int, actor: User, *, reason: str = "Scenario cancellation") -> Event:
        lifecycle = EventLifecycleService(self.bot, self.session)
        await lifecycle.transition_with_lifecycle(
            event_id=event_id,
            target_state="cancelled",
            actor_telegram_user_id=int(actor.telegram_user_id),
            source="scenario",
            reason=reason,
            expected_version=(await self.fetch_event(event_id)).version,
        )
        await self.session.commit()
        return await self.fetch_event(event_id)

    async def complete_event(self, event_id: int, actor: User) -> Event:
        lifecycle = EventLifecycleService(self.bot, self.session)
        await lifecycle.transition_with_lifecycle(
            event_id=event_id,
            target_state="completed",
            actor_telegram_user_id=int(actor.telegram_user_id),
            source="scenario",
            reason="Scenario completion",
            expected_version=(await self.fetch_event(event_id)).version,
        )
        await self.session.commit()
        return await self.fetch_event(event_id)

    async def add_to_waitlist(self, event_id: int, user: User) -> int:
        waitlist_service = WaitlistService(self.session, self.bot)
        position = await waitlist_service.add_to_waitlist(event_id, int(user.telegram_user_id))
        await self.session.commit()
        return position

    async def accept_waitlist_offer(self, event_id: int, user: User) -> bool:
        waitlist_service = WaitlistService(self.session, self.bot)
        accepted = await waitlist_service.accept_offer(event_id, int(user.telegram_user_id))
        await self.session.commit()
        return accepted

    async def decline_waitlist_offer(self, event_id: int, user: User) -> bool:
        waitlist_service = WaitlistService(self.session, self.bot)
        declined = await waitlist_service.decline_offer(event_id, int(user.telegram_user_id))
        await self.session.commit()
        return declined

    async def modify_event(self, event_id: int, actor: User, **changes: Any) -> Event:
        event = await self.fetch_event(event_id)
        changed_fields = set(changes)
        for key, value in changes.items():
            setattr(event, key, value)

        if "min_participants" in changed_fields and event.target_participants < event.min_participants:
            event.target_participants = event.min_participants

        if changed_fields & {
            "scheduled_time",
            "duration_minutes",
            "min_participants",
            "target_participants",
            "description",
            "planning_prefs",
        }:
            await invalidate_confirmations_and_notify(
                context=self.context,
                event=event,
                reason="scenario modify",
            )
            active_count = sum(
                1
                for participant in (event.participants or [])
                if participant.status in {ParticipantStatus.joined, ParticipantStatus.confirmed}
            )
            event.state = "interested" if active_count > 0 else "proposed"

        event.version += 1
        await self.session.commit()
        return await self.fetch_event(event_id)

    async def add_constraint(
        self,
        event_id: int,
        source_user: User,
        target_user: User,
        constraint_type: str,
        *,
        confidence: float = 0.8,
    ) -> Constraint:
        source_user_id = await get_or_create_user_id(
            self.session,
            telegram_user_id=int(source_user.telegram_user_id),
            display_name=source_user.display_name,
            username=source_user.username,
        )
        target_user_id = await get_or_create_user_id(
            self.session,
            telegram_user_id=int(target_user.telegram_user_id),
            display_name=target_user.display_name,
            username=target_user.username,
        )
        constraint = Constraint(
            user_id=source_user_id,
            target_user_id=target_user_id,
            event_id=event_id,
            type=constraint_type,
            confidence=confidence,
        )
        self.session.add(constraint)
        await self.session.commit()
        return constraint

    async def add_availability(self, event_id: int, user: User, slot_iso: str) -> Constraint:
        source_user_id = await get_or_create_user_id(
            self.session,
            telegram_user_id=int(user.telegram_user_id),
            display_name=user.display_name,
            username=user.username,
        )
        constraint = Constraint(
            user_id=source_user_id,
            target_user_id=None,
            event_id=event_id,
            type=f"available:{slot_iso}",
            confidence=1.0,
        )
        self.session.add(constraint)
        await self.session.commit()
        return constraint

    async def record_memory_fragment(self, event_id: int, text: str) -> EventMemory:
        event = await self.fetch_event(event_id)
        memory = event.memories
        if memory is None:
            memory = EventMemory(event_id=event_id, fragments=[])
            self.session.add(memory)
            await self.session.flush()

        fragments = list(memory.fragments or [])
        fragments.append(
            {
                "text": text,
                "submitted_at": datetime.utcnow().isoformat(),
                "word_count": len(text.split()),
            }
        )
        memory.fragments = fragments
        await self.session.commit()
        return memory

    async def get_failure_pattern(self, group_id: int, event_type: str) -> dict[str, Any] | None:
        service = GroupEventTypeStatsService(self.session)
        return await service.get_failure_pattern(group_id, event_type)

    async def get_memory_hook(self, group_id: int, event_type: str, max_words: int = 12) -> str | None:
        service = EventMemoryService(self.bot, self.session)
        return await service.get_memory_hook(group_id, event_type, max_words=max_words)
