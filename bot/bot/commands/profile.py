#!/usr/bin/env python3
"""Profile command handler."""
from sqlalchemy import select, func
from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings
from db.connection import get_session
from db.models import User, Feedback, Reputation


async def handle(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle /profile command."""
    if not update.message:
        return

    if not update.effective_user:
        return
    if not settings.db_url:
        await update.message.reply_text("❌ Database configuration is unavailable.")
        return

    telegram_user_id = update.effective_user.id
    async with get_session(settings.db_url) as session:
        user_result = await session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            await update.message.reply_text(
                "👤 *Your Profile*\n\n"
                "No profile data yet.\n"
                "Join/confirm events and submit feedback to build your profile."
            )
            return

        feedback_stats = await session.execute(
            select(
                func.count(Feedback.feedback_id),
                func.avg(Feedback.value),
            ).where(Feedback.user_id == user.user_id)
        )
        feedback_count, avg_feedback = feedback_stats.one()

        rep_rows = await session.execute(
            select(Reputation)
            .where(Reputation.user_id == user.user_id)
            .order_by(Reputation.score.desc())
            .limit(5)
        )
        reputation_rows = rep_rows.scalars().all()

    lines = [
        "👤 *Your Profile*",
        "",
        f"Username: @{user.username}" if user.username else "Username: N/A",
        f"Display Name: {user.display_name or 'N/A'}",
        f"Global Reputation: {float(user.reputation or 1.0):.2f}/5",
        f"Feedback Entries: {int(feedback_count or 0)}",
        f"Avg Feedback Score: {float(avg_feedback or 0.0):.2f}",
        "",
        "Top Activity Reputation:",
    ]
    if reputation_rows:
        for rep in reputation_rows:
            lines.append(
                f"- {rep.activity_type}: {float(rep.score or 0.0):.2f}"
            )
    else:
        lines.append("- No activity reputation yet.")

    await update.message.reply_text("\n".join(lines))
