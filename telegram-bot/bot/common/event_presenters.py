"""Shared event presentation helpers."""
from typing import Any

from sqlalchemy import select

from bot.common.event_states import STATE_EXPLANATIONS
from bot.common.attendance import parse_attendance_with_status
from db.models import User
from db.connection import get_session
from config.settings import settings


async def get_user_mention(session, telegram_user_id: int, bot=None) -> str:
    """
    Get a clickable @username mention for a user.

    Fetches user from database first, then from Telegram API if needed:
    - @username (clickable) if username exists
    - display_name (clickable) if display_name exists
    - User ID link as last fallback

    Args:
        session: Database session
        telegram_user_id: User's Telegram ID
        bot: Telegram bot instance to fetch user info from API

    Returns:
        Formatted mention string
    """
    user = (
        await session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
    ).scalar_one_or_none()

    username = None
    display_name = None

    if user:
        username = getattr(user, "username", None)
        display_name = getattr(user, "display_name", None)

    # If no username in DB and bot is available, fetch from Telegram API
    if not username and bot:
        try:
            tg_user = await bot.get_chat(telegram_user_id)
            if tg_user:
                username = getattr(tg_user, "username", None)
                if not username:
                    # Try first_name + last_name
                    first_name = getattr(tg_user, "first_name", "")
                    last_name = getattr(tg_user, "last_name", "")
                    display_name = f"{first_name} {last_name}".strip() or None

                # Update database with fetched username
                if user and username:
                    user.username = username.lower()
                    await session.flush()
                elif not user:
                    # Create user record
                    from db.models import User as UserModel
                    new_user = UserModel(
                        telegram_user_id=telegram_user_id,
                        username=username.lower() if username else None,
                        display_name=display_name,
                    )
                    session.add(new_user)
                    await session.flush()
        except Exception:
            pass  # User might have privacy settings blocking this

    if username:
        return f"{display_name or username}(@{username})"
    elif display_name:
        return display_name

    # Fallback to User ID
    return f"User{telegram_user_id}"


async def get_user_mention_with_bot(session, telegram_user_id: int, bot) -> str:
    """
    Get user mention with guaranteed Telegram API lookup.
    Wrapper that ensures bot is passed for API lookup.
    """
    return await get_user_mention(session, telegram_user_id, bot=bot)


def format_user_display(
    telegram_user_id: int,
    username: str | None = None,
    display_name: str | None = None,
    include_link: bool = False,  # Deprecated parameter, kept for compatibility
) -> str:
    """Format user display with fallback hierarchy: Name(@username) → @username → display_name → User ID.

    Args:
        telegram_user_id: User's Telegram ID
        username: User's @username if available
        display_name: User's display name if available
        include_link: Deprecated - no longer used (Markdown links removed)

    Returns:
        Formatted user display string: "Name(@username)" or "@username" or "display_name"
    """
    if username:
        # Format: Name(@username) or just @username if no display name
        if display_name:
            return f"{display_name}(@{username})"
        return f"@{username}"
    elif display_name:
        return display_name
    else:
        # Fallback to User ID
        return f"User{telegram_user_id}"


def summarize_description(description: str | None, max_len: int = 400) -> str:
    """Normalize and truncate event description for messages."""
    text = (description or "No description provided").strip()
    if len(text) > max_len:
        return f"{text[:max_len - 3]}..."
    return text


