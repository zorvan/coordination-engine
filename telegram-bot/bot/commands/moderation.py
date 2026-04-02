"""Moderation command handler for organizer actions."""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes
from sqlalchemy import select

from config.settings import settings
from db.connection import get_session
from db.models import Event, User, EarlyFeedback, Log
from bot.common.moderation import (
    apply_warning,
)
from bot.common.reputation_trends import get_user_reliability_trend
from bot.common.event_presenters import format_user_display


async def handle_warn(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /warn command - warn a user."""
    if not update.message or not update.effective_user:
        return

    if not update.effective_chat or update.effective_chat.type not in {"group", "supergroup"}:
        await update.message.reply_text("❌ This command can only be used in groups.")
        return

    args = context.args or []
    if len(args) < 1:
        await update.message.reply_text(
            "Usage: /warn <@username|user_id> <reason>\n\n"
            "Example: /warn @alice Being consistently late"
        )
        return

    target_input = args[0]
    reason = " ".join(args[1:]) if len(args) > 1 else "No reason provided"

    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        # Get event from context
        event_id = context.user_data.get("current_event_id") if context.user_data else None

        # Find event from group
        result = await session.execute(
            select(Event).where(Event.group_id == update.effective_chat.id).order_by(Event.created_at.desc())
        )
        event = result.scalar_one_or_none()

        if event_id:
            result = await session.execute(
                select(Event).where(Event.event_id == event_id)
            )
            event = result.scalar_one_or_none()

        # Resolve target user
        target_telegram_id = None
        if target_input.startswith("@"):
            result = await session.execute(
                select(User).where(User.username == target_input.lower().lstrip("@"))
            )
            target_user = result.scalar_one_or_none()
            if target_user:
                target_telegram_id = target_user.telegram_user_id
        else:
            try:
                target_telegram_id = int(target_input)
            except ValueError:
                pass

        if not target_telegram_id:
            await update.message.reply_text(
                "❌ Could not resolve user. Please use @username or user ID."
            )
            return

        # Get user ID for the action log
        result = await session.execute(
            select(User).where(User.telegram_user_id == update.effective_user.id)
        )
        requester = result.scalar_one_or_none()

        # Apply warning
        result = await session.execute(
            select(User).where(User.telegram_user_id == target_telegram_id)
        )
        target_user = result.scalar_one_or_none()

        result = await session.execute(
            select(User).where(User.telegram_user_id == update.effective_user.id)
        )
        requester = result.scalar_one_or_none()

        moderator_user_id = requester.user_id if requester else None

        result = await session.execute(
            select(User).where(User.telegram_user_id == target_telegram_id)
        )
        target_db_user = result.scalar_one_or_none()

        target_user_id = target_db_user.user_id if target_db_user else target_telegram_id

        # Apply warning
        result = await session.execute(
            select(Event).where(Event.group_id == update.effective_chat.id).order_by(Event.created_at.desc())
        )
        event = result.scalar_one_or_none()

        event_id = event.event_id if event else None

        warning_result = await apply_warning(
            session=session,
            event_id=event_id,
            target_user_id=target_user_id,
            reason=reason,
            moderator_user_id=moderator_user_id,
        )

        await session.commit()

        await update.message.reply_text(
            f"⚠️ *Warning applied to user*\n\n"
            f"User: {target_input}\n"
            f"Reason: {reason}\n"
            f"Evidence count: {warning_result['evidence_count']}"
        )


async def handle_reliability(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /reliability command - show user's reliability trend."""
    if not update.message or not update.effective_user:
        return

    args = context.args or []
    target_input = args[0] if args else None

    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        target_telegram_id = None

        if target_input:
            if target_input.startswith("@"):
                result = await session.execute(
                    select(User).where(User.username == target_input.lower().lstrip("@"))
                )
                target_user = result.scalar_one_or_none()
                if target_user:
                    target_telegram_id = target_user.telegram_user_id
            else:
                try:
                    target_telegram_id = int(target_input)
                except ValueError:
                    pass
        else:
            target_telegram_id = update.effective_user.id

        if not target_telegram_id:
            await update.message.reply_text("❌ Could not resolve user.")
            return

        # Fetch user information for display
        result = await session.execute(
            select(User).where(User.telegram_user_id == target_telegram_id)
        )
        target_user = result.scalar_one_or_none()

        user_display = format_user_display(
            telegram_user_id=target_telegram_id,
            username=target_user.username if target_user and getattr(target_user, "username", None) else None,
            display_name=target_user.display_name if target_user and getattr(target_user, "display_name", None) else None,
            include_link=False,
        )

        # Get reliability trend
        trend = await get_user_reliability_trend(session, target_telegram_id)

        if not trend.get("current_score"):
            await update.message.reply_text("❌ No reliability data available.")
            return

        lines = [
            f"📊 *Reliability Trend for {user_display}*",
            "",
            f"Current Score: {trend.get('current_score', 0):.2f}",
            f"Events Participated: {trend.get('total_events', 0)}",
            f"Confirmed Events: {trend.get('confirmed_events', 0)}",
            f"Confirmation Rate: {trend.get('confirmation_rate', 0)*100:.1f}%",
            f"Last Event: {trend.get('last_event_days_ago', 0)} days ago",
            "",
            "Score History:",
        ]

        for entry in trend.get('score_history', [])[:5]:
            lines.append(f"  {entry['period']}: {entry['score']:.2f} ({entry['confirmed']}/{entry['total']})")

        await update.message.reply_text("\n".join(lines))


async def handle_attendance_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /attendance_history command - show user's attendance history."""
    if not update.message or not update.effective_user:
        return

    args = context.args or []
    target_input = args[0] if args else None

    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        target_telegram_id = None

        if target_input:
            if target_input.startswith("@"):
                result = await session.execute(
                    select(User).where(User.username == target_input.lower().lstrip("@"))
                )
                target_user = result.scalar_one_or_none()
                if target_user:
                    target_telegram_id = target_user.telegram_user_id
            else:
                try:
                    target_telegram_id = int(target_input)
                except ValueError:
                    pass
        else:
            target_telegram_id = update.effective_user.id

        if not target_telegram_id:
            await update.message.reply_text("❌ Could not resolve user.")
            return

        # Get attendance summary
        result = await session.execute(
            select(User).where(User.telegram_user_id == target_telegram_id)
        )
        target_user = result.scalar_one_or_none()

        result = await session.execute(
            select(User).where(User.telegram_user_id == target_telegram_id)
        )
        db_target_user = result.scalar_one_or_none()

        if not db_target_user:
            await update.message.reply_text("❌ User not found.")
            return

        # Get logs for this user
        result = await session.execute(
            select(Log).where(Log.user_id == db_target_user.user_id).order_by(Log.timestamp.desc()).limit(10)
        )
        logs = result.scalars().all()

        # Count actions
        action_counts = {}
        for log in logs:
            action_counts[log.action] = action_counts.get(log.action, 0) + 1

        total = sum(action_counts.values())
        confirmed = action_counts.get("confirm", 0)

        lines = [
            f"📋 *Attendance History for {db_target_user.display_name}*",
            "",
            f"Total Actions: {total}",
            f"Confirmations: {confirmed}",
            f"Rate: {confirmed/total*100:.1f}%" if total > 0 else "N/A",
            "",
            "Recent Actions:",
        ]

        for log in logs[:5]:
            lines.append(f"  {log.timestamp.strftime('%Y-%m-%d %H:%M')}: {log.action}")

        await update.message.reply_text("\n".join(lines))


async def handle_moderation_actions(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /mod_actions command - show moderation actions for a user."""
    if not update.message or not update.effective_user:
        return

    args = context.args or []
    if len(args) < 1:
        await update.message.reply_text(
            "Usage: /mod_actions <@username|user_id>\n\n"
            "Example: /mod_actions @alice"
        )
        return

    target_input = args[0]

    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        target_telegram_id = None

        if target_input.startswith("@"):
            result = await session.execute(
                select(User).where(User.username == target_input.lower().lstrip("@"))
            )
            target_user = result.scalar_one_or_none()
            if target_user:
                target_telegram_id = target_user.telegram_user_id
        else:
            try:
                target_telegram_id = int(target_input)
            except ValueError:
                pass

        if not target_telegram_id:
            await update.message.reply_text("❌ Could not resolve user.")
            return

        # Fetch user information for display
        result = await session.execute(
            select(User).where(User.telegram_user_id == target_telegram_id)
        )
        target_user = result.scalar_one_or_none()

        user_display = format_user_display(
            telegram_user_id=target_telegram_id,
            username=target_user.username if target_user and getattr(target_user, "username", None) else None,
            display_name=target_user.display_name if target_user and getattr(target_user, "display_name", None) else None,
            include_link=False,
        )

        # Get moderation logs
        result = await session.execute(
            select(Log).where(
                Log.user_id == target_telegram_id,
                Log.action.like("moderation:%")
            ).order_by(Log.timestamp.desc()).limit(10)
        )
        logs = result.scalars().all()

        # Get early feedback
        result = await session.execute(
            select(EarlyFeedback).where(
                EarlyFeedback.target_user_id == target_telegram_id,
                EarlyFeedback.signal_type.in_(["reliability", "toxicity"])
            ).order_by(EarlyFeedback.created_at.desc()).limit(10)
        )
        feedbacks = result.scalars().all()

        if not logs and not feedbacks:
            await update.message.reply_text("❌ No moderation actions found for this user.")
            return

        lines = [
            f"👮 *Moderation Actions for {user_display}*",
            "",
            f"Logs: {len(logs)}",
            f"Feedback: {len(feedbacks)}",
            "",
            "Recent Actions:",
        ]

        for log in logs[:3]:
            lines.append(f"  {log.timestamp.strftime('%Y-%m-%d')}: {log.action}")

        for fb in feedbacks[:3]:
            lines.append(f"  {fb.created_at.strftime('%Y-%m-%d')}: {fb.signal_type} (score: {fb.value})")

        await update.message.reply_text("\n".join(lines))
