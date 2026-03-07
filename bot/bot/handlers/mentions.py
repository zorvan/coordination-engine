#!/usr/bin/env python3
"""Mention-driven natural language orchestration in group chats."""
from __future__ import annotations

from datetime import datetime
import logging
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
from bot.commands import event_creation, request_confirmations, suggest_time
from bot.common.scheduling import find_user_event_conflict
from bot.common.attendance import (
    derive_state_from_attendance,
    finalize_commitments,
    has_attendee,
    has_confirmed,
    mark_confirmed,
    mark_joined,
    remove_attendee,
)
from bot.common.event_notifications import (
    send_event_invitation_dm,
    send_event_modification_request_dm,
)

from bot.common.event_presenters import (
    format_event_details_message,
    format_status_message,
)
logger = logging.getLogger("coord_bot.mentions")
from config.settings import settings
from db.connection import get_session
from db.models import Constraint, Event, Group, Log, User
from bot.common.event_access import (
    get_event_organizer_telegram_id,
    get_event_admin_telegram_id,
)
from db.users import get_or_create_user_id, get_user_id_by_username

HISTORY_LIMIT = 40
MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_]{5,32})")
EVENT_ID_PATTERNS = (
    re.compile(r"\bevent\s*(?:id)?\s*[:#]?\s*(\d{1,9})\b", re.IGNORECASE),
    re.compile(r"\bid\s*[:#]?\s*(\d{1,9})\b", re.IGNORECASE),
    re.compile(r"\bevent_id\s*[:=]?\s*(\d{1,9})\b", re.IGNORECASE),
)


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
    # If user is in organize_event text stages, let that FSM consume input.
    user_data = context.user_data or {}
    event_flow = user_data.get("event_flow")
    if isinstance(event_flow, dict):
        stage = str(event_flow.get("stage", "")).strip().lower()
        if stage in {"description", "time", "invitees", "final"}:
            return

    bot_username = (context.bot.username or "").lower()
    has_bot_mention = bool(bot_username and f"@{bot_username}" in text.lower())
    is_reply_to_bot = _is_reply_to_bot_message(message, context)
    if not has_bot_mention and not is_reply_to_bot:
        return

    parent_text = ""
    history = context.bot_data.get("chat_history", {}).get(chat.id, [])
    if is_reply_to_bot:
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
    direct_action = _infer_direct_action(text=text, parent_text=parent_text)
    if direct_action is not None:
        action = direct_action
    else:
        llm = LLMClient()
        try:
            action = await llm.infer_group_mention_action(
                text=text,
                history=history,
            )
        finally:
            await llm.close()

    action_type = str(action.get("action_type", "opinion")).strip().lower()
    if action_type in {"organize_event", "organize_event_flexible"}:
        mode = "flexible" if action_type == "organize_event_flexible" else "public"
        llm = LLMClient()
        try:
            draft = await llm.infer_event_draft_from_context(
                message_text=text,
                history=history,
            )
        finally:
            await llm.close()
        await _handle_organize_event_direct(
            update=update,
            context=context,
            mode=mode,
            draft=draft,
            chat=chat,
            user=user,
        )
        return

    if action_type == "opinion":
        response = str(action.get("assistant_response", "")).strip()
        if not response:
            response = (
                "I reviewed the context and suggest clarifying goals, constraints, "
                "and expected attendees before deciding."
            )
        await message.reply_text(f"🤖 {response}")
        return

    if action_type in {
        "join",
        "confirm",
        "cancel",
        "lock",
        "request_confirmations",
    } and not action.get("event_id"):
        await message.reply_text(
            "❌ I inferred an action, but event ID is missing.\n"
            "Use a specific message like: `confirm event 12`."
        )
        return

    participant_user_ids = await _resolve_mentioned_participants(
        text=text,
        bot_username=bot_username,
    )
    approval_required_actions = {
        "constraint_add",
        "organize_event",
        "organize_event_flexible",
    }
    if participant_user_ids and action_type in approval_required_actions:
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
        requester_display_name=user.full_name,
        requester_username=user.username,
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
        requester_display_name=None,
        requester_username=None,
        reply_message=message,
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for event-related actions."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    data = query.data
    user = query.from_user

    if data.startswith("event_modify_"):
        event_id_str = data.replace("event_modify_", "")
        try:
            event_id = int(event_id_str)
        except (TypeError, ValueError):
            await query.edit_message_text("❌ Invalid event ID.")
            return

        if not settings.db_url:
            await query.edit_message_text("❌ Database configuration is unavailable.")
            return

        async with get_session(settings.db_url) as session:
            result = await session.execute(
                select(Event).where(Event.event_id == event_id)
            )
            event = result.scalar_one_or_none()
            if not event:
                await query.edit_message_text("❌ Event not found.")
                return

            admin_id = get_event_admin_telegram_id(event)

        requester_id = user.id if user else None
        requester_username = user.username if user else None
        request_id = uuid4().hex[:8]

        pending_modify_root = context.bot_data.setdefault("pending_modify_requests", {})
        pending_modify_root[request_id] = {
            "request_id": request_id,
            "event_id": event_id,
            "requester_id": requester_id,
            "requester_username": requester_username,
            "change_text": "",
            "admin_id": admin_id,
            "created_at": datetime.utcnow().isoformat(),
        }

        await query.edit_message_text(
            "✅ *Modification request submitted!*\n\n"
            "The event admin will review your request.",
            parse_mode="Markdown",
        )

        if admin_id:
            await send_event_modification_request_dm(
                context,
                admin_id,
                {
                    "event_id": event_id,
                    "requester_id": requester_id,
                    "requester_username": requester_username,
                    "change_text": "",
                    "request_id": request_id,
                    "description": event.description if event else "",
                    "scheduled_time": event.scheduled_time.isoformat() if event and event.scheduled_time else "",
                    "location_type": "cafe",
                },
                event_id,
                "Please review and approve this modification request.",
            )

        return

    if data.startswith("event_details_"):
        event_id_str = data.replace("event_details_", "")
        try:
            event_id = int(event_id_str)
        except (TypeError, ValueError):
            await query.edit_message_text("❌ Invalid event ID.")
            return
        await _send_event_details(query.message, event_id)
        return

    if data.startswith("event_status_"):
        event_id_str = data.replace("event_status_", "")
        try:
            event_id = int(event_id_str)
        except (TypeError, ValueError):
            await query.edit_message_text("❌ Invalid event ID.")
            return
        await _send_status(query.message, event_id)
        return


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
    requester_display_name: str | None,
    requester_username: str | None,
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
            context=context,
            reply_message=reply_message,
            requester_telegram_user_id=requester_id,
            event_id=event_id,
            target_username=target_username,
            constraint_type=constraint_type,
            summary=summary,
        )
        return
    if action_type in {"join", "confirm", "cancel"} and event_id is not None:
        await _apply_participation_action(
            reply_message=reply_message,
            requester_telegram_user_id=requester_id,
            requester_display_name=requester_display_name,
            requester_username=requester_username,
            event_id=event_id,
            action_type=action_type,
        )
        return
    if action_type == "lock" and event_id is not None:
        await _apply_lock_action(
            reply_message=reply_message,
            event_id=event_id,
        )
        return
    if action_type == "request_confirmations" and event_id is not None:
        await request_confirmations.send_confirmation_request_message(
            reply_message=reply_message,
            context=context,
            event_id=event_id,
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
        await format_status_message(event_id, event, log_count, constraint_count)
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
        await format_event_details_message(event_id, event, list(logs), list(constraints))
    )


