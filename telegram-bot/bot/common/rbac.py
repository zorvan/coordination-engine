"""
RBAC (Role-Based Access Control) helpers for event operations.
PRD v2: Organizer control, permission checks, and group membership enforcement.
"""
from __future__ import annotations

from typing import Optional, Tuple, TYPE_CHECKING
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from db.models import Event, EventParticipant, Group

if TYPE_CHECKING:
    from db.models import Event as EventType, Group as GroupType


async def check_group_membership(
    session: AsyncSession,
    group_id: int,
    user_id: int,
    telegram_chat_id: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """
    Check if a user is a member of the given group.

    Checks in order:
    1. If telegram_chat_id matches the group's telegram_group_id → implicit member
    2. If user has participated in ANY event in this group → proven member
    3. Explicit check of Group.member_list (unreliable if not fully populated)

    Args:
        session: DB session
        group_id: Internal group ID
        user_id: Telegram user ID
        telegram_chat_id: Optional Telegram chat ID for implicit membership

    Returns:
        (is_member, error_message)
    """
    result = await session.execute(
        select(Group).where(Group.group_id == group_id)
    )
    group = result.scalar_one_or_none()

    if not group:
        return False, "Group not found"

    # 1. If the user is interacting from the same group chat, they're implicitly a member
    if telegram_chat_id is not None and group.telegram_group_id == telegram_chat_id:
        # Auto-enroll into member_list for future checks
        member_list = group.member_list or []
        if int(user_id) not in [int(m) for m in member_list]:
            group.member_list = [*member_list, int(user_id)]
            await session.flush()
        return True, None

    # 2. If user is a participant in ANY event in this group, they're a proven member
    participant_check = await session.execute(
        select(EventParticipant.event_id)
        .join(Event, EventParticipant.event_id == Event.event_id)
        .where(
            Event.group_id == group_id,
            EventParticipant.telegram_user_id == int(user_id),
        )
        .limit(1)
    )
    if participant_check.scalar_one_or_none() is not None:
        # Auto-enroll into member_list
        member_list = group.member_list or []
        if int(user_id) not in [int(m) for m in member_list]:
            group.member_list = [*member_list, int(user_id)]
            await session.flush()
        return True, None

    # 3. Fallback: check member_list (may not be fully populated)
    member_list = group.member_list or []
    if int(user_id) not in [int(m) for m in member_list]:
        return False, "You are not a member of this group"

    return True, None


async def check_event_visibility_and_get_event(
    session: AsyncSession,
    event_id: int,
    user_id: int,
    telegram_chat_id: Optional[int] = None,
) -> Tuple[bool, Optional["EventType"], Optional["GroupType"], Optional[str]]:
    """
    Check if an event is visible to the user based on group membership.

    Rules:
    - Event organizer can always see the event
    - Event admin can always see the event
    - If user is interacting from the same group chat as the event, they're a member
    - If user has participated in ANY event in this group, they're a member
    - Otherwise, check Group.member_list for explicit membership
    - Non-members cannot see events in the group

    Args:
        session: DB session
        event_id: Event ID to check
        user_id: Telegram user ID
        telegram_chat_id: Optional Telegram chat ID for implicit membership

    Returns:
        (is_visible, event, group, error_message)
    """
    result = await session.execute(
        select(Event, Group)
        .join(Group, Event.group_id == Group.group_id, isouter=True)
        .where(Event.event_id == event_id)
    )
    row = result.one_or_none()

    if not row:
        return False, None, None, "Event not found"

    event, group = row

    # Organizer and admin can always see the event
    if event.organizer_telegram_user_id == user_id:
        return True, event, group, None
    if event.admin_telegram_user_id == user_id:
        return True, event, group, None

    # If event has no group, it's orphaned — deny access
    if not group:
        return False, None, None, "Event not found"

    # 1. If user is interacting from the same group chat as the event, they're a member
    if telegram_chat_id is not None and group.telegram_group_id == telegram_chat_id:
        # Auto-enroll into member_list for future checks
        member_list = group.member_list or []
        if int(user_id) not in [int(m) for m in member_list]:
            group.member_list = [*member_list, int(user_id)]
            await session.flush()
        return True, event, group, None

    # 2. If user has participated in ANY event in this group, they're a proven member
    participant_check = await session.execute(
        select(EventParticipant.event_id)
        .join(Event, EventParticipant.event_id == Event.event_id)
        .where(
            Event.group_id == group.group_id,
            EventParticipant.telegram_user_id == int(user_id),
        )
        .limit(1)
    )
    if participant_check.scalar_one_or_none() is not None:
        # Auto-enroll into member_list
        member_list = group.member_list or []
        if int(user_id) not in [int(m) for m in member_list]:
            group.member_list = [*member_list, int(user_id)]
            await session.flush()
        return True, event, group, None

    # 3. Fallback: check member_list (used for DM access or cross-context)
    member_list = group.member_list or []
    if int(user_id) not in [int(m) for m in member_list]:
        return False, None, None, "You do not have access to this event"

    return True, event, group, None


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