async def attendance_stats_with_usernames(
    attendance: list[Any] | None, session, event_id: int = None
) -> tuple[int, int, str]:
    """
    Return interested count, confirmed count, and formatted attendee text with usernames.

    Reads from event_participants table for accurate status.
    Format: "Name(@username) has confirmed"
    """
    from db.models import EventParticipant, ParticipantStatus

    if not event_id:
        # Fallback to old method (legacy attendance_list)
        status_by_user = parse_attendance_with_status(attendance)
    else:
        # Read from participant table (current system)
        result = await session.execute(
            select(EventParticipant).where(EventParticipant.event_id == event_id)
        )
        participants = result.scalars().all()
        status_by_user = {
            p.telegram_user_id: p.status.value for p in participants
        }

    # Count statuses (new system uses 'joined' and 'confirmed')
    interested_count = sum(
        1 for status in status_by_user.values() if status == "joined"
    )
    confirmed_count = sum(
        1 for status in status_by_user.values() if status == "confirmed"
    )

    if not status_by_user:
        return interested_count, confirmed_count, "No attendees yet."

    lines = []
    user_ids = list(status_by_user.keys())

    users = {}
    if user_ids:
        result = await session.execute(
            select(User).where(User.telegram_user_id.in_(user_ids))
        )
        for user in result.scalars().all():
            users[user.telegram_user_id] = user

    for telegram_user_id in sorted(status_by_user.keys()):
        status = status_by_user[telegram_user_id]
        user = users.get(telegram_user_id)
        username = getattr(user, "username", None) if user else None
        display_name = getattr(user, "display_name", None) if user else None

        # Format: "Name(@username) has confirmed"
        if display_name and username:
            user_display = f"{display_name}(@{username})"
        elif username:
            user_display = f"@{username}"
        elif display_name:
            user_display = display_name
        else:
            user_display = f"User{telegram_user_id}"

        # Map status to readable text with "has" verb
        status_text = {
            "joined": "has joined",
            "confirmed": "has confirmed",
            "cancelled": "has cancelled",
            "no_show": "was absent",
        }.get(status, status)

        lines.append(f"{user_display} {status_text}")

    return interested_count, confirmed_count, "\n".join(lines)


def attendance_stats(attendance: list[Any] | None) -> tuple[int, int, str]:
    """Return interested count, confirmed count, and formatted attendee text (legacy function)."""
    status_by_user = parse_attendance_with_status(attendance)
    # Legacy system: 'interested' = joined, 'confirmed' = confirmed (committed is mapped to confirmed)
    interested_count = sum(
        1 for status in status_by_user.values() if status == "interested"
    )
    confirmed_count = sum(
        1 for status in status_by_user.values() if status == "confirmed"
    )

    if not status_by_user:
        return interested_count, confirmed_count, "No attendees yet."

    lines = []
    user_ids = list(status_by_user.keys())
    
    # Fetch user data for formatting
    from db.models import User
    from db.connection import get_session
    from config.settings import settings
    
    users = {}
    if user_ids and settings.db_url:
        import asyncio
        async def fetch_users():
            async with get_session(settings.db_url) as session:
                result = await session.execute(
                    select(User).where(User.telegram_user_id.in_(user_ids))
                )
                for user in result.scalars().all():
                    users[user.telegram_user_id] = user
        try:
            asyncio.get_event_loop().run_until_complete(fetch_users())
        except Exception:
            pass

    for telegram_user_id in sorted(status_by_user.keys()):
        status = status_by_user[telegram_user_id]
        user = users.get(telegram_user_id)
        username = getattr(user, "username", None) if user else None
        display_name = getattr(user, "display_name", None) if user else None
        
        # Format: "Name(@username) has confirmed"
        if display_name and username:
            user_display = f"{display_name}(@{username})"
        elif username:
            user_display = f"@{username}"
        elif display_name:
            user_display = display_name
        else:
            user_display = f"User{telegram_user_id}"
        
        status_text = {
            "invited": "has been invited",
            "interested": "has joined",
            "confirmed": "has confirmed",
            "committed": "has confirmed",  # Legacy mapping
        }.get(status, status)
        
        lines.append(f"{user_display} {status_text}")
    return interested_count, confirmed_count, "\n".join(lines)


