"""
EventMaterializationService — Layer 2: Event Materialization (v3).

Posts natural-language updates to the group chat at key state transitions,
transforming events from silent records to visible social objects.

v3 Design:
- Show reality, don't engineer response
- All announcements identical regardless of user history
- No fragility framing ("if one drops, collapse")
- No reliability amplification
- Cancellations stay private to organizer
"""
from __future__ import annotations

import logging
import sqlalchemy
from datetime import datetime
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot

from db.models import Event, EventParticipant, ParticipantStatus, User

logger = logging.getLogger("coord_bot.services.materialization")


class EventMaterializationService:
    """
    Posts materialization announcements to group chat.

    v3 principle: Show what is. The bot reports reality; it does not try to
    change behavior through framing.
    """

    def __init__(self, bot: Bot, session: AsyncSession):
        self.bot = bot
        self.session = session

    async def announce_first_join(
        self,
        event: Event,
        user: User,
        group_chat_id: int,
    ) -> None:
        """
        v3: State the fact. No fragility framing.

        "Name joined. 1 person in."
        """
        name = self._get_display_name(user)

        message = f"{name} joined the {event.event_type}. 1 person in."

        await self._send_to_group(group_chat_id, message)
        logger.info("Announced first join", extra={"event_id": event.event_id, "user": user.user_id})

    async def announce_join(
        self,
        event: Event,
        user: User,
        confirmed_count: int,
        group_chat_id: int,
    ) -> None:
        """
        v3: Same format for every join. Just the count.

        "Name joined. N people in."
        """
        name = self._get_display_name(user)

        message = f"{name} joined the {event.event_type}. {confirmed_count} people in."

        await self._send_to_group(group_chat_id, message)
        logger.info("Announced join", extra={"event_id": event.event_id, "user": user.user_id})

    async def announce_threshold_reached(
        self,
        event: Event,
        confirmed_count: int,
        group_chat_id: int,
    ) -> None:
        """
        v3: State the threshold was met. No celebration framing.

        "Threshold met. N people in."
        """
        message = f"Threshold met for the {event.event_type}. {confirmed_count} people in."

        await self._send_to_group(group_chat_id, message)
        logger.info(
            "Announced threshold reached",
            extra={"event_id": event.event_id, "count": confirmed_count}
        )

    async def announce_event_locked(
        self,
        event: Event,
        participants: List[EventParticipant],
        group_chat_id: int,
    ) -> None:
        """
        Announce event is locked with participant list.

        "Event locked. Date/time. Who's in: names."
        """
        time_str = self._format_event_time(event)

        names = []
        for p in participants:
            if p.status in {ParticipantStatus.confirmed, ParticipantStatus.joined}:
                user_result = await self.session.execute(
                    sqlalchemy.select(User).where(User.telegram_user_id == p.telegram_user_id)
                )
                user = user_result.scalar_one_or_none()
                if user:
                    names.append(self._get_display_name(user))

        names_str = ", ".join(names) if names else "TBD"

        message = (
            f"{event.event_type} is locked.\n"
            f"{time_str}.\n\n"
            f"Who's in: {names_str}"
        )

        await self._send_to_group(group_chat_id, message)
        logger.info("Announced event locked", extra={"event_id": event.event_id})

    async def announce_cancellation_private(
        self,
        event: Event,
        user: User,
        organizer_chat_id: int,
        remaining_count: int,
        waitlist_count: int = 0,
    ) -> None:
        """
        Private notice to organizer only. No public announcement.

        v3: Cancellation is a fact for the organizer, not the group.
        """
        name = self._get_display_name(user)

        message = f"{name} is no longer attending. {remaining_count} people still in."

        if waitlist_count > 0:
            message += f"\n{waitlist_count} people on waitlist."

        await self._send_dm(organizer_chat_id, message)
        logger.info(
            "Sent private cancellation notice",
            extra={"event_id": event.event_id, "cancelled_user": user.user_id}
        )

    async def announce_event_completed(
        self,
        event: Event,
        participant_count: int,
        group_chat_id: int,
    ) -> None:
        """
        Announce event completion.

        "Event complete. N people joined."
        """
        message = f"{event.event_type} complete. {participant_count} people joined."

        await self._send_to_group(group_chat_id, message)
        logger.info("Announced event completed", extra={"event_id": event.event_id})

    def _get_display_name(self, user: User) -> str:
        """Get user display name with fallbacks."""
        if user.display_name:
            return user.display_name
        if user.username:
            return f"@{user.username}"
        return f"User #{user.telegram_user_id}"

    def _format_event_time(self, event: Event) -> str:
        """Format event scheduled time for display."""
        if not event.scheduled_time:
            return "Time TBD"

        time_str = event.scheduled_time.strftime("%a %d %b, %H:%M")
        return time_str

    async def _send_to_group(self, chat_id: int, message: str) -> None:
        """Send message to group chat."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(
                "Failed to send materialization message to group %s: %s",
                chat_id,
                e,
            )

    async def _send_dm(self, chat_id: int, message: str) -> None:
        """Send DM to user."""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=message,
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(
                "Failed to send materialization DM to %s: %s",
                chat_id,
                e,
            )
