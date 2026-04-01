"""
ParticipantService - Manages normalized participant records.
PRD v2 Section 2.1: Replaces attendance_list JSON operations.

This service provides the single write path for participant management.
All join/confirm/cancel operations must route through this service.
"""
from __future__ import annotations

import logging
import sqlalchemy
from datetime import datetime
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func

from db.models import Event, EventParticipant, ParticipantStatus, ParticipantRole

logger = logging.getLogger("coord_bot.services.participant")


class ParticipantError(Exception):
    """Base exception for participant operations."""
    pass


class ParticipantNotFoundError(ParticipantError):
    """Raised when expected participant record not found."""
    pass


class ParticipantService:
    """
    Single write path for participant management.
    
    Handles:
    - Join/leave operations
    - Confirm/cancel operations
    - Status queries and counts
    - Migration from legacy attendance_list
    """
    
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def join(
        self,
        event_id: int,
        telegram_user_id: int,
        source: str = "slash",
        role: ParticipantRole = ParticipantRole.participant,
    ) -> Tuple[EventParticipant, bool]:
        """
        Add user as participant (joined state).
        
        Returns:
            (participant_record, is_new_join)
        """
        # Check if already exists
        result = await self.session.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        participant = result.scalar_one_or_none()
        
        if participant:
            # Already joined - update status if cancelled
            if participant.status == ParticipantStatus.cancelled:
                participant.status = ParticipantStatus.joined
                participant.joined_at = datetime.utcnow()
                participant.cancelled_at = None
                logger.info(
                    "Participant rejoined event",
                    extra={"event_id": event_id, "user": telegram_user_id}
                )
                return participant, True
            
            if participant.status == ParticipantStatus.joined:
                return participant, False
            
            # Upgrade from no_show
            if participant.status == ParticipantStatus.no_show:
                participant.status = ParticipantStatus.joined
                participant.joined_at = datetime.utcnow()
                return participant, True
            
            return participant, False
        
        # Create new participant
        participant = EventParticipant(
            event_id=event_id,
            telegram_user_id=telegram_user_id,
            status=ParticipantStatus.joined,
            role=role,
            source=source,
            joined_at=datetime.utcnow(),
        )
        self.session.add(participant)
        
        logger.info(
            "New participant joined",
            extra={
                "event_id": event_id,
                "user": telegram_user_id,
                "source": source,
            }
        )
        
        return participant, True
    
    async def confirm(
        self,
        event_id: int,
        telegram_user_id: int,
        source: str = "callback",
    ) -> Tuple[EventParticipant, bool]:
        """
        Confirm participant attendance.
        
        Returns:
            (participant_record, is_new_confirm)
        """
        result = await self.session.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        participant = result.scalar_one_or_none()
        
        if not participant:
            # Auto-join on confirm
            return await self.join(event_id, telegram_user_id, source)
        
        if participant.status == ParticipantStatus.confirmed:
            return participant, False
        
        if participant.status == ParticipantStatus.cancelled:
            raise ParticipantError(
                f"User {telegram_user_id} cannot confirm after cancelling"
            )
        
        participant.status = ParticipantStatus.confirmed
        participant.confirmed_at = datetime.utcnow()
        
        logger.info(
            "Participant confirmed",
            extra={
                "event_id": event_id,
                "user": telegram_user_id,
                "source": source,
            }
        )
        
        return participant, True
    
    async def cancel(
        self,
        event_id: int,
        telegram_user_id: int,
        source: str = "callback",
    ) -> Tuple[EventParticipant, bool]:
        """
        Cancel participant attendance.
        
        Returns:
            (participant_record, is_new_cancel)
        """
        result = await self.session.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise ParticipantNotFoundError(
                f"User {telegram_user_id} is not a participant of event {event_id}"
            )
        
        if participant.status == ParticipantStatus.cancelled:
            return participant, False
        
        participant.status = ParticipantStatus.cancelled
        participant.cancelled_at = datetime.utcnow()
        
        logger.info(
            "Participant cancelled",
            extra={
                "event_id": event_id,
                "user": telegram_user_id,
                "source": source,
            }
        )
        
        return participant, True
    
    async def mark_no_show(
        self,
        event_id: int,
        telegram_user_id: int,
    ) -> None:
        """Mark participant as no-show after event completion."""
        result = await self.session.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        participant = result.scalar_one_or_none()
        
        if participant and participant.status == ParticipantStatus.confirmed:
            participant.status = ParticipantStatus.no_show
            logger.warning(
                "Participant marked as no-show",
                extra={"event_id": event_id, "user": telegram_user_id}
            )
    
    async def get_participant(
        self,
        event_id: int,
        telegram_user_id: int,
    ) -> Optional[EventParticipant]:
        """Get participant record."""
        result = await self.session.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        return result.scalar_one_or_none()
    
    async def get_all_participants(
        self,
        event_id: int,
        status_filter: Optional[ParticipantStatus] = None,
    ) -> List[EventParticipant]:
        """Get all participants for an event, optionally filtered by status."""
        query = select(EventParticipant).where(
            EventParticipant.event_id == event_id
        )
        
        if status_filter:
            query = query.where(EventParticipant.status == status_filter)
        
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def get_counts(self, event_id: int) -> Dict[str, int]:
        """
        Get participant counts by status.
        
        Returns dict with: joined, confirmed, cancelled, total
        """
        result = await self.session.execute(
            select(
                EventParticipant.status,
                func.count(EventParticipant.telegram_user_id)
            )
            .where(EventParticipant.event_id == event_id)
            .group_by(EventParticipant.status)
        )
        
        counts = {
            "joined": 0,
            "confirmed": 0,
            "cancelled": 0,
            "no_show": 0,
            "total": 0,
        }
        
        for status, count in result.all():
            counts[status.value] = count
            counts["total"] += count
        
        return counts
    
    async def get_confirmed_count(self, event_id: int) -> int:
        """Get count of confirmed participants (for threshold checks)."""
        result = await self.session.execute(
            select(func.count(EventParticipant.telegram_user_id))
            .where(
                EventParticipant.event_id == event_id,
                EventParticipant.status.in_([
                    ParticipantStatus.confirmed,
                    ParticipantStatus.joined,
                ])
            )
        )
        return result.scalar() or 0
    
    async def finalize_commitments(self, event_id: int) -> int:
        """
        Finalize commitments by marking all joined participants as confirmed.
        
        Returns the number of participants that were finalized.
        """
        result = await self.session.execute(
            update(EventParticipant)
            .where(
                EventParticipant.event_id == event_id,
                EventParticipant.status == ParticipantStatus.joined,
            )
            .values(
                status=ParticipantStatus.confirmed,
                confirmed_at=datetime.utcnow(),
            )
        )
        
        finalized_count = result.rowcount
        if finalized_count > 0:
            logger.info(
                "Finalized commitments for event",
                extra={
                    "event_id": event_id,
                    "finalized_count": finalized_count,
                }
            )
        
        return finalized_count
    
    async def unconfirm(
        self,
        event_id: int,
        telegram_user_id: int,
        source: str = "callback",
    ) -> Tuple[EventParticipant, bool]:
        """
        Unconfirm participant attendance (revert from confirmed to joined).
        
        Returns:
            (participant_record, is_new_unconfirm)
        """
        result = await self.session.execute(
            select(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        participant = result.scalar_one_or_none()
        
        if not participant:
            raise ParticipantNotFoundError(
                f"User {telegram_user_id} is not a participant of event {event_id}"
            )
        
        if participant.status != ParticipantStatus.confirmed:
            return participant, False
        
        participant.status = ParticipantStatus.joined
        participant.confirmed_at = None
        
        logger.info(
            "Participant unconfirmed",
            extra={
                "event_id": event_id,
                "user": telegram_user_id,
                "source": source,
            }
        )
        
        return participant, True
    
    async def remove_participant(
        self,
        event_id: int,
        telegram_user_id: int,
    ) -> bool:
        """
        Completely remove participant record.
        
        Use with caution - prefer cancel() for audit trail.
        """
        result = await self.session.execute(
            delete(EventParticipant).where(
                EventParticipant.event_id == event_id,
                EventParticipant.telegram_user_id == telegram_user_id,
            )
        )
        return result.rowcount > 0
    
    async def migrate_from_legacy(
        self,
        event: Event,
    ) -> int:
        """
        Migrate event from legacy attendance_list to normalized table.
        
        Returns count of migrated participants.
        """
        from bot.common.attendance import parse_attendance_with_status
        
        if not event.attendance_list:
            return 0
        
        attendance_map = parse_attendance_with_status(event.attendance_list)
        migrated_count = 0
        
        for telegram_user_id, status_str in attendance_map.items():
            # Map legacy status to new enum
            if status_str in {"committed", "confirmed"}:
                status = ParticipantStatus.confirmed
            elif status_str == "interested":
                status = ParticipantStatus.joined
            else:
                status = ParticipantStatus.joined
            
            participant = EventParticipant(
                event_id=event.event_id,
                telegram_user_id=telegram_user_id,
                status=status,
                source="migration",
            )
            self.session.add(participant)
            migrated_count += 1
        
        logger.info(
            "Migrated %d participants from legacy attendance_list",
            migrated_count,
            extra={"event_id": event.event_id}
        )
        
        return migrated_count