async def format_event_details_message(
    event_id: int, event: Any, logs: list[Any], constraints: list[Any], bot=None
) -> str:
    """Build consistent detailed event info with early-stage progress."""
    attendance = event.attendance_list or []
    
    if settings.db_url:
        async with get_session(settings.db_url) as session:
            interested_count, confirmed_count, attendees_text = await attendance_stats_with_usernames(attendance, session, event_id)
    else:
        interested_count, confirmed_count, attendees_text = attendance_stats(attendance)
    threshold = event.threshold_attendance or 0
    needed = max(threshold - confirmed_count, 0)
    availability_count = sum(
        1 for c in constraints if str(getattr(c, "type", "")).startswith("available:")
    )
    planning_prefs = (
        event.planning_prefs
        if isinstance(getattr(event, "planning_prefs", None), dict)
        else {}
    )
    location_type = str(planning_prefs.get("location_type", "n/a")).replace("_", " ")
    budget_level = str(planning_prefs.get("budget_level", "n/a")).replace("_", " ")
    transport_mode = str(planning_prefs.get("transport_mode", "n/a")).replace("_", " ")
    time_window = str(planning_prefs.get("time_window", "n/a"))
    date_preset = str(planning_prefs.get("date_preset", "n/a"))

    next_step = "Run /join <event_id> to gather interest."
    if event.scheduled_time is None:
        next_step = (
            "No time selected yet. Collect availability via "
            f"/constraints {event_id} availability <YYYY-MM-DD HH:MM, ...> "
            f"then run /suggest_time {event_id}."
        )
    elif event.state == "interested":
        next_step = "Members should run /confirm <event_id>."
    elif event.state == "confirmed":
        next_step = "Organizer can lock the event when ready."
    elif event.state in {"locked", "completed", "cancelled"}:
        next_step = "Event is in a terminal/locked stage."

    # Get admin mention
    admin_id = getattr(event, "admin_telegram_user_id", None)
    admin_text = "N/A"
    if admin_id and settings.db_url:
        async with get_session(settings.db_url) as session:
            admin_text = await get_user_mention(session, int(admin_id), bot=bot)

    return (
        f"📋 *Event {event_id} Details*\n\n"
        f"Type: {event.event_type}\n"
        f"Description: {event.description or 'N/A'}\n"
        f"Time: {event.scheduled_time or 'TBD'}\n"
        f"Commit-By: {event.commit_by or 'N/A'}\n"
        f"Date Preset: {date_preset}\n"
        f"Time Window: {time_window}\n"
        f"Location Type: {location_type}\n"
        f"Budget: {budget_level}\n"
        f"Transport: {transport_mode}\n"
        f"Duration: {event.duration_minutes or 120} minutes\n"
        f"Threshold: {threshold}\n"
        f"State: {event.state}\n"
        f"State Meaning: {STATE_EXPLANATIONS.get(event.state, 'Unknown state')}\n"
        f"AI Score: {event.ai_score:.2f}\n"
        f"Created: {event.created_at}\n"
        f"Locked: {event.locked_at or 'N/A'}\n"
        f"Completed: {event.completed_at or 'N/A'}\n\n"
        f"Admin: {admin_text}\n\n"
        f"Progress:\n"
        f"- Interested: {interested_count}\n"
        f"- Confirmed: {confirmed_count}\n"
        f"- Needed to reach threshold: {needed}\n"
        f"- Availability slots: {availability_count}\n\n"
        f"Attendees ({len(attendance)}):\n{attendees_text}\n\n"
        f"Logs: {len(logs)}\n"
        f"Constraints: {len(constraints)}\n\n"
        f"Next step: {next_step}"
    )


