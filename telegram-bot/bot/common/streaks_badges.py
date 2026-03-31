"""Streaks and badges system for reliable participation."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Log


STREAK_DAYS_BRONZE = 7
STREAK_DAYS_SILVER = 30
STREAK_DAYS_GOLD = 90

BADGES = {
    "first_event": {
        "id": "first_event",
        "name": "First Step",
        "description": "Attended your first event",
        "icon": "🌟",
    },
    "confirmed_attendee": {
        "id": "confirmed_attendee",
        "name": "Confirmed",
        "description": "Confirmed attendance multiple times",
        "icon": "✅",
    },
    "reliable_7": {
        "id": "reliable_7",
        "name": "Bronze Streak",
        "description": "7-day attendance streak",
        "icon": "🥉",
    },
    "reliable_30": {
        "id": "reliable_30",
        "name": "Silver Streak",
        "description": "30-day attendance streak",
        "icon": "🥈",
    },
    "reliable_90": {
        "id": "reliable_90",
        "name": "Gold Streak",
        "description": "90-day attendance streak",
        "icon": "🥇",
    },
    "social_butterfly": {
        "id": "social_butterfly",
        "name": "Social Butterfly",
        "description": "Attended events in multiple groups",
        "icon": "🦋",
    },
    "event_organizer": {
        "id": "event_organizer",
        "name": "Event Organizer",
        "description": "Organized your first event",
        "icon": "👑",
    },
}


def get_badge_for_streak(days: int) -> Optional[Dict[str, str]]:
    """Get badge for current streak length."""
    if days >= STREAK_DAYS_GOLD:
        return BADGES["reliable_90"]
    elif days >= STREAK_DAYS_SILVER:
        return BADGES["reliable_30"]
    elif days >= STREAK_DAYS_BRONZE:
        return BADGES["reliable_7"]
    return None


def calculate_streak(logs: List[Log]) -> int:
    """Calculate current attendance streak from logs."""
    if not logs:
        return 0

    action_dates = set()
    for log in logs:
        if log.action in ["confirm", "join"]:
            action_dates.add(log.timestamp.date())

    if not action_dates:
        return 0

    sorted_dates = sorted(action_dates, reverse=True)

    current_streak = 0
    today = datetime.today().date()

    if sorted_dates[0] not in [today, today - timedelta(days=1)]:
        return 0

    for i, date_item in enumerate(sorted_dates):
        if i == 0:
            current_streak = 1
        else:
            diff = (sorted_dates[i - 1] - date_item).days
            if diff == 1:
                current_streak += 1
            elif diff > 1:
                break

    return current_streak


async def get_user_streak(
    session: AsyncSession,
    user_id: int,
) -> int:
    """Get current streak for a user."""
    from db.models import Log

    result = await session.execute(
        select(Log).where(Log.user_id == user_id)
    )
    logs_list = result.scalars().all()

    return calculate_streak(logs_list)  # type: ignore[arg-type]


async def award_badges(
    session: AsyncSession,
    user_id: int,
) -> List[Dict[str, Any]]:
    """Award badges to user based on their actions."""
    awarded = []
    streak = await get_user_streak(session, user_id)

    if streak >= STREAK_DAYS_GOLD:
        awarded.append(BADGES["reliable_90"])
    elif streak >= STREAK_DAYS_SILVER:
        awarded.append(BADGES["reliable_30"])
    elif streak >= STREAK_DAYS_BRONZE:
        awarded.append(BADGES["reliable_7"])

    return awarded


async def get_user_badges(session: AsyncSession, user_id: int) -> List[Dict[str, Any]]:
    """Get all badges earned by a user."""
    badges_earned = []

    # Check for first event badge
    result = await session.execute(
        select(Log).where(Log.user_id == user_id).limit(1)
    )
    if result.scalar_one_or_none():
        badges_earned.append(BADGES["first_event"])

    # Check for confirmed attendee badge
    result = await session.execute(
        select(Log).where(Log.user_id == user_id, Log.action == "confirm").limit(3)
    )
    confirmations = result.scalars().all()
    if len(confirmations) >= 3:
        badges_earned.append(BADGES["confirmed_attendee"])

    # Check for streak badges
    streak = await get_user_streak(session, user_id)
    if streak >= STREAK_DAYS_BRONZE:
        badge = get_badge_for_streak(streak)
        if badge:
            badges_earned.append(badge)

    return badges_earned


def format_badge_display(badges: List[Dict[str, Any]]) -> str:
    """Format badges for display."""
    if not badges:
        return "No badges earned yet"

    return "\n".join(
        f"{badge['icon']} **{badge['name']}**: {badge['description']}"
        for badge in badges
    )