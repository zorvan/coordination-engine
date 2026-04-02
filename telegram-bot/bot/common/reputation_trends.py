"""Reputation trends and user history tracking."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Event, Log, User


# Default time windows for analysis
TIME_WINDOWS = {
    "week": timedelta(days=7),
    "month": timedelta(days=30),
    "quarter": timedelta(days=90),
    "year": timedelta(days=365),
}


def calculate_reliability_score(
    total_events: int,
    confirmed_events: int,
    last_event_days_ago: float,
    decay_rate: float = 0.05,
) -> float:
    """
    Calculate reliability score based on attendance history.

    Args:
        total_events: Total events user was invited to
        confirmed_events: Events user confirmed attendance for
        last_event_days_ago: Days since last event participation
        decay_rate: Decay rate per day

    Returns:
        Reliability score (0.0 - 1.0)
    """
    if total_events == 0:
        return 0.5  # Neutral score for new users

    # Base score from confirmation rate
    confirmation_rate = confirmed_events / total_events
    base_score = confirmation_rate * 0.7 + 0.3 * 0.5  # 70% weight to confirmation rate

    # Apply decay for inactivity
    decay_factor = ((1 - decay_rate) ** last_event_days_ago)

    return round(max(0.0, min(1.0, base_score * decay_factor)), 3)


async def get_user_reliability_trend(
    session: AsyncSession,
    telegram_user_id: int,
    time_window: str = "month",
) -> Dict[str, Any]:
    """
    Get reliability trend for a user over time.

    Returns trend data including:
    - Total events participated
    - Confirmation rate by period
    - Reliability score history
    """
    window_delta = TIME_WINDOWS.get(time_window, TIME_WINDOWS["month"])
    cutoff_date = datetime.utcnow() - window_delta

    # Get all logs for this user in the time window
    result = await session.execute(
        select(Log).where(
            Log.user_id == telegram_user_id,
            Log.timestamp >= cutoff_date,
        ).order_by(Log.timestamp)
    )
    logs = result.scalars().all()

    # Calculate metrics by period
    period_stats: Dict[str, Dict[str, int]] = {}
    for log in logs:
        period_key = log.timestamp.strftime("%Y-%m-%d")
        if period_key not in period_stats:
            period_stats[period_key] = {"confirmed": 0, "total": 0}

        period_stats[period_key]["total"] += 1
        if log.action in ["confirm", "lock"]:
            period_stats[period_key]["confirmed"] += 1

    # Calculate reliability score history
    score_history: List[Dict[str, Any]] = []
    confirmed_count = 0
    total_count = 0

    for period in sorted(period_stats.keys()):
        stats = period_stats[period]
        confirmed_count += stats["confirmed"]
        total_count += stats["total"]

        score = calculate_reliability_score(
            total_events=total_count,
            confirmed_events=confirmed_count,
            last_event_days_ago=0,  # Current period
        )
        score_history.append({
            "period": period,
            "confirmed": stats["confirmed"],
            "total": stats["total"],
            "score": score,
        })

    # Calculate current reliability score
    last_event_days = (
        (datetime.utcnow() - logs[-1].timestamp).days if logs else 0
    )
    current_score = calculate_reliability_score(
        total_events=total_count,
        confirmed_events=confirmed_count,
        last_event_days_ago=last_event_days,
    )

    return {
        "time_window": time_window,
        "cutoff_date": cutoff_date.isoformat(),
        "total_events": total_count,
        "confirmed_events": confirmed_count,
        "confirmation_rate": confirmed_count / total_count if total_count > 0 else 0,
        "current_score": current_score,
        "score_history": score_history,
        "last_event_days_ago": last_event_days,
    }


async def get_user_attendance_history(
    session: AsyncSession,
    telegram_user_id: int,
    event_type: Optional[str] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """
    Get user's attendance history with optional event type filter.
    """
    query = select(Log).where(Log.user_id == telegram_user_id)

    if event_type:
        # Join with events to filter by event type
        query = query.join(Event, Log.event_id == Event.event_id).where(
            Event.event_type == event_type
        )

    query = query.order_by(desc(Log.timestamp)).limit(limit)
    result = await session.execute(query)
    logs = result.scalars().all()

    history: List[Dict[str, Any]] = []
    for log in logs:
        history.append({
            "event_id": log.event_id,
            "action": log.action,
            "timestamp": log.timestamp.isoformat(),
            "metadata": log.metadata_dict or {},
        })

    return history


async def get_user_reputation_summary(
    session: AsyncSession,
    telegram_user_id: int,
) -> Dict[str, Any]:
    """
    Get comprehensive reputation summary for a user.
    """
    # Get user record
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()

    if not user:
        return {"error": "User not found"}

    # Get global reputation
    reputation = user.reputation or 1.0

    # Get activity-specific reputation
    activity_reputations: Dict[str, float] = {}
    for rep in user.reputation_records or []:
        activity_reputations[rep.activity_type] = rep.score

    # Get reliability trend
    reliability = await get_user_reliability_trend(session, telegram_user_id)

    return {
        "user_id": telegram_user_id,
        "display_name": user.display_name,
        "global_reputation": reputation,
        "activity_reputations": activity_reputations,
        "reliability_trend": reliability,
        "last_updated": datetime.utcnow().isoformat(),
    }


async def get_attendance_summary(
    session: AsyncSession,
    telegram_user_id: int,
    limit: int = 10,
) -> Dict[str, Any]:
    """
    Get summary of user's attendance across different event types.
    """
    # Get logs for this user
    result = await session.execute(
        select(Log).where(Log.user_id == telegram_user_id).order_by(desc(Log.timestamp)).limit(limit)
    )
    logs = result.scalars().all()

    # Count actions by type
    action_counts: Dict[str, int] = {}
    for log in logs:
        action_counts[log.action] = action_counts.get(log.action, 0) + 1

    # Calculate confirmation rate
    total = sum(action_counts.values())
    confirmed = action_counts.get("confirm", 0)
    confirmation_rate = confirmed / total if total > 0 else 0

    return {
        "user_id": telegram_user_id,
        "total_interactions": total,
        "action_breakdown": action_counts,
        "confirmation_rate": round(confirmation_rate, 3),
        "recent_logs": [
            {"action": log.action, "timestamp": log.timestamp.isoformat()}
            for log in logs[:5]
        ],
    }