async def format_status_message(
    event_id: int,
    event: Any,
    log_count: int,
    constraint_count: int,
    bot=None,
    user_participant=None,
    session=None,
) -> str:
    """
    Build consistent event status message with mutual dependence visibility.

    PRD v2 Section 2.2.3: Visibility of Mutual Dependence
    - Shows who else is in (confirmed names, interested names)
    - Shows threshold progress and fragility
    - User-specific acknowledgment: "You are one of [N] people [Name] is counting on"
    """
    description = summarize_description(event.description, max_len=400)
    planning_prefs = (
        event.planning_prefs
        if isinstance(getattr(event, "planning_prefs", None), dict)
        else {}
    )
    location_type = str(planning_prefs.get("location_type", "n/a")).replace("_", " ")
    budget_level = str(planning_prefs.get("budget_level", "n/a")).replace("_", " ")
    transport_mode = str(planning_prefs.get("transport_mode", "n/a")).replace("_", " ")
    time_window = str(planning_prefs.get("time_window", "n/a"))
    date_preset = str(planning_prefs.get("date_preset", "n/a"))

    # Get participant counts with names (PRD v2: Visibility of Mutual Dependence)
    min_participants = event.min_participants or 2
    threshold = event.threshold_attendance or min_participants
    confirmed_count = 0
    interested_count = 0
    confirmed_names = []
    interested_names = []

    if session and settings.db_url:
        from db.models import EventParticipant, ParticipantStatus
        from sqlalchemy import select

        result = await session.execute(
            select(EventParticipant, User)
            .join(User, EventParticipant.telegram_user_id == User.telegram_user_id, isouter=True)
            .where(EventParticipant.event_id == event_id)
        )

        for participant, user in result.all():
            user_display = format_user_display(
                telegram_user_id=participant.telegram_user_id,
                username=getattr(user, 'username', None),
                display_name=getattr(user, 'display_name', None),
            )

            if participant.status == ParticipantStatus.confirmed:
                confirmed_count += 1
                confirmed_names.append(user_display)
            elif participant.status == ParticipantStatus.joined:
                interested_count += 1
                interested_names.append(user_display)

    # Threshold fragility display (PRD v2 Section 2.2.1)
    needed = max(threshold - confirmed_count, 0)
    fragility_text = ""
    if needed > 0:
        fragility_text = f"\n⚠️ We need {needed} more to reach threshold ({confirmed_count}/{threshold})"
        if needed == 1:
            fragility_text += "\n❗ If one more person drops, this event collapses."
    elif confirmed_count >= threshold:
        fragility_text = f"\n✅ Threshold reached! ({confirmed_count}/{threshold})"

    # User-specific mutual dependence acknowledgment (PRD v2 Section 2.2.3)
    mutual_dependence_text = ""
    if user_participant and session:
        total_count = confirmed_count + interested_count
        if total_count > 1:
            # Find who the user might be counting on (other participants)
            others_count = total_count - 1
            if user_participant.status == ParticipantStatus.confirmed:
                mutual_dependence_text = (
                    f"\n\n🤝 You are one of {total_count} people others are counting on.\n"
                    f"   {others_count} participant{'s' if others_count > 1 else ''} depending on you."
                )
            elif user_participant.status == ParticipantStatus.joined:
                mutual_dependence_text = (
                    f"\n\n🤝 You are one of {total_count} interested participants.\n"
                    f"   Confirm to let others know you're committed."
                )

    # Get admin mention
    admin_id = getattr(event, "admin_telegram_user_id", None)
    admin_text = "N/A"
    if admin_id and settings.db_url:
        async with get_session(settings.db_url) as session:
            admin_text = await get_user_mention(session, int(admin_id), bot=bot)

    # Build participant lists
    participant_text = ""
    if confirmed_names:
        participant_text += f"\n✅ Confirmed ({confirmed_count}): {', '.join(confirmed_names)}"
    if interested_names:
        participant_text += f"\n👀 Interested ({interested_count}): {', '.join(interested_names)}"
    if not participant_text:
        participant_text = "\nNo participants yet."

    return (
        f"📊 *Event {event_id} Status*\n\n"
        f"Type: {event.event_type}\n"
        f"Description: {description}\n"
        f"Time: {event.scheduled_time or 'TBD'}\n"
        f"Threshold: {threshold}\n"
        f"State: {event.state}\n"
        f"{fragility_text}"
        f"{mutual_dependence_text}\n\n"
        f"Participants:{participant_text}\n\n"
        f"Admin: {admin_text}\n"
        f"Logs: {log_count} | Constraints: {constraint_count}"
    )
