#!/usr/bin/env python3
"""Mention-driven natural language orchestration in group chats."""
from __future__ import annotations

from datetime import datetime
import re
from uuid import uuid4
from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ai.llm import LLMClient
from bot.commands import suggest_time
from bot.common.event_presenters import (
    format_event_details_message,
    format_status_message,
)
from config.settings import settings
from db.connection import get_session
from db.models import Constraint, Event, User
from db.users import get_or_create_user_id, get_user_id_by_username

HISTORY_LIMIT = 40
MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_]{5,32})")


async def record_group_history(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Record rolling chat history for each group."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or chat.type not in {"group", "supergroup"}:
        return
    text = (message.text or message.caption or "").strip()
    if not text:
        return

    bot_data = context.bot_data
    history_root = bot_data.setdefault("chat_history", {})
    chat_history = history_root.setdefault(chat.id, [])
    chat_history.append(
        {
            "user_id": user.id if user else None,
            "username": user.username if user else None,
            "display_name": user.full_name if user else None,
            "text": text,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    if len(chat_history) > HISTORY_LIMIT:
        del chat_history[:-HISTORY_LIMIT]


async def handle_mention(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle bot mentions or replies-to-bot and infer next action."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or not user:
        return
    if chat.type not in {"group", "supergroup"}:
        return
    text = (message.text or message.caption or "").strip()
    if not text:
        return
    # Slash commands should stay in the classic command handlers.
    if text.startswith("/"):
        return

    bot_username = (context.bot.username or "").lower()
    has_bot_mention = bool(bot_username and f"@{bot_username}" in text.lower())
    is_reply_to_bot = _is_reply_to_bot_message(message, context)
    if not has_bot_mention and not is_reply_to_bot:
        return

    history = context.bot_data.get("chat_history", {}).get(chat.id, [])
    if is_reply_to_bot:
        # Give model stronger local context from the replied bot message.
        parent_text = (
            message.reply_to_message.text
            or message.reply_to_message.caption
            or ""
        ).strip()
        if parent_text:
            history = [
                *history,
                {
                    "user_id": None,
                    "username": bot_username or None,
                    "display_name": "coord-bot",
                    "text": f"[replied_bot_prompt] {parent_text}",
                    "timestamp": datetime.utcnow().isoformat(),
                },
            ]
    llm = LLMClient()
    try:
        action = await llm.infer_group_mention_action(
            text=text,
            history=history,
        )
    finally:
        await llm.close()

    action_type = str(action.get("action_type", "opinion")).strip().lower()
    if action_type == "opinion":
        response = str(action.get("assistant_response", "")).strip()
        if not response:
            response = (
                "I reviewed the context and suggest clarifying goals, constraints, "
                "and expected attendees before deciding."
            )
        await message.reply_text(f"🤖 {response}")
        return

    participant_user_ids = await _resolve_mentioned_participants(
        text=text,
        bot_username=bot_username,
    )
    if participant_user_ids:
        pending_id = uuid4().hex[:10]
        pending_root = context.bot_data.setdefault("pending_mention_actions", {})
        pending_root[pending_id] = {
            "chat_id": chat.id,
            "requester_id": user.id,
            "action": action,
            "required_user_ids": participant_user_ids,
            "approved_user_ids": [],
            "created_at": datetime.utcnow().isoformat(),
        }
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ Approve",
                        callback_data=f"mentionact_{pending_id}_approve",
                    ),
                    InlineKeyboardButton(
                        "❌ Reject",
                        callback_data=f"mentionact_{pending_id}_reject",
                    ),
                ]
            ]
        )
        await message.reply_text(
            "🤖 *AI inferred an action from mention*\n\n"
            f"Action: {action_type}\n"
            f"Target Event: {action.get('event_id', 'N/A')}\n"
            "Waiting approvals from mentioned participants before execution.",
            reply_markup=keyboard,
        )
        return

    await _execute_inferred_action(
        context=context,
        action=action,
        requester_id=user.id,
        reply_message=message,
    )


async def handle_mention_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Process approval callbacks for inferred mention actions."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    parts = query.data.split("_")
    if len(parts) != 3 or parts[0] != "mentionact":
        return
    pending_id = parts[1]
    decision = parts[2]
    pending_root = context.bot_data.get("pending_mention_actions", {})
    pending = pending_root.get(pending_id)
    if not pending:
        await query.edit_message_text("⚠️ This approval request has expired.")
        return

    required = set(int(x) for x in pending.get("required_user_ids", []))
    clicker = query.from_user.id
    if clicker not in required:
        await query.answer(
            "Only participants mentioned in the request can approve/reject.",
            show_alert=True,
        )
        return

    if decision == "reject":
        pending_root.pop(pending_id, None)
        await query.edit_message_text(
            "❌ Action cancelled because one participant rejected it."
        )
        return

    approved = set(int(x) for x in pending.get("approved_user_ids", []))
    approved.add(clicker)
    pending["approved_user_ids"] = sorted(approved)
    if approved != required:
        await query.edit_message_text(
            "⏳ Approval recorded.\n"
            f"Approvals: {len(approved)}/{len(required)}"
        )
        return

    pending_root.pop(pending_id, None)
    action = pending.get("action", {})
    requester_id = int(pending.get("requester_id"))
    await query.edit_message_text("✅ All approvals received. Executing action...")
    message = query.message
    if not message:
        return
    await _execute_inferred_action(
        context=context,
        action=action,
        requester_id=requester_id,
        reply_message=message,
    )