async def _save_constraint_from_inferred(
    context: ContextTypes.DEFAULT_TYPE,
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
            try:
                target_chat = await context.bot.get_chat(target_input)
                target_user_id = await get_or_create_user_id(
                    session,
                    telegram_user_id=target_chat.id,
                    display_name=getattr(target_chat, "full_name", None),
                    username=getattr(target_chat, "username", None),
                )
            except Exception:
                await reply_message.reply_text(
                    f"❌ Target {target_input} not found in records and could not be resolved from Telegram API."
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
        bot_id = context.bot.id if context.bot else None
        return bot_id is None or parent.from_user.id == bot_id
    return False


def _infer_direct_action(text: str, parent_text: str = "") -> dict | None:
    """Infer explicit imperative actions without LLM for reliability."""
    lowered = text.lower()
    mapping = [
        ("organize_event_flexible", {"organize flexible", "flexible event", "plan flexible"}),
        (
            "organize_event",
            {
                "organize event",
                "organize this event",
                "schedule event",
                "create event",
                "new event",
                "plan event",
            },
        ),
        (
            "request_confirmations",
            {"request confirmations", "ask confirmations", "confirm buttons"},
        ),
        ("confirm", {"confirm", "confirmed", "interested", "interest"}),
        ("join", {"join", "joined"}),
        ("cancel", {"cancel", "leave", "withdraw"}),
        ("lock", {"lock", "finalize", "close"}),
        ("status", {"status"}),
        ("event_details", {"details", "detail"}),
        ("suggest_time", {"suggest time", "suggest", "time options"}),
    ]
    selected_action: str | None = None
    for action_name, keywords in mapping:
        if any(keyword in lowered for keyword in keywords):
            selected_action = action_name
            break
    if not selected_action:
        return None

    event_id = _extract_event_id(text) or _extract_event_id(parent_text)
    return {
        "action_type": selected_action,
        "event_id": event_id,
        "target_username": None,
        "constraint_type": None,
        "assistant_response": "Parsed explicit action from message.",
    }


def _extract_event_id(raw_text: str) -> int | None:
    """Extract event id from free text."""
    if not raw_text:
        return None
    for pattern in EVENT_ID_PATTERNS:
        match = pattern.search(raw_text)
        if not match:
            continue
        try:
            return int(match.group(1))
        except (TypeError, ValueError):
            continue
    return None


async def _apply_participation_action(
    reply_message,
    requester_telegram_user_id: int,
    requester_display_name: str | None,
    requester_username: str | None,
    event_id: int,
    action_type: str,
) -> None:
    """Apply join/confirm/cancel using shared attendance functions."""
    if not settings.db_url:
        await reply_message.reply_text("❌ Database configuration is unavailable.")
        return

    from bot.common.scheduling import find_user_event_conflict

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(
                select(Event).where(Event.event_id == event_id)
            )
        ).scalar_one_or_none()
        if not event:
            await reply_message.reply_text("❌ Event not found.")
            return

        user_id = await get_or_create_user_id(
            session,
            telegram_user_id=requester_telegram_user_id,
            display_name=requester_display_name,
            username=requester_username,
        )

        if action_type == "join":
            if event.state in {"locked", "completed"}:
                await reply_message.reply_text(
                    f"❌ Cannot join event {event_id} - it's {event.state}."
                )
                return
            conflict = await find_user_event_conflict(
                session=session,
                telegram_user_id=requester_telegram_user_id,
                start_time=event.scheduled_time,
                duration_minutes=event.duration_minutes,
                ignore_event_id=event.event_id,
            )
            if conflict:
                await reply_message.reply_text(
                    "❌ You have a conflicting event.\n"
                    f"Conflicting Event ID: {conflict.event_id}\n"
                    f"Time: {conflict.scheduled_time}\n"
                    f"Duration: {conflict.duration_minutes or 120} minutes"
                )
                return

            attendance = list(event.attendance_list or [])
            attendance, _ = mark_joined(attendance, requester_telegram_user_id)
            event.attendance_list = attendance
            if event.state == "proposed":
                event.state = "interested"

        elif action_type == "confirm":
            if event.state in {"locked", "completed", "cancelled"}:
                await reply_message.reply_text(
                    f"❌ Cannot confirm event {event_id} - it's {event.state}."
                )
                return
            attendance = list(event.attendance_list or [])
            if not has_attendee(attendance, requester_telegram_user_id) or not has_confirmed(attendance, requester_telegram_user_id):
                attendance, _ = mark_confirmed(attendance, requester_telegram_user_id)
            event.attendance_list = attendance
            event.state = "confirmed"

        elif action_type == "cancel":
            if event.state == "locked":
                await reply_message.reply_text(
                    f"❌ Cannot cancel event {event_id} - it's already locked."
                )
                return
            attendance = list(event.attendance_list or [])
            filtered, changed = remove_attendee(attendance, requester_telegram_user_id)
            if not changed:
                await reply_message.reply_text(
                    f"❌ You haven't joined event {event_id} yet. Nothing to cancel."
                )
                return
            event.attendance_list = filtered
            if event.state not in {"locked", "completed", "cancelled"}:
                event.state = derive_state_from_attendance(filtered)

        session.add(
            Log(
                event_id=event_id,
                user_id=user_id,
                action=action_type,
                metadata_dict={"timestamp": datetime.utcnow().isoformat()},
            )
        )
        await session.commit()

    if action_type == "join":
        await reply_message.reply_text(
            f"✅ Joined event {event_id}.\nUse /confirm {event_id} to commit attendance."
        )
    elif action_type == "confirm":
        await reply_message.reply_text(
            f"✅ Committed to event {event_id}.\nEvent state is now `confirmed`."
        )
    else:
        await reply_message.reply_text(f"❌ Attendance cancelled for event {event_id}.")


async def _apply_lock_action(reply_message, event_id: int) -> None:
    """Lock event using shared attendance functions."""
    if not settings.db_url:
        await reply_message.reply_text("❌ Database configuration is unavailable.")
        return

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(
                select(Event).where(Event.event_id == event_id)
            )
        ).scalar_one_or_none()
        if not event:
            await reply_message.reply_text("❌ Event not found.")
            return
        if event.state != "confirmed":
            await reply_message.reply_text(
                f"❌ Cannot lock event {event_id}. Current state: {event.state}. "
                "Lock is allowed only when state is `confirmed`."
            )
            return
        event.state = "locked"
        event.attendance_list, _ = finalize_commitments(event.attendance_list)
        event.locked_at = datetime.utcnow()
        await session.commit()

    await reply_message.reply_text(
        f"🔒 Event {event_id} locked successfully at {datetime.utcnow().isoformat()}."
    )


