"""Message presenters — format domain data for Telegram display."""

from __future__ import annotations

from datetime import datetime

from coordination_engine.application.dto import EventDTO, ParticipantDTO
from bot.common.event_formatters import (
    format_date_preset,
    format_time_window,
    format_location_type,
    format_budget_level,
    format_transport_mode,
    format_scheduled_time,
    format_commit_by,
    format_duration,
)


def format_event_card(event: EventDTO, include_stats: bool = True) -> str:
    """Format an event as a compact card for inline display."""
    status_emoji = {
        "proposed": "🌱",
        "interested": "💭",
        "confirmed": "✅",
        "locked": "🔒",
        "completed": "🎉",
        "cancelled": "❌",
    }.get(event.state, "❓")

    time_display = format_scheduled_time(event.scheduled_time, include_flexible_note=False)

    lines = [
        f"{status_emoji} *Event #{event.event_id}* — {event.event_type.upper()}",
        f"📝 {event.description[:120]}{'...' if len(event.description) > 120 else ''}",
        f"📅 {time_display}",
        f"⏱ {format_duration(event.duration_minutes)}",
        f"📍 {format_location_type(event.planning_prefs.get('location_type'))}",
        f"👥 {event.participant_count} joined / {event.confirmed_count} confirmed",
        f"🎯 Threshold: {event.threshold_attendance}",
    ]

    if include_stats:
        lines.append(f"🔢 State: {event.state}")

    return "\n".join(lines)


def format_event_details(event: EventDTO) -> str:
    """Format full event details for /event_details."""
    time_display = format_scheduled_time(event.scheduled_time)
    
    prefs = event.planning_prefs or {}
    commit_display = format_commit_by(event.commit_by)

    return (
        f"📋 *Event #{event.event_id}*\n\n"
        f"State: {event.state}\n"
        f"Type: {event.event_type}\n"
        f"Description: {event.description}\n\n"
        f"📅 Time: {time_display}\n"
        f"⏱ Duration: {format_duration(event.duration_minutes)}\n"
        f"📍 Location: {format_location_type(prefs.get('location_type'))}\n"
        f"💰 Budget: {format_budget_level(prefs.get('budget_level'))}\n"
        f"🚶 Transport: {format_transport_mode(prefs.get('transport_mode'))}\n"
        f"📆 Date Preset: {format_date_preset(prefs.get('date_preset'))}\n"
        f"🕐 Time Window: {format_time_window(prefs.get('time_window'))}\n\n"
        f"👥 Participants: {event.participant_count}\n"
        f"✅ Confirmed: {event.confirmed_count}\n"
        f"🎯 Threshold: {event.threshold_attendance}\n"
        f"📌 Min: {event.min_participants} | Target: {event.target_participants}\n"
        f"⏰ Commit-by: {commit_display}\n"
        f"🔢 Version: {event.version}"
    )


def format_participant_list(participants: list[ParticipantDTO]) -> str:
    """Format participant list."""
    if not participants:
        return "No participants yet."

    lines = ["👥 *Participants*", ""]
    for p in participants:
        name = p.display_name or (f"@{p.username}" if p.username else f"User#{p.telegram_user_id}")
        status_emoji = {
            "joined": "💭",
            "confirmed": "✅",
            "cancelled": "❌",
            "no_show": "👻",
        }.get(p.status, "?")
        lines.append(f"  {status_emoji} {name} ({p.role})")

    return "\n".join(lines)


def format_event_list(events: list[EventDTO], title: str = "Events") -> str:
    """Format a list of events compactly."""
    if not events:
        return f"📋 *{title}*\n\nNo events found."

    lines = [f"📋 *{title}*", ""]
    for e in events:
        status = e.state[:3].upper()
        time_str = format_scheduled_time(e.scheduled_time, include_flexible_note=False)
        desc = (e.description or "No description")[:50]
        lines.append(
            f"• #{e.event_id} [{status}] {e.event_type} | {time_str} | {desc}"
        )

    return "\n".join(lines)