async def _resolve_mentioned_participants(
    text: str, bot_username: str
) -> list[int]:
    """Resolve non-bot @mentions to known internal user IDs."""
    mentioned = {
        username.lower()
        for username in MENTION_PATTERN.findall(text)
        if username.lower() != bot_username
    }
    if not mentioned:
        return []
    if not settings.db_url:
        return []

    resolved: list[int] = []
    async with get_session(settings.db_url) as session:
        for uname in mentioned:
            uid = await get_user_id_by_username(session, f"@{uname}")
            if uid is not None:
                # get telegram id for approval checks
                result = await session.execute(
                    select(User).where(User.user_id == uid)
                )
                user = result.scalar_one_or_none()
                if user is not None:
                    resolved.append(int(user.telegram_user_id))
    return resolved


async def _execute_inferred_action(
    context: ContextTypes.DEFAULT_TYPE,
    action: dict,
    requester_id: int,
    reply_message,
) -> None:
    """Execute inferred action if supported."""
    action_type = str(action.get("action_type", "")).strip().lower()
    event_id_raw = action.get("event_id")
    try:
        event_id = int(event_id_raw) if event_id_raw is not None else None
    except (TypeError, ValueError):
        event_id = None

    if action_type == "suggest_time" and event_id is not None:
        await suggest_time._send_suggestion(reply_message, event_id)
        return
    if action_type == "status" and event_id is not None:
        await _send_status(reply_message, event_id)
        return
    if action_type == "event_details" and event_id is not None:
        await _send_event_details(reply_message, event_id)
        return
    if action_type == "constraint_add" and event_id is not None:
        target_username = str(action.get("target_username", "")).strip()
        constraint_type = str(action.get("constraint_type", "")).strip()
        summary = str(action.get("assistant_response", "")).strip()
        await _save_constraint_from_inferred(
            reply_message=reply_message,
            requester_telegram_user_id=requester_id,
            event_id=event_id,
            target_username=target_username,
            constraint_type=constraint_type,
            summary=summary,
        )
        return

    response = str(action.get("assistant_response", "")).strip()
    if not response:
        response = "I inferred an unsupported action. Try a direct command."
    await reply_message.reply_text(f"🤖 {response}")


async def _send_status(reply_message, event_id: int) -> None:
    """Send event status text in mention flow."""
    if not settings.db_url:
        await reply_message.reply_text("❌ Database configuration is unavailable.")
        return
    from sqlalchemy import func
    from db.models import Log, Constraint

    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            await reply_message.reply_text("❌ Event not found.")
            return
        log_count = int(
            (
                await session.execute(
                    func.count(Log.log_id).select().where(Log.event_id == event_id)
                )
            ).scalar_one()
        )
        constraint_count = int(
            (
                await session.execute(
                    func.count(Constraint.constraint_id).select().where(
                        Constraint.event_id == event_id
                    )
                )
            ).scalar_one()
        )
    await reply_message.reply_text(
        format_status_message(event_id, event, log_count, constraint_count)
    )


async def _send_event_details(reply_message, event_id: int) -> None:
    """Send event details in mention flow."""
    if not settings.db_url:
        await reply_message.reply_text("❌ Database configuration is unavailable.")
        return
    from db.models import Log as LogModel, Constraint as ConstraintModel

    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(Event).where(Event.event_id == event_id)
        )
        event = result.scalar_one_or_none()
        if not event:
            await reply_message.reply_text("❌ Event not found.")
            return
        logs = (
            await session.execute(
                select(LogModel).where(LogModel.event_id == event_id)
            )
        ).scalars().all()
        constraints = (
            await session.execute(
                select(ConstraintModel).where(ConstraintModel.event_id == event_id)
            )
        ).scalars().all()
    await reply_message.reply_text(
        format_event_details_message(event_id, event, list(logs), list(constraints))
    )


async def _save_constraint_from_inferred(
    reply_message,
    requester_telegram_user_id: int,
    event_id: int,
    target_username: str,
    constraint_type: str,
    summary: str,
) -> None:
    """Persist inferred constraint after approvals."""
    allowed = {"if_joins", "if_attends", "unless_joins"}
    if constraint_type not in allowed:
        await reply_message.reply_text("❌ Inferred constraint type is not supported.")
        return
    if not target_username:
        await reply_message.reply_text("❌ Inferred target user is missing.")
        return
    if not settings.db_url:
        await reply_message.reply_text("❌ Database configuration is unavailable.")
        return

    target_input = target_username if target_username.startswith("@") else f"@{target_username}"

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(
                select(Event).where(Event.event_id == event_id)
            )
        ).scalar_one_or_none()
        if not event:
            await reply_message.reply_text("❌ Event not found.")
            return

        source_user_id = await get_or_create_user_id(
            session,
            telegram_user_id=requester_telegram_user_id,
            display_name=None,
            username=None,
        )
        target_user_id = await get_user_id_by_username(session, target_input)
        if target_user_id is None:
            await reply_message.reply_text(
                f"❌ Target {target_input} not found in records."
            )
            return

        session.add(
            Constraint(
                user_id=source_user_id,
                target_user_id=target_user_id,
                event_id=event_id,
                type=constraint_type,
                confidence=0.75,
            )
        )
        await session.commit()

    await reply_message.reply_text(
        "✅ Constraint saved from mention inference.\n"
        f"Event: {event_id}\n"
        f"Target: {target_input}\n"
        f"Type: {constraint_type}\n"
        f"Summary: {summary or 'N/A'}"
    )


def _is_reply_to_bot_message(message, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Return True if message is a reply to a bot-authored message."""
    parent = message.reply_to_message
    if not parent:
        return False
    if parent.from_user and parent.from_user.is_bot:
        # Prefer strict identity when available.
        bot_id = context.bot.id if context.bot else None
        return bot_id is None or parent.from_user.id == bot_id
    return False
