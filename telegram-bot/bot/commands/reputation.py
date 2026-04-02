#!/usr/bin/env python3
"""Reputation command handler.

PRD v2 Updates (TODO-033):
- Show personal trend over time (not leaderboard)
- No score comparison with others
- Display reliability signals and event history
"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select, func

from config.settings import settings
from db.connection import get_session
from db.models import User, Reputation, EventParticipant, ParticipantStatus, Event

logger = logging.getLogger("coord_bot.commands.reputation")


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle /reputation command - show personal reputation trend.

    PRD v2 Design rule:
    - Personal trend, not leaderboard
    - No comparative scoring
    - Show reliability signals and participation history
    """
    if not update.message:
        return

    if not settings.db_url:
        await update.message.reply_text("❌ Database configuration is unavailable.")
        return

    user_id = update.effective_user.id if update.effective_user else None
    if not user_id:
        return

    async with get_session(settings.db_url) as session:
        # Get user
        result = await session.execute(
            select(User).where(User.telegram_user_id == user_id)
        )
        user = result.scalar_one_or_none()

        if not user:
            await update.message.reply_text(
                "You're not registered yet.\n"
                "Use /start to register."
            )
            return

        # Get overall reputation
        overall_rep = user.reputation or 1.0

        # Get activity-specific reputation
        rep_result = await session.execute(
            select(Reputation)
            .where(Reputation.user_id == user.user_id)
            .order_by(Reputation.activity_type)
        )
        activity_reps = rep_result.scalars().all()

        # Get participation stats
        participation_stats = await _get_participation_stats(session, user.user_id)

        # Get recent trend (last 30 days)
        trend_data = await _get_reputation_trend(session, user.user_id, days=30)

        # Build response
        response_parts = [
            "⭐ <b>Your Reputation</b>\n",
            f"Overall: <b>{overall_rep:.1f}/5.0</b>\n",
        ]

        # Activity-specific scores
        if activity_reps:
            response_parts.append("<b>By Activity:</b>")
            for rep in activity_reps:
                response_parts.append(
                    f"• {rep.activity_type.title()}: {rep.score:.1f}"
                )
            response_parts.append("")

        # Participation stats
        if participation_stats:
            response_parts.append("<b>Participation:</b>")
            response_parts.append(
                f"• Events attended: {participation_stats.get('total_events', 0)}"
            )
            response_parts.append(
                f"• Confirmed: {participation_stats.get('confirmed', 0)}"
            )
            response_parts.append(
                f"• No-shows: {participation_stats.get('no_shows', 0)}"
            )
            if participation_stats.get('reliability_rate'):
                response_parts.append(
                    f"• Reliability: {participation_stats['reliability_rate']:.0f}%"
                )
            response_parts.append("")

        # Trend indicator
        if trend_data and len(trend_data) > 1:
            first_score = trend_data[0].get('score', overall_rep)
            last_score = trend_data[-1].get('score', overall_rep)
            change = last_score - first_score

            if change > 0.1:
                trend_indicator = "📈 trending up"
            elif change < -0.1:
                trend_indicator = "📉 trending down"
            else:
                trend_indicator = "➡️ stable"

            response_parts.append(f"<b>30-day trend:</b> {trend_indicator}")
        else:
            response_parts.append("<b>Trend:</b> Not enough data yet")

        # Footer
        response_parts.append(
            "\n_Reputation is personal — never shown as leaderboard_"
        )

        response = "\n".join(response_parts)

        await update.message.reply_text(response, parse_mode="HTML")

        logger.info(
            "User viewed reputation",
            extra={"user": user.user_id, "reputation": overall_rep}
        )


async def _get_participation_stats(
    session,
    user_id: int,
) -> Dict[str, Any]:
    """Get user's participation statistics."""
    # Total events
    total_result = await session.execute(
        select(func.count(func.distinct(EventParticipant.event_id)))
        .where(EventParticipant.telegram_user_id == user_id)
    )
    total_events = total_result.scalar() or 0

    # Confirmed count
    confirmed_result = await session.execute(
        select(func.count(EventParticipant.event_id))
        .where(
            EventParticipant.telegram_user_id == user_id,
            EventParticipant.status == ParticipantStatus.confirmed,
        )
    )
    confirmed = confirmed_result.scalar() or 0

    # No-show count
    no_show_result = await session.execute(
        select(func.count(EventParticipant.event_id))
        .where(
            EventParticipant.telegram_user_id == user_id,
            EventParticipant.status == ParticipantStatus.no_show,
        )
    )
    no_shows = no_show_result.scalar() or 0

    # Reliability rate
    reliability_rate = 0.0
    if total_events > 0:
        reliability_rate = (confirmed / total_events) * 100

    return {
        "total_events": total_events,
        "confirmed": confirmed,
        "no_shows": no_shows,
        "reliability_rate": reliability_rate,
    }


async def _get_reputation_trend(
    session,
    user_id: int,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """
    Get reputation trend over last N days.

    Returns list of {date, score} dicts.
    """
    # For now, return simplified trend based on recent events
    # In future, this could query a reputation_history table

    cutoff = datetime.utcnow() - timedelta(days=days)

    # Get recent event participations
    result = await session.execute(
        select(Event, EventParticipant)
        .join(EventParticipant, Event.event_id == EventParticipant.event_id)
        .where(
            EventParticipant.telegram_user_id == user_id,
            Event.completed_at >= cutoff,
        )
        .order_by(Event.completed_at)
    )

    trend_data = []
    for event, participant in result.all():
        # Simplified: use participant status as proxy for reputation impact
        if participant.status == ParticipantStatus.confirmed:
            score_impact = 0.1
        elif participant.status == ParticipantStatus.no_show:
            score_impact = -0.2
        else:
            score_impact = 0.0

        trend_data.append({
            "date": event.completed_at,
            "score_impact": score_impact,
            "event_type": event.event_type,
        })

    return trend_data
