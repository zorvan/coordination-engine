"""Post-event engagement loop utilities."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.models import Event, User


async def get_event_summary(
    session: AsyncSession,
    event_id: int,
) -> Dict[str, Any]:
    """Generate an auto-post event summary after completion."""
    result = await session.execute(
        select(Event).where(Event.event_id == event_id)
    )
    event = result.scalar_one_or_none()
    if not event:
        return {"error": "Event not found"}
    
    summary = {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "scheduled_time": event.scheduled_time.isoformat() if event.scheduled_time else None,
        "duration_minutes": event.duration_minutes,
        "state": event.state,
        "completed_at": event.completed_at.isoformat() if event.completed_at else None,
        "organizer": None,
        "attendees": [],
        "completion_status": "unknown",
        "stats": {
            "total_invited": 0,
            "joined": 0,
            "confirmed": 0,
            "cancelled": 0,
            "commitment_rate": 0.0,
        },
        "highlights": [],
    }
    
    attendance_list = event.attendance_list or []
    
    def get_user_id(a):
        if isinstance(a, dict):
            return a.get("user_id")
        elif isinstance(a, (int, float)):
            return int(a)
        return None
    
    telegram_ids = [get_user_id(a) for a in attendance_list]
    telegram_ids = [t for t in telegram_ids if t]
    
    if telegram_ids:
        result = await session.execute(
            select(User).where(User.telegram_user_id.in_(telegram_ids))
        )
        users = result.scalars().all()
        user_map = {u.telegram_user_id: u for u in users}
        
        summary["attendees"] = [
            {
                "telegram_user_id": t_id,
                "display_name": user_map.get(t_id, User(telegram_user_id=t_id)).display_name or "Unknown",
                "joined": True,
            }
            for t_id in telegram_ids
        ]
    
    if event.organizer_telegram_user_id:
        result = await session.execute(
            select(User).where(User.telegram_user_id == event.organizer_telegram_user_id)
        )
        organizer = result.scalar_one_or_none()
        if organizer:
            summary["organizer"] = {
                "telegram_user_id": event.organizer_telegram_user_id,
                "display_name": organizer.display_name or "Unknown",
            }
    
    summary["stats"]["total_invited"] = len(telegram_ids)
    summary["stats"]["joined"] = len(telegram_ids)
    
    confirmed_count = 0
    for attendee in attendance_list:
        if isinstance(attendee, dict):
            if attendee.get("status") == "confirmed":
                confirmed_count += 1
        elif isinstance(attendee, (int, float)):
            confirmed_count += 1
    
    summary["stats"]["confirmed"] = confirmed_count
    summary["stats"]["commitment_rate"] = (
        confirmed_count / len(telegram_ids) if telegram_ids else 0
    )
    
    summary["stats"]["cancelled"] = summary["stats"]["total_invited"] - summary["stats"]["confirmed"]
    
    if event.state == "completed":
        summary["completion_status"] = "completed_successfully"
    elif event.state == "cancelled":
        summary["completion_status"] = "cancelled"
    elif event.state in ["locked", "confirmed"]:
        summary["completion_status"] = "completed_without_feedback"
    
    if summary["stats"]["commitment_rate"] >= 0.8:
        summary["highlights"].append("⭐ High commitment rate - great coordination!")
    if summary["stats"]["confirmed"] >= 5:
        summary["highlights"].append("👥 Large group turnout!")
    
    return summary


async def post_event_summary(
    session: AsyncSession,
    event_id: int,
    group_telegram_id: int,
    chat_id: int,
) -> Dict[str, Any]:
    """Post event summary to group chat after completion."""
    summary = await get_event_summary(session, event_id)
    
    if "error" in summary:
        return summary
    
    lines = [
        "📋 *Event Summary*",
        "",
        f"*{summary['event_type']}* (#{summary['event_id']})",
        f"Time: {summary['scheduled_time']}",
        f"Duration: {summary['duration_minutes']} minutes",
        "",
        f"Status: {summary['completion_status'].replace('_', ' ').title()}",
        "",
        "📊 *Attendance Stats*:",
        f"  🎯 Committed: {summary['stats']['confirmed']}/{summary['stats']['total_invited']}",
        f"  ✅ Commitment rate: {summary['stats']['commitment_rate']*100:.0f}%",
        "",
    ]
    
    if summary.get("organizer"):
        lines.append(f"👤 Organized by: {summary['organizer']['display_name']}")
    
    if summary.get("attendees"):
        lines.append("")
        lines.append("👥 Attendees:")
        for attendee in summary["attendees"][:10]:
            lines.append(f"  • {attendee['display_name']}")
        if len(summary["attendees"]) > 10:
            lines.append(f"  ... and {len(summary['attendees']) - 10} more")
    
    if summary.get("highlights"):
        lines.append("")
        lines.append("✨ Highlights:")
        for highlight in summary["highlights"]:
            lines.append(f"  {highlight}")
    
    return {
        "message": "\n".join(lines),
        "event_summary": summary,
    }


async def create_feedback_prompt(
    event_id: int,
    event_type: str,
    scheduled_time: Optional[datetime],
) -> Dict[str, Any]:
    """Create one-tap lightweight feedback prompt for attendees."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    keyboard = [
        [
            InlineKeyboardButton("⭐ 5 - Perfect!", callback_data=f"feedback_{event_id}_5"),
            InlineKeyboardButton("⭐ 4 - Good", callback_data=f"feedback_{event_id}_4"),
        ],
        [
            InlineKeyboardButton("⭐ 3 - Okay", callback_data=f"feedback_{event_id}_3"),
            InlineKeyboardButton("⭐ 2 - Could be better", callback_data=f"feedback_{event_id}_2"),
        ],
        [
            InlineKeyboardButton("⭐ 1 - Poor", callback_data=f"feedback_{event_id}_1"),
        ],
        [
            InlineKeyboardButton("💬 Add comment", callback_data=f"feedback_{event_id}_comment"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    scheduled_str = scheduled_time.strftime("%Y-%m-%d %H:%M") if scheduled_time else "TBD"
    
    return {
        "message": (
            f"👋 *Thanks for attending {event_type}!*\n\n"
            f"Event: {scheduled_str}\n\n"
            "Please rate your experience:"
        ),
        "reply_markup": reply_markup,
        "event_id": event_id,
    }


async def create_schedule_next_prompt(
    event_id: int,
    event_type: str,
    scheduled_time: Optional[datetime],
    attendance_list: List[Any],
) -> Dict[str, Any]:
    """Create 'schedule next one?' prompt after event completion."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    telegram_ids = []
    for a in attendance_list or []:
        if isinstance(a, dict):
            telegram_ids.append(a.get("user_id"))
        elif isinstance(a, (int, float)):
            telegram_ids.append(int(a))
    
    telegram_ids = [t for t in telegram_ids if t]
    total_attendees = len(telegram_ids)
    
    keyboard = [
        [
            InlineKeyboardButton("📅 Schedule next one!", callback_data=f"schedule_next_{event_id}"),
        ],
        [
            InlineKeyboardButton("💡 Suggest time", callback_data=f"suggest_time_next_{event_id}"),
        ],
        [
            InlineKeyboardButton("📍 Suggest location", callback_data=f"suggest_location_next_{event_id}"),
        ],
        [
            InlineKeyboardButton("🔄 Reuse defaults", callback_data=f"reuse_defaults_{event_id}"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    scheduled_str = scheduled_time.strftime("%Y-%m-%d %H:%M") if scheduled_time else "TBD"
    
    return {
        "message": (
            f"✨ *{event_type} completed successfully!*\n\n"
            f" attendees ({total_attendees} people)\n"
            f"Scheduled: {scheduled_str}\n\n"
            "What's next?"
        ),
        "reply_markup": reply_markup,
        "event_id": event_id,
        "attendees": telegram_ids,
    }


async def create_attendee_followup(
    event_id: int,
    event_type: str,
    scheduled_time: Optional[datetime],
    attendance_list: List[Any],
) -> Dict[str, Any]:
    """Create attendee follow-up suggestions."""
    telegram_ids = []
    for a in attendance_list or []:
        if isinstance(a, dict):
            telegram_ids.append(a.get("user_id"))
        elif isinstance(a, (int, float)):
            telegram_ids.append(int(a))
    
    telegram_ids = [t for t in telegram_ids if t]
    
    return {
        "message": (
            f"📝 *Feedback needed for {event_type}* ({len(telegram_ids)} attendees)\n\n"
            "Improvement suggestions for future events:"
        ),
        "attendees": telegram_ids,
    }


def generate_suggestions_for_event(
    event: Event,
    user_preferences: Optional[Dict[str, Any]] = None,
) -> List[str]:
    """Generate time/place improvement suggestions based on event data."""
    suggestions = []
    
    if event.scheduled_time:
        hour = event.scheduled_time.hour
        if hour < 9:
            suggestions.append("Consider mornings - attendance might be low")
        elif 12 <= hour <= 14:
            suggestions.append("Lunchtime could work well for quick meetups")
        elif hour > 18:
            suggestions.append("Evening events are popular for after-work gatherings")
    
    if event.event_type:
        if "dining" in event.event_type.lower() or "food" in event.event_type.lower():
            suggestions.append("Suggest restaurants with good reviews")
        elif "sports" in event.event_type.lower():
            suggestions.append("Check sports facilities availability")
        elif "movie" in event.event_type.lower():
            suggestions.append("Cinema with good sound system preferred")
    
    return suggestions


async def create_reactivation_prompt(
    group_telegram_id: int,
    days_inactive: int,
) -> Dict[str, Any]:
    """Create reactivation nudge for inactive groups."""
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
    
    if days_inactive > 30:
        message = (
            f"👋 *We miss you!* 🌟\n\n"
            f"It's been {days_inactive} days since your last event.\n\n"
            "Ready to reconnect with your group?"
        )
    elif days_inactive > 14:
        message = (
            f"👋 *Long time no see!* 📅\n\n"
            f"Your group hasn't scheduled an event in {days_inactive} days.\n\n"
            "Time to plan something fun?"
        )
    else:
        message = (
            f"👋 *Hello there!* 👋\n\n"
            f"Your group has been quiet for {days_inactive} days.\n\n"
            "Want to schedule an event soon?"
        )
    
    keyboard = [
        [
            InlineKeyboardButton("📅 Schedule event now", callback_data="reactivate_schedule"),
        ],
        [
            InlineKeyboardButton("💡 Event ideas", callback_data="reactivate_ideas"),
        ],
        [
            InlineKeyboardButton("👻 Maybe later", callback_data="reactivate_later"),
        ],
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    return {
        "message": message,
        "reply_markup": reply_markup,
        "days_inactive": days_inactive,
    }