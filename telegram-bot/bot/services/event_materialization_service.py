"""
EventMaterializationService - Layer 2: Makes events feel real.
PRD v2 Section 2.2: Event Materialization Layer.

This service posts natural-language updates to the group chat at key state transitions,
transforming events from silent records to visible social objects.
"""
from __future__ import annotations

import logging
import sqlalchemy
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from telegram import Bot

from db.models import Event, EventParticipant, ParticipantStatus, User
from bot.services.participant_service import ParticipantService

logger = logging.getLogger("coord_bot.services.materialization")


class EventMaterializationService:
    """
    Posts materialization announcements to group chat.
    
    Design principles (PRD Section 1.3):
    - Recognition over Enforcement: Celebrate commitments, don't shame cancellations
    - Gravity over Control: Make events feel real through visible momentum
    - Memory over Surveillance: Store what mattered, not everything
    
    Bot persona (PRD Section 5.2):
    - Quiet facilitator in coordination flows
    - Relational, not administrative
    - No gamification language
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
        Announce first person joining the event.
        
        Message: "[Name] just joined the [event]. We need [N] more for it to happen."
        """
        needed = (event.min_participants or 2) - 1
        name = self._get_display_name(user)
        
        message = (
            f"🌱 {name} just joined the {event.event_type}.\n"
            f"We need {needed} more for it to happen."
        )
        
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
        Announce someone joining the event.
        
        Message: "[Name] just joined the [event]. [N] people in."
        """
        name = self._get_display_name(user)
        min_required = event.min_participants or 2
        still_needed = max(0, min_required - confirmed_count)
        
        if still_needed > 0:
            message = (
                f"👋 {name} just joined the {event.event_type}.\n"
                f"We need {still_needed} more for it to happen. {confirmed_count} people in."
            )
        else:
            message = (
                f"👋 {name} just joined the {event.event_type}.\n"
                f"{confirmed_count} people in."
            )
        
        await self._send_to_group(group_chat_id, message)
        logger.info("Announced join", extra={"event_id": event.event_id, "user": user.user_id})
    
    async def announce_threshold_reached(
        self,
        event: Event,
        confirmed_count: int,
        group_chat_id: int,
    ) -> None:
        """
        Announce that threshold has been reached - event is now viable.
        
        Message: "We have enough for [event]. It's happening. [N] people in."
        
        This is a key materialization moment - the event becomes "real".
        """
        message = (
            f"✨ We have enough for the {event.event_type}.\n"
            f"It's happening! {confirmed_count} people in."
        )
        
        await self._send_to_group(group_chat_id, message)
        logger.info(
            "Announced threshold reached",
            extra={"event_id": event.event_id, "count": confirmed_count}
        )
    
    async def announce_high_reliability_join(
        self,
        event: Event,
        user: User,
        reliability_signal: str,
        group_chat_id: int,
    ) -> None:
        """
        Subtle signal amplification for high-reliability participants.

        Message: "[Name] just confirmed." (Signal only - no explicit score)

        PRD Design rule: Never show reliability score publicly.
        """
        name = self._get_display_name(user)

        # Use reliability signal (e.g., "been to every session", "always confirms early")
        message = f"🌟 {name} just confirmed{reliability_signal}."

        await self._send_to_group(group_chat_id, message)
        logger.info(
            "Announced high-reliability confirmation",
            extra={"event_id": event.event_id, "user": user.user_id}
        )
    
    async def announce_event_locked(
        self,
        event: Event,
        participants: List[EventParticipant],
        group_chat_id: int,
    ) -> None:
        """
        Announce event is locked with participant list.
        
        Message: "[Event] is locked. See you [date/time]. [participant list]"
        """
        time_str = self._format_event_time(event)
        
        # Build participant list (names only, no status distinction)
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
            f"🔒 {event.event_type} is locked.\n"
            f"See you {time_str}.\n\n"
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
    ) -> None:
        """
        Privately inform organizer of cancellation.
        
        PRD Design constraint: No public shaming of cancellations.
        No "[X] cancelled" posts in group.
        
        Message to organizer: "[Name] had to drop. [N] still in. [Waitlist status]"
        """
        name = self._get_display_name(user)
        
        message = (
            f"⚠️ {name} had to drop.\n"
            f"{remaining_count} people still in."
        )
        
        # TODO: Add waitlist status when waitlist feature is implemented
        
        await self._send_dm(organizer_chat_id, message)
        logger.info(
            "Sent private cancellation notice",
            extra={"event_id": event.event_id, "cancelled_user": user.user_id}
        )
    
    async def announce_near_collapse(
        self,
        event: Event,
        confirmed_count: int,
        group_chat_id: int,
    ) -> None:
        """
        Alert that event is at risk of collapse.
        
        Message: "Heads up: [event] needs [N] more to stay alive. Deadline: [time]."
        
        This creates threshold fragility awareness without penalties.
        """
        needed = (event.min_participants or 2) - confirmed_count
        deadline_str = self._format_deadline(event.collapse_at)
        
        message = (
            f"⚠️ Heads up: the {event.event_type} needs {needed} more to stay alive.\n"
            f"Deadline: {deadline_str}"
        )
        
        await self._send_to_group(group_chat_id, message)
        logger.info(
            "Announced near collapse",
            extra={"event_id": event.event_id, "needed": needed}
        )
    
    async def announce_event_completed(
        self,
        event: Event,
        participant_count: int,
        group_chat_id: int,
    ) -> None:
        """
        Announce event completion.
        
        Message: "[Event] is complete! Thanks to all [N] who joined."
        """
        message = (
            f"✅ {event.event_type} is complete!\n"
            f"Thanks to all {participant_count} who joined."
        )
        
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
            return "soon"
        
        time_str = event.scheduled_time.strftime("%a %d %b, %H:%M")
        return time_str
    
    def _format_deadline(self, deadline: Optional[datetime]) -> str:
        """Format collapse deadline for display."""
        if not deadline:
            return "soon"
        
        return deadline.strftime("%a %d %b, %H:%M")
    
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
