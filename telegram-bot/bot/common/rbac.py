"""
RBAC (Role-Based Access Control) helpers for event operations.
PRD v2: Organizer control and permission checks.
"""
from __future__ import annotations

from typing import Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import Event, EventParticipant, ParticipantRole


async def check_event_organizer(
    session: AsyncSession,
    event_id: int,
    telegram_user_id: int,
) -> Tuple[bool, Optional[str]]:
    """
    Check if user is the event organizer.

    Returns:
        (is_authorized, error_message)
    """
    result = await session.execute(
        select(Event).where(Event.event_id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        return False, "Event not found"

    if event.organizer_telegram_user_id != telegram_user_id:
        return False, "Only the event organizer can perform this action"

    return True, None


async def check_event_admin(
    session: AsyncSession,
    event_id: int,
    telegram_user_id: int,
) -> Tuple[bool, Optional[str]]:
    """
    Check if user is an event admin (organizer or group admin).

    Returns:
        (is_authorized, error_message)
    """
    result = await session.execute(
        select(Event).where(Event.event_id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        return False, "Event not found"

    # Check if user is organizer or admin
    if event.organizer_telegram_user_id == telegram_user_id:
        return True, None

    if event.admin_telegram_user_id == telegram_user_id:
        return True, None

    return False, "Only event organizer or admin can perform this action"


async def check_event_participant(
    session: AsyncSession,
    event_id: int,
    telegram_user_id: int,
) -> Tuple[bool, Optional[str], Optional[EventParticipant]]:
    """
    Check if user is a participant of the event.

    Returns:
        (is_authorized, error_message, participant_record)
    """
    result = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.telegram_user_id == telegram_user_id,
        )
    )
    participant = result.scalar_one_or_none()

    if not participant:
        return False, "You are not a participant of this event", None

    return True, None, participant


async def check_can_modify_event(
    session: AsyncSession,
    event_id: int,
    telegram_user_id: int,
) -> Tuple[bool, Optional[str]]:
    """
    Check if user can modify the event.

    Permissions:
    - Organizer: Always can modify
    - Admin: Can modify
    - Confirmed participants: Can modify in emergencies (logged)

    Returns:
        (is_authorized, error_message)
    """
    result = await session.execute(
        select(Event).where(Event.event_id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        return False, "Event not found"

    # Organizer or admin can always modify
    if event.organizer_telegram_user_id == telegram_user_id:
        return True, None

    if event.admin_telegram_user_id == telegram_user_id:
        return True, None

    # Confirmed participants can modify in emergencies
    participant_result = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.telegram_user_id == telegram_user_id,
            EventParticipant.status == 'confirmed',
        )
    )
    participant = participant_result.scalar_one_or_none()

    if participant:
        return True, None  # Will be logged as emergency modification

    return False, "Only organizer, admin, or confirmed participants can modify this event"


async def check_can_submit_private_note(
    session: AsyncSession,
    event_id: int,
    telegram_user_id: int,
) -> Tuple[bool, Optional[str]]:
    """
    Check if user can submit private attendee notes.

    Rules (PRD v2):
    - Only interested attendees (joined or confirmed) can submit
    - Organizer CANNOT submit attendee notes (they're private feedback)

    Returns:
        (is_authorized, error_message)
    """
    # Check if user is organizer (organizers cannot submit private notes)
    event_result = await session.execute(
        select(Event).where(Event.event_id == event_id)
    )
    event = event_result.scalar_one_or_none()

    if not event:
        return False, "Event not found"

    if event.organizer_telegram_user_id == telegram_user_id:
        return False, "Organizers cannot submit private attendee notes"

    # Check if user is a participant
    participant_result = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.telegram_user_id == telegram_user_id,
            EventParticipant.status.in_(['joined', 'confirmed']),
        )
    )
    participant = participant_result.scalar_one_or_none()

    if not participant:
        return False, "Only joined or confirmed participants can submit private notes"

    return True, None


async def check_can_lock_event(
    session: AsyncSession,
    event_id: int,
    telegram_user_id: int,
) -> Tuple[bool, Optional[str]]:
    """
    Check if user can lock the event.

    Permissions:
    - Organizer: Can lock
    - Admin: Can lock

    Returns:
        (is_authorized, error_message)
    """
    return await check_event_admin(session, event_id, telegram_user_id)


async def get_user_event_role(
    session: AsyncSession,
    event_id: int,
    telegram_user_id: int,
) -> Optional[str]:
    """
    Get user's role for an event.

    Returns:
        'organizer', 'admin', 'participant', or None
    """
    result = await session.execute(
        select(Event).where(Event.event_id == event_id)
    )
    event = result.scalar_one_or_none()

    if not event:
        return None

    if event.organizer_telegram_user_id == telegram_user_id:
        return 'organizer'

    if event.admin_telegram_user_id == telegram_user_id:
        return 'admin'

    participant_result = await session.execute(
        select(EventParticipant).where(
            EventParticipant.event_id == event_id,
            EventParticipant.telegram_user_id == telegram_user_id,
        )
    )
    participant = participant_result.scalar_one_or_none()

    if participant:
        return 'participant'

    return None