async def _handle_organize_event_direct(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str,
    draft: dict,
    chat,
    user,
) -> None:
    """Directly create event from LLM draft without interactive flow."""
    if not settings.db_url:
        await update.message.reply_text("❌ Database configuration is unavailable.")
        return
    
    description = str(draft.get("description") or "Group planned event").strip()[:500]
    event_type = str(draft.get("event_type") or "social").strip().lower()
    if event_type not in event_creation.ALLOWED_EVENT_TYPES:
        event_type = "social"
    
    try:
        threshold = max(1, int(draft.get("threshold_attendance", 3)))
    except (TypeError, ValueError):
        threshold = 3
    
    try:
        duration = max(30, int(draft.get("duration_minutes", 120)))
    except (TypeError, ValueError):
        duration = 120
    
    scheduled_time_raw = draft.get("scheduled_time")
    if mode == "flexible" or not isinstance(scheduled_time_raw, str):
        scheduling_mode = "flexible"
        scheduled_time = None
    else:
        scheduling_mode = "fixed"
        try:
            scheduled_time = datetime.fromisoformat(scheduled_time_raw)
        except ValueError:
            scheduling_mode = "flexible"
            scheduled_time = None
    
    invite_all = bool(draft.get("invite_all_members", True))
    invitees_raw = draft.get("invitees", [])
    invitees = event_creation._normalize_patch_invitees(invitees_raw)
    
    location_type = str(draft.get("location_type") or "cafe").strip().lower()
    if location_type not in {value for _, value in event_creation.LOCATION_PRESETS}:
        location_type = "cafe"
    
    budget_level = str(draft.get("budget_level") or "medium").strip().lower()
    if budget_level not in {value for _, value in event_creation.BUDGET_PRESETS}:
        budget_level = "medium"
    
    transport_mode = str(draft.get("transport_mode") or "any").strip().lower()
    if transport_mode not in {value for _, value in event_creation.TRANSPORT_PRESETS}:
        transport_mode = "any"
    
    date_preset = str(draft.get("date_preset") or "custom").strip().lower()
    if date_preset not in event_creation.DATE_PRESET_LABELS and date_preset != "custom":
        date_preset = "custom"
    
    time_window = str(draft.get("time_window") or "evening").strip().lower()
    if time_window not in event_creation.TIME_WINDOWS:
        time_window = "evening"
    
    notes = draft.get("planning_notes", [])
    planning_notes = (
        [str(x).strip()[:300] for x in notes if str(x).strip()]
        if isinstance(notes, list) else []
    )
    
    creator_id = user.id if user else None
    
    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(Group).where(Group.telegram_group_id == chat.id)
        )
        group = result.scalar_one_or_none()
        
        if not group:
            group = Group(
                telegram_group_id=chat.id,
                group_name=chat.title or str(chat.id),
                member_list=[creator_id] if creator_id else [],
            )
            session.add(group)
            await session.commit()
            await session.refresh(group)
        
        commit_by = None
        if scheduled_time:
            commit_by = event_creation.compute_commit_by_time(scheduled_time)
        
        conflict = await find_user_event_conflict(
            session=session,
            telegram_user_id=creator_id,
            start_time=scheduled_time,
            duration_minutes=duration,
        )
        if conflict:
            await update.message.reply_text(
                "❌ Cannot create event: creator has a conflicting event.\n"
                f"Conflicting Event ID: {conflict.event_id}\n"
                f"Time: {conflict.scheduled_time}\n"
                f"Duration: {conflict.duration_minutes or 120} minutes"
            )
            return
        
        event = Event(
            group_id=group.group_id,
            event_type=event_type,
            description=description,
            organizer_telegram_user_id=creator_id,
            admin_telegram_user_id=creator_id,
            scheduled_time=scheduled_time,
            commit_by=commit_by,
            duration_minutes=duration,
            threshold_attendance=threshold,
            attendance_list=[f"{creator_id}:interested"] if creator_id else [],
            planning_prefs={
                "date_preset": date_preset,
                "time_window": time_window,
                "location_type": location_type,
                "budget_level": budget_level,
                "transport_mode": transport_mode,
            },
            state="proposed",
            locked_at=None,
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)
        
        group_members = group.member_list or []
        
        async with get_session(settings.db_url) as session:
            organizer_user = (
                await session.execute(
                    select(User).where(User.telegram_user_id == creator_id)
                )
            ).scalar_one_or_none()
            organizer_username = organizer_user.username if organizer_user else None
            
            data_for_dm = {
                "description": description,
                "event_type": event_type,
                "scheduled_time": scheduled_time_raw,
                "duration_minutes": duration,
                "threshold_attendance": threshold,
                "invitees": invitees if not invite_all else [],
                "invite_all_members": invite_all,
                "location_type": location_type,
                "budget_level": budget_level,
                "transport_mode": transport_mode,
                "date_preset": date_preset,
                "time_window": time_window,
                "planning_notes": planning_notes,
                "organizer_telegram_user_id": creator_id,
                "organizer_username": organizer_username,
            }
            
            send_to_all_members = invite_all
            invitees_list = invitees
            
            if not send_to_all_members and invitees_list:
                for invite_handle in invitees_list:
                    if not invite_handle.startswith("@"):
                        continue
                    username = invite_handle[1:]
                    try:
                        user_id = await get_user_id_by_username(session, username)
                        if user_id:
                            result = await session.execute(
                                select(User).where(User.user_id == int(user_id))
                            )
                            user = result.scalar_one_or_none()
                            if user and user.telegram_user_id:
                                await send_event_invitation_dm(
                                    context,
                                    int(user.telegram_user_id),
                                    data_for_dm,
                                    int(event.event_id),
                                )
                                logger.info(
                                    f"DM sent to @{username} for event {event.event_id}"
                                )
                    except Exception as e:
                        logger.error(
                            f"Error sending DM to @{username}: {e}", exc_info=True
                        )
            
            if send_to_all_members:
                for telegram_user_id in group_members:
                    if telegram_user_id:
                        try:
                            await send_event_invitation_dm(
                                context,
                                int(telegram_user_id),
                                data_for_dm,
                                int(event.event_id),
                            )
                            logger.info(
                                f"DM sent to user {telegram_user_id} for event {event.event_id}"
                            )
                        except Exception as e:
                            logger.error(
                                f"Error sending DM to user {telegram_user_id}: {e}",
                                exc_info=True,
                            )
            
            if creator_id:
                await context.bot.send_message(
                    chat_id=creator_id,
                    text=(
                        f"✅ *Event Created Successfully!*\n\n"
                        f"Event ID: {event.event_id}\n\n"
                        f"All event coordination happens in private DM."
                    ),
                )
                logger.info(f"Creator notification sent to user {creator_id} for event {event.event_id}")
        
        scheduled_time = (
            str(scheduled_time_raw).replace("T", " ")
            if scheduled_time_raw
            else "TBD (flexible scheduling)"
        )
        commit_by_text = (
            commit_by.isoformat(timespec="minutes").replace("T", " ")
            if commit_by is not None
            else "N/A"
        )
        invitees_summary = (
            "all group members"
            if invite_all else f"{len(invitees)} users"
        )
        location_text = location_type.replace("_", " ").title()
        budget_text = budget_level.replace("_", " ").title()
        transport_text = transport_mode.replace("_", " ").title()
        date_preset_text = event_creation.DATE_PRESET_LABELS.get(
            date_preset,
            date_preset.title(),
        )
        time_window_text = time_window.title()
        
        group_message = (
            f"✅ *Event Created!*\n\n"
            f"Event ID: {event.event_id}\n"
            f"Type: {event_type}\n"
            f"Description: {description}\n"
            f"Time: {scheduled_time}\n"
            f"Commit-By: {commit_by_text}\n"
            f"Date Preset: {date_preset_text}\n"
            f"Time Window: {time_window_text}\n"
            f"Duration: {duration} minutes\n"
            f"Mode: {scheduling_mode}\n"
            f"Location Type: {location_text}\n"
            f"Budget: {budget_text}\n"
            f"Transport: {transport_text}\n"
            f"Threshold: {threshold}\n"
            f"Invitees: {invitees_summary}"
            + "\n\n✅ Event ready for confirmation. Run /confirm <event_id> to lock it.\n"
            + (f"Event Admin: @{organizer_username}" if organizer_username else "Event Admin: Unknown")
        )
        
        await update.message.reply_text(group_message)