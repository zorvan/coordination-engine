"""
WaitlistService - Manages waitlist for oversubscribed events.
PRD v2 Section 4.3: Waitlist support (TODO-023).

Features:
- Join waitlist when event at capacity
- Auto-promote from waitlist on cancellation
- Waitlist position tracking
- Offer expiration handling
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete

from db.models import Event, EventWaitlist, EventParticipant, ParticipantStatus

logger = logging.getLogger("coord_bot.services.waitlist")


class WaitlistService:
    """
    Manages event waitlists.

    Handles:
    - Joining waitlist
    - Auto-promotion on cancellation
    - Position tracking
    - Offer expiration
    """

    # Offer expiration: 24 hours
    OFFER_EXPIRATION_HOURS = 24

    def __init__(self, session: AsyncSession):
        self.session = session

    async def join_waitlist(
        self,
        event_id: int,
        telegram_user_id: int,
    ) -> Tuple[EventWaitlist, int]:
        """
        Add user to event waitlist.

        Returns:
            (waitlist_record, position)

        Raises:
            ValueError: If user already on waitlist or already participant
        """
        # Check if already participant
        participant_result = await self.session.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        if participant_result.scalar_one_or_none():
            raise ValueError("User is already a participant")

        # Check if already on waitlist
        existing = await self.session.execute(
            select(EventWaitlist).where(
                EventWaitlist.event_id == event_id,
                EventWaitlist.telegram_user_id == telegram_user_id,
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError("User already on waitlist")

        # Get current max position
        max_pos_result = await self.session.execute(
            select(func.max(EventWaitlist.position)).where(
                EventWaitlist.event_id == event_id
            )
        )
        max_position = max_pos_result.scalar() or 0
        new_position = max_position + 1

        # Create waitlist entry
        waitlist = EventWaitlist(
            event_id=event_id,
            telegram_user_id=telegram_user_id,
            position=new_position,
            status="waiting",
        )
        self.session.add(waitlist)

        logger.info(
            "User %s joined waitlist for event %s (position %s)",
            telegram_user_id,
            event_id,
            new_position,
        )

        return waitlist, new_position

    async def leave_waitlist(
        self,
        event_id: int,
        telegram_user_id: int,
    ) -> bool:
        """
        Remove user from waitlist.

        Returns:
            True if removed, False if not found
        """
        result = await self.session.execute(
            delete(EventWaitlist).where(
                EventWaitlist.event_id == event_id,
                EventWaitlist.telegram_user_id == telegram_user_id,
            )
        )

        removed = result.rowcount > 0

        if removed:
            # Reorder remaining waitlist
            await self._reorder_waitlist(event_id)

        return removed

    async def promote_from_waitlist(
        self,
        event_id: int,
    ) -> Optional[EventWaitlist]:
        """
        Promote first waiting user from waitlist.

        Returns:
            Promoted waitlist record, or None if no one waiting

        Process:
        1. Get first waiting user
        2. Mark as "offered"
        3. Set expiration
        4. Return for notification
        """
        # Get first waiting user
        result = await self.session.execute(
            select(EventWaitlist)
            .where(
                EventWaitlist.event_id == event_id,
                EventWaitlist.status == "waiting",
            )
            .order_by(EventWaitlist.position)
            .limit(1)
        )
        waitlist = result.scalar_one_or_none()

        if not waitlist:
            return None

        # Mark as offered with expiration
        waitlist.status = "offered"
        waitlist.expires_at = datetime.utcnow() + timedelta(
            hours=self.OFFER_EXPIRATION_HOURS
        )

        logger.info(
            "Promoted user %s from waitlist for event %s",
            waitlist.telegram_user_id,
            event_id,
        )

        return waitlist

    async def confirm_promotion(
        self,
        event_id: int,
        telegram_user_id: int,
    ) -> bool:
        """
        Confirm waitlist promotion (user accepts offer).

        Returns:
            True if confirmed, False if not valid
        """
        # Get waitlist entry
        result = await self.session.execute(
            select(EventWaitlist).where(
                EventWaitlist.event_id == event_id,
                EventWaitlist.telegram_user_id == telegram_user_id,
                EventWaitlist.status == "offered",
            )
        )
        waitlist = result.scalar_one_or_none()

        if not waitlist:
            return False

        # Check expiration
        if waitlist.expires_at and datetime.utcnow() > waitlist.expires_at:
            waitlist.status = "expired"
            await self._reorder_waitlist(event_id)
            return False

        # Mark as promoted
        waitlist.status = "promoted"

        # Remove from waitlist (will be added as participant)
        await self.session.delete(waitlist)
        await self._reorder_waitlist(event_id)

        return True

    async def check_expired_offers(
        self,
        event_id: Optional[int] = None,
    ) -> List[EventWaitlist]:
        """
        Check for expired waitlist offers.

        Args:
            event_id: Optional specific event to check

        Returns:
            List of expired waitlist entries
        """
        now = datetime.utcnow()

        query = select(EventWaitlist).where(
            EventWaitlist.status == "offered",
            EventWaitlist.expires_at.is_not(None),
            EventWaitlist.expires_at < now,
        )

        if event_id:
            query = query.where(EventWaitlist.event_id == event_id)

        result = await self.session.execute(query)
        expired = list(result.scalars().all())

        # Mark as expired
        for waitlist in expired:
            waitlist.status = "expired"

        # Reorder waitlists
        if event_id:
            await self._reorder_waitlist(event_id)
        else:
            # Get unique event IDs
            event_ids = set(w.event_id for w in expired)
            for eid in event_ids:
                await self._reorder_waitlist(eid)

        return expired

    async def get_waitlist_position(
        self,
        event_id: int,
        telegram_user_id: int,
    ) -> Optional[int]:
        """Get user's waitlist position."""
        result = await self.session.execute(
            select(EventWaitlist.position).where(
                EventWaitlist.event_id == event_id,
                EventWaitlist.telegram_user_id == telegram_user_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_waitlist_count(
        self,
        event_id: int,
    ) -> int:
        """Get total waitlist count for event."""
        result = await self.session.execute(
            select(func.count(EventWaitlist.waitlist_id)).where(
                EventWaitlist.event_id == event_id,
                EventWaitlist.status == "waiting",
            )
        )
        return result.scalar() or 0

    async def get_waitlist(
        self,
        event_id: int,
    ) -> List[EventWaitlist]:
        """Get full waitlist for event."""
        result = await self.session.execute(
            select(EventWaitlist)
            .where(
                EventWaitlist.event_id == event_id,
                EventWaitlist.status == "waiting",
            )
            .order_by(EventWaitlist.position)
        )
        return list(result.scalars().all())

    async def _reorder_waitlist(self, event_id: int) -> None:
        """Reorder waitlist positions after removal."""
        result = await self.session.execute(
            select(EventWaitlist)
            .where(
                EventWaitlist.event_id == event_id,
                EventWaitlist.status == "waiting",
            )
            .order_by(EventWaitlist.position)
        )
        waitlists = list(result.scalars().all())

        for new_pos, waitlist in enumerate(waitlists, 1):
            waitlist.position = new_pos

    async def is_event_oversubscribed(
        self,
        event_id: int,
    ) -> bool:
        """Check if event is at/over capacity."""
        from sqlalchemy import select

        event_result = await self.session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = event_result.scalar_one_or_none()

        if not event:
            return False

        # Count confirmed participants
        participant_result = await self.session.execute(
            select(func.count(EventParticipant.telegram_user_id)).where(
                EventParticipant.event_id == event_id,
                EventParticipant.status.in_([
                    ParticipantStatus.confirmed,
                    ParticipantStatus.joined,
                ])
            )
        )
        confirmed_count = participant_result.scalar() or 0

        threshold = event.threshold_attendance or 3
        return confirmed_count >= threshold
