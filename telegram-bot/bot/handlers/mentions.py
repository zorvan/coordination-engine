#!/usr/bin/env python3
"""Mention-driven natural language orchestration in group chats."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
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

from ai.llm import LLMClient
from bot.commands import event_creation, request_confirmations, suggest_time
from bot.common.scheduling import find_user_event_conflict
from bot.services import ParticipantService, EventLifecycleService
from bot.common.event_notifications import (
    send_event_invitation_dm,
)

from bot.common.event_presenters import (
    format_event_details_message,
    format_status_message,
)

from config.settings import settings
from db.connection import get_session
from db.models import Constraint, Event, Group, Log, User
from bot.common.event_access import (
    get_event_admin_telegram_id,
)
from db.users import get_or_create_user_id, get_user_id_by_username

logger = logging.getLogger("coord_bot.mentions")

_PICK_CODE_TO_ACTION: dict[str, str] = {
    "j": "join",
    "c": "confirm",
    "x": "cancel",
    "l": "lock",
    "r": "request_confirmations",
}
_ACTION_TO_PICK_CODE = {v: k for k, v in _PICK_CODE_TO_ACTION.items()}

HISTORY_LIMIT = 40
MENTION_PATTERN = re.compile(r"@([A-Za-z0-9_]{5,32})")


def _escape_for_markdown(text: str) -> str:
    """Escape Telegram Markdown v1 metacharacters in user-controlled text."""
    return (
        text.replace("[", "\\[")
        .replace("]", "\\]")
        .replace("_", "\\_")
        .replace("*", "\\*")
        .replace("`", "\\`")
    )


EVENT_ID_PATTERNS = (
    re.compile(r"\bevent\s*(?:id)?\s*[:#]?\s*(\d{1,9})\b", re.IGNORECASE),
    re.compile(r"\bid\s*[:#]?\s*(\d{1,9})\b", re.IGNORECASE),
    re.compile(r"\bevent_id\s*[:=]?\s*(\d{1,9})\b", re.IGNORECASE),
)


def _derive_collapse_at(
    scheduled_time: datetime | None,
    draft_collapse_iso: str | None,
) -> datetime | None:
    """Deadline for threshold auto-cancel (PRD collapse_at)."""
    if isinstance(draft_collapse_iso, str) and draft_collapse_iso.strip():
        try:
            dt = datetime.fromisoformat(draft_collapse_iso.strip())
            if dt > datetime.utcnow():
                return dt
        except ValueError:
            pass
    now = datetime.utcnow()
    if scheduled_time:
        candidate = scheduled_time - timedelta(hours=2)
        return candidate if candidate > now else now + timedelta(hours=1)
    return now + timedelta(days=7)


async def _offer_event_selection(
    message,
    context: ContextTypes.DEFAULT_TYPE,
    action_type: str,
    chat_id: int,
) -> None:
    """Query active events in this group and offer tap targets for disambiguation."""
    if not settings.db_url:
        await message.reply_text("❌ Database configuration is unavailable.")
        return

    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(Event)
            .join(Group, Event.group_id == Group.group_id)
            .where(
                Group.telegram_group_id == chat_id,
                Event.state.in_(["proposed", "interested", "confirmed"]),
            )
            .order_by(Event.event_id.desc())
            .limit(5)
        )
        events = result.scalars().all()

    if not events:
        await message.reply_text(
            "No active events in this group yet. Mention me to create one, "
            "or use /organize_event."
        )
        return

    action_label = {
        "join": "✅ Join",
        "confirm": "🎯 Confirm",
        "cancel": "❌ Cancel",
        "lock": "🔒 Lock",
        "request_confirmations": "📣 Ask confirmations",
    }.get(action_type, action_type)
    code = _ACTION_TO_PICK_CODE.get(action_type, "j")
    buttons = []
    for e in events:
        desc = (e.description or "").strip().replace("\n", " ")
        if len(desc) > 28:
            desc = f"{desc[:25]}…"
        buttons.append(
            [
                InlineKeyboardButton(
                    f"{action_label} #{e.event_id}: {desc}",
                    callback_data=f"mnpick_{e.event_id}_{code}",
                )
            ]
        )
    await message.reply_text(
        f"Which event should I **{action_type}** for you?",
        reply_markup=InlineKeyboardMarkup(buttons),
        parse_mode="Markdown",
    )


async def _send_group_events_list(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    reply_to_message,
) -> None:
    """Post a compact /events-style list for callback flows."""
    if not settings.db_url:
        await reply_to_message.reply_text("❌ Database configuration is unavailable.")
        return
    async with get_session(settings.db_url) as session:
        q = (
            select(Event, Group)
            .join(Group, Event.group_id == Group.group_id, isouter=True)
            .where(Group.telegram_group_id == chat_id)
            .order_by(Event.created_at.desc())
            .limit(15)
        )
        result = await session.execute(q)
        rows = result.all()
    if not rows:
        await reply_to_message.reply_text("ℹ️ No events found in this group.")
        return
    lines: list[str] = ["📋 *Recent events in this group*", ""]
    for event, group in rows:
        group_name = (
            group.group_name
            if group and group.group_name
            else str(group.telegram_group_id) if group else "Unknown Group"
        )
        description = (event.description or "No description").strip()
        if len(description) > 80:
            description = f"{description[:77]}..."
        lines.append(f"• ID `{event.event_id}` | {event.event_type} | {event.state}")
        lines.append(
            f"  Group: {group_name} | Time: {event.scheduled_time or 'TBD'} | "
            f"Duration: {event.duration_minutes or 120}m"
        )
        lines.append(f"  Description: {description}")
    await reply_to_message.reply_text("\n".join(lines), parse_mode="Markdown")


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


async def handle_mention(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
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
            message.reply_to_message.text or message.reply_to_message.caption or ""
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
    logger.debug(
        f"Mention inference: action_type={action_type}, event_id={action.get('event_id')}, text={text[:100]}"
    )

    # Handle organize_event actions (these don't need event_id - they CREATE events)
    if action_type in {"organize_event", "organize_event_flexible"}:
        mode = "flexible" if action_type == "organize_event_flexible" else "public"
        scheduling_mode = (
            "flexible" if action_type == "organize_event_flexible" else "fixed"
        )
        llm = LLMClient()
        try:
            draft = await llm.infer_event_draft_from_context(
                message_text=text,
                history=history,
                scheduling_mode=scheduling_mode,
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
        lowered = text.lower()
        wants_event = any(
            kw in lowered
            for kw in (
                "let's",
                "let us",
                "we should",
                "how about",
                "shall we",
                "what if",
                "can we",
                "gather",
                "meet",
                "meetup",
                "hangout",
            )
        )
        if wants_event:
            keyboard = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "🗓 Create an event from this",
                            callback_data="mention_start_organize",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "📋 See current events",
                            callback_data="mention_show_status",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "❓ How to ask",
                            callback_data="mention_ask_help",
                        )
                    ],
                ]
            )
            await message.reply_text(
                f"🤖 {response}\n\n"
                "_Want me to turn this into an event, or see what’s already planned?_",
                reply_markup=keyboard,
                parse_mode="Markdown",
            )
        else:
            await message.reply_text(f"🤖 {response}")
        return

    # For actions that need an event_id, check if we have one
    # If not, ask user to clarify which event
    if action_type in {
        "join",
        "confirm",
        "cancel",
        "lock",
        "request_confirmations",
    } and not action.get("event_id"):
        # Check if the message might be about organizing a new event
        lowered_text = text.lower()
        if any(
            kw in lowered_text
            for kw in ["organize", "organise", "create", "plan", "new event"]
        ):
            # User might be trying to organize - start that flow instead
            mode = "flexible" if "flexible" in lowered_text else "public"
            scheduling_mode = "flexible" if "flexible" in lowered_text else "fixed"
            llm = LLMClient()
            try:
                draft = await llm.infer_event_draft_from_context(
                    message_text=text,
                    history=history,
                    scheduling_mode=scheduling_mode,
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

        await _offer_event_selection(
            message=message,
            context=context,
            action_type=action_type,
            chat_id=chat.id,
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
            f"⏳ Approval recorded.\nApprovals: {len(approved)}/{len(required)}"
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


async def handle_disambiguation_callbacks(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Inline actions from opinion disambiguation and event pick lists."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    data = query.data
    user = query.from_user
    if not user:
        return

    if data.startswith("mnpick_"):
        rest = data[7:]
        idx = rest.rfind("_")
        if idx <= 0:
            await query.edit_message_text("❌ Invalid selection.")
            return
        try:
            event_id = int(rest[:idx])
            code = rest[idx + 1 :]
        except ValueError:
            await query.edit_message_text("❌ Invalid selection.")
            return
        action_type = _PICK_CODE_TO_ACTION.get(code)
        if not action_type:
            await query.edit_message_text("❌ Unknown action.")
            return
        action = {
            "action_type": action_type,
            "event_id": event_id,
            "target_username": None,
            "constraint_type": None,
            "assistant_response": "",
        }
        try:
            await query.edit_message_text("⏳ Working…")
        except Exception:
            pass
        if not query.message:
            return
        await _execute_inferred_action(
            context=context,
            action=action,
            requester_id=user.id,
            requester_display_name=user.full_name,
            requester_username=user.username,
            reply_message=query.message,
        )
        return

    if data == "mention_start_organize":
        await event_creation.start_event_flow(update, context, mode="public")
        return

    if data == "mention_show_status":
        if query.message:
            await _send_group_events_list(context, query.message.chat.id, query.message)
        return

    if data == "mention_ask_help":
        await query.edit_message_text(
            "❓ *Tips*\n"
            "• Mention me with a clear ask.\n"
            "• When I list events, tap a row to pick one.\n"
            "• Use /organize_event to start a structured setup.",
            parse_mode="Markdown",
        )
        return


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

        # Store event info for later use in processing modifications
        modify_request = {
            "event_id": event_id,
            "event_description": event.description or "",
            "event_scheduled_time": (
                event.scheduled_time.isoformat()
                if event and event.scheduled_time
                else None
            ),
            "admin_id": admin_id,
            "requester_id": user.id if user else None,
            "requester_username": user.username if user else None,
        }
        request_id = uuid4().hex[:8]
        context.user_data[f"pending_modify_request_{request_id}"] = modify_request

        # Show keyboard for user to choose modification method
        keyboard = [
            [
                InlineKeyboardButton(
                    "✍️ Write your own", callback_data=f"modinput_{request_id}_write"
                ),
                InlineKeyboardButton(
                    "🤖 AI suggested", callback_data=f"modinput_{request_id}_ai"
                ),
            ],
            [
                InlineKeyboardButton(
                    "❌ Cancel", callback_data=f"modinput_{request_id}_cancel"
                )
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            "🔧 How would you like to modify the event?\n\n"
            "Choose a method to specify the changes you want to make.",
            reply_markup=reply_markup,
            parse_mode="Markdown",
        )

        return

    if data.startswith("event_details_"):
        event_id_str = data.replace("event_details_", "")
        try:
            event_id = int(event_id_str)
        except (TypeError, ValueError):
            await query.edit_message_text("❌ Invalid event ID.")
            return
        await _send_event_details(query.message, event_id, context)
        return

    if data.startswith("event_status_"):
        event_id_str = data.replace("event_status_", "")
        try:
            event_id = int(event_id_str)
        except (TypeError, ValueError):
            await query.edit_message_text("❌ Invalid event ID.")
            return
        await _send_status(query.message, event_id, context)
        return

    if data.startswith("modinput_"):
        parts = data.split("_")
        if len(parts) != 3:
            await query.answer("❌ Invalid request format.")
            return

        request_id = parts[1]
        action = parts[2]

        pending_key = f"pending_modify_request_{request_id}"
        modify_request = context.user_data.pop(pending_key, None)

        if not modify_request:
            await query.edit_message_text("❌ This modification request has expired.")
            return

        if action == "cancel":
            await query.edit_message_text("✅ Modification request cancelled.")
            return

        event_id = modify_request.get("event_id")
        admin_id = modify_request.get("admin_id")

        if action == "write":
            # Ask user to provide modification text
            await query.edit_message_text(
                "✏️ *Please type your modification request below:*\n\n"
                "Describe the changes you want to make. Examples:\n"
                "- Change time to March 8, 2026 at 18:00\n"
                "- Increase threshold to 10\n"
                "- Move location to gym\n\n"
                "Type 'cancel' to abort.",
                parse_mode="Markdown",
            )
            # Store pending modification for processing
            context.user_data[f"pending_mod_text_{request_id}"] = {
                "event_id": event_id,
                "admin_id": admin_id,
                "requester_id": modify_request.get("requester_id"),
                "requester_username": modify_request.get("requester_username"),
            }
            return

        if action == "ai":
            # Use AI to suggest modifications
            async with get_session(settings.db_url) as session:
                result = await session.execute(
                    select(Event).where(Event.event_id == event_id)
                )
                event = result.scalar_one_or_none()
                if not event:
                    await query.edit_message_text("❌ Event not found.")
                    return

                llm = LLMClient()
                try:
                    draft = {
                        "description": event.description or "",
                        "event_type": event.event_type,
                        "scheduled_time": (
                            event.scheduled_time.isoformat()
                            if event and event.scheduled_time
                            else None
                        ),
                        "duration_minutes": int(event.duration_minutes or 120),
                        "threshold_attendance": int(event.threshold_attendance or 0),
                    }
                    change_text = (
                        "Please suggest improvements to this event draft. "
                        "Return a JSON object with a 'suggestion' key containing "
                        "your recommendation."
                    )
                    patch = await llm.infer_event_draft_patch(draft, change_text)
                    suggestion = patch
                finally:
                    await llm.close()

                change_text = suggestion.get(
                    "suggestion", "Please review the AI suggestions for modifications."
                )

                # Submit the request to admin
                await _submit_modify_request_via_callback(
                    update,
                    context,
                    request_id,
                    event_id,
                    admin_id,
                    change_text,
                    modify_request.get("requester_id"),
                    modify_request.get("requester_username"),
                )
                return

        await query.edit_message_text("❌ Unknown modification action.")
        return


async def handle_modify_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle text messages for modification requests."""
    message = update.effective_message
    if not message or not message.text:
        return

    text = message.text.strip()

    pending_keys = [k for k in context.user_data if k.startswith("pending_mod_text_")]
    if not pending_keys:
        return

    request_id = pending_keys[0].replace("pending_mod_text_", "")
    pending_data = context.user_data.pop(pending_keys[0])

    if text.lower() == "cancel":
        await message.reply_text("✅ Modification request cancelled.")
        return

    change_text = text
    event_id = pending_data.get("event_id")
    admin_id = pending_data.get("admin_id")
    requester_id = pending_data.get("requester_id")
    requester_username = pending_data.get("requester_username")

    await _submit_modify_request_via_message(
        update,
        context,
        request_id,
        event_id,
        admin_id,
        change_text,
        requester_id,
        requester_username,
    )


async def _submit_modify_request_via_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    request_id: str,
    event_id: int,
    admin_id: int,
    change_text: str,
    requester_id: int | None,
    requester_username: str | None,
) -> None:
    """Helper to submit modification request via message."""
    pending_key = f"modreq_{request_id}"
    context.bot_data.setdefault("pending_modify_requests", {})[pending_key] = {
        "event_id": event_id,
        "requester_id": requester_id,
        "requester_username": requester_username,
        "change_text": change_text,
        "admin_id": admin_id,
        "created_at": datetime.utcnow().isoformat(),
    }

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Approve", callback_data=f"modreq_{request_id}_approve"
            ),
            InlineKeyboardButton(
                "❌ Reject", callback_data=f"modreq_{request_id}_reject"
            ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"📩 *Modify request submitted for admin approval*\n\n"
        f"Event ID: {event_id}\n"
        f"Changes: {change_text}\n\n"
        f"Waiting for admin approval...",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    from bot.common.event_notifications import send_event_modification_request_dm

    await send_event_modification_request_dm(
        context=context,
        telegram_user_id=admin_id,
        event_data={
            "event_id": event_id,
            "change_text": change_text,
        },
        event_id=event_id,
        deadline_info="Please review and approve the modification request",
        request_id=request_id,
    )


async def _submit_modify_request_via_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    request_id: str,
    event_id: int,
    admin_id: int,
    change_text: str,
    requester_id: int | None,
    requester_username: str | None,
) -> None:
    """Helper to submit modification request via callback."""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Approve", callback_data=f"modreq_{request_id}_approve"
            ),
            InlineKeyboardButton(
                "❌ Reject", callback_data=f"modreq_{request_id}_reject"
            ),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.edit_message_text(
        f"📩 *Modify request submitted for admin approval*\n\n"
        f"Event ID: {event_id}\n"
        f"Changes: {change_text}\n\n"
        f"Waiting for admin approval...",
        reply_markup=reply_markup,
        parse_mode="Markdown",
    )

    from bot.common.event_notifications import send_event_modification_request_dm

    await send_event_modification_request_dm(
        context=context,
        telegram_user_id=admin_id,
        event_data={
            "event_id": event_id,
            "change_text": change_text,
        },
        event_id=event_id,
        deadline_info="Please review and approve the modification request",
        request_id=request_id,
    )


async def _resolve_mentioned_participants(text: str, bot_username: str) -> list[int]:
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
                result = await session.execute(select(User).where(User.user_id == uid))
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
        await _send_status(reply_message, event_id, context)
        return
    if action_type == "event_details" and event_id is not None:
        await _send_event_details(reply_message, event_id, context)
        return
    if action_type == "constraint_add" and event_id is not None:
        target_username = str(action.get("target_username", "")).strip()
        constraint_type = str(action.get("constraint_type", "")).strip()
        summary = str(action.get("assistant_response", "")).strip()
        await _save_constraint_from_inferred(
            context=context,
            reply_message=reply_message,
            requester_telegram_user_id=requester_id,
            requester_display_name=requester_display_name,
            requester_username=requester_username,
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
            context=context,
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


async def _send_status(
    reply_message, event_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send event status text in mention flow."""
    if not settings.db_url:
        await reply_message.reply_text("❌ Database configuration is unavailable.")
        return
    from sqlalchemy import func
    from db.models import Log, Constraint

    async with get_session(settings.db_url) as session:
        result = await session.execute(select(Event).where(Event.event_id == event_id))
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
                    func.count(Constraint.constraint_id)
                    .select()
                    .where(Constraint.event_id == event_id)
                )
            ).scalar_one()
        )
    await reply_message.reply_text(
        await format_status_message(
            event_id, event, log_count, constraint_count, context.bot
        )
    )


async def _send_event_details(
    reply_message, event_id: int, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Send event details in mention flow."""
    if not settings.db_url:
        await reply_message.reply_text("❌ Database configuration is unavailable.")
        return
    from db.models import Log as LogModel, Constraint as ConstraintModel

    async with get_session(settings.db_url) as session:
        result = await session.execute(select(Event).where(Event.event_id == event_id))
        event = result.scalar_one_or_none()
        if not event:
            await reply_message.reply_text("❌ Event not found.")
            return
        logs = (
            (
                await session.execute(
                    select(LogModel).where(LogModel.event_id == event_id)
                )
            )
            .scalars()
            .all()
        )
        constraints = (
            (
                await session.execute(
                    select(ConstraintModel).where(ConstraintModel.event_id == event_id)
                )
            )
            .scalars()
            .all()
        )
    await reply_message.reply_text(
        await format_event_details_message(
            event_id, event, list(logs), list(constraints), context.bot
        )
    )


async def _save_constraint_from_inferred(
    context: ContextTypes.DEFAULT_TYPE,
    reply_message,
    requester_telegram_user_id: int,
    requester_display_name: str | None,
    requester_username: str | None,
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

    target_input = (
        target_username if target_username.startswith("@") else f"@{target_username}"
    )

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(select(Event).where(Event.event_id == event_id))
        ).scalar_one_or_none()
        if not event:
            await reply_message.reply_text("❌ Event not found.")
            return

        source_user_id = await get_or_create_user_id(
            session,
            telegram_user_id=requester_telegram_user_id,
            display_name=requester_display_name,
            username=requester_username,
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
        (
            "organize_event_flexible",
            {"organize flexible", "flexible event", "plan flexible"},
        ),
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
    context: ContextTypes.DEFAULT_TYPE,
) -> None:
    """Apply join/confirm/cancel using shared attendance functions."""
    if not settings.db_url:
        await reply_message.reply_text("❌ Database configuration is unavailable.")
        return

    from bot.common.scheduling import find_user_event_conflict

    async with get_session(settings.db_url) as session:
        event = (
            await session.execute(select(Event).where(Event.event_id == event_id))
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

            # Use ParticipantService for join operation
            participant_service = ParticipantService(session)
            participant, is_new_join = await participant_service.join(
                event_id=event_id,
                telegram_user_id=requester_telegram_user_id,
                source="mention",
            )

            # Check if we need to transition state from proposed to interested
            confirmed_count = await participant_service.get_confirmed_count(event_id)
            if event.state == "proposed" and confirmed_count > 0:
                lifecycle_service = EventLifecycleService(context.bot, session)
                try:
                    event, _ = await lifecycle_service.transition_with_lifecycle(
                        event_id=event_id,
                        target_state="interested",
                        actor_telegram_user_id=requester_telegram_user_id,
                        source="mention",
                        reason="Participant joined via mention",
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to transition event {event_id} to interested: {e}"
                    )

        elif action_type == "confirm":
            if event.state in {"locked", "completed", "cancelled"}:
                await reply_message.reply_text(
                    f"❌ Cannot confirm event {event_id} - it's {event.state}."
                )
                return

            # Use ParticipantService for confirm operation
            participant_service = ParticipantService(session)
            participant, is_new_confirm = await participant_service.confirm(
                event_id=event_id,
                telegram_user_id=requester_telegram_user_id,
                source="mention",
            )

            # Check if we need to transition to confirmed state
            confirmed_count = await participant_service.get_confirmed_count(event_id)
            if event.state != "confirmed" and confirmed_count > 0:
                lifecycle_service = EventLifecycleService(context.bot, session)
                try:
                    event, _ = await lifecycle_service.transition_with_lifecycle(
                        event_id=event_id,
                        target_state="confirmed",
                        actor_telegram_user_id=requester_telegram_user_id,
                        source="mention",
                        reason="Participant confirmed via mention",
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to transition event {event_id} to confirmed: {e}"
                    )

        elif action_type == "cancel":
            if event.state == "locked":
                await reply_message.reply_text(
                    f"❌ Cannot cancel event {event_id} - it's already locked."
                )
                return

            # Use ParticipantService for cancel operation
            participant_service = ParticipantService(session)
            try:
                participant, is_new_cancel = await participant_service.cancel(
                    event_id=event_id,
                    telegram_user_id=requester_telegram_user_id,
                    source="mention",
                )
            except Exception as e:
                await reply_message.reply_text(
                    f"❌ Failed to cancel attendance: {str(e)}"
                )
                return

            # Update event state if needed
            confirmed_count = await participant_service.get_confirmed_count(event_id)
            if (
                event.state not in {"locked", "completed", "cancelled"}
                and confirmed_count == 0
            ):
                new_state = "interested" if confirmed_count > 0 else "proposed"
                lifecycle_service = EventLifecycleService(context.bot, session)
                try:
                    event, _ = await lifecycle_service.transition_with_lifecycle(
                        event_id=event_id,
                        target_state=new_state,
                        actor_telegram_user_id=requester_telegram_user_id,
                        source="mention",
                        reason="Last participant cancelled",
                    )
                except Exception as e:
                    logger.error(
                        f"Failed to transition event {event_id} to {new_state}: {e}"
                    )

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
            f"✅ Confirmed for event {event_id}.\nEvent state is now `confirmed`."
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
            await session.execute(select(Event).where(Event.event_id == event_id))
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

        # Use ParticipantService to finalize commitments (new system)
        participant_service = ParticipantService(session)
        await participant_service.finalize_commitments(event_id)

        event.state = "locked"
        event.locked_at = datetime.utcnow()
        await session.commit()

    await reply_message.reply_text(
        f"🔒 Event {event_id} locked successfully at {datetime.utcnow().isoformat()}."
    )


async def _start_interactive_event_flow(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str,
    draft: dict,
    chat,
    user,
) -> None:
    """
    Start interactive event creation flow with pre-filled data from LLM draft.

    This allows the bot to ask for missing parameters while using inferred values
    for what the LLM could extract from context.
    """
    from bot.commands.event_creation import start_event_flow

    # Start the standard event flow first
    await start_event_flow(update, context, mode=mode)

    # Now pre-fill the flow data with inferred values from the draft
    if context.user_data is None:
        return

    flow_key = "private_event_flow" if mode == "private" else "event_flow"
    event_flow_raw = context.user_data.get(flow_key)
    if not isinstance(event_flow_raw, dict):
        return

    event_flow: dict[str, Any] = event_flow_raw
    flow_data = event_flow.get("data")
    if not isinstance(flow_data, dict):
        flow_data = {}
        event_flow["data"] = flow_data

    # Pre-fill with inferred values (only if present in draft)
    if draft.get("description"):
        flow_data["description"] = str(draft.get("description")).strip()[:500]
    if draft.get("event_type"):
        event_type = str(draft.get("event_type")).strip().lower()
        if event_type in event_creation.ALLOWED_EVENT_TYPES:
            flow_data["event_type"] = event_type
    if draft.get("threshold_attendance"):
        try:
            flow_data["threshold_attendance"] = max(
                1, int(draft.get("threshold_attendance", 3))
            )
        except (TypeError, ValueError):
            pass
    if draft.get("duration_minutes"):
        try:
            flow_data["duration_minutes"] = max(
                30, int(draft.get("duration_minutes", 120))
            )
        except (TypeError, ValueError):
            pass
    if draft.get("scheduled_time") and isinstance(draft.get("scheduled_time"), str):
        try:
            parsed = datetime.fromisoformat(draft.get("scheduled_time").strip())
            flow_data["scheduled_time"] = parsed.isoformat(timespec="minutes")
            if mode == "public":
                flow_data["scheduling_mode"] = "fixed"
        except ValueError:
            pass
    if draft.get("location_type"):
        location_type = str(draft.get("location_type")).strip().lower()
        if location_type in {value for _, value in event_creation.LOCATION_PRESETS}:
            flow_data["location_type"] = location_type
    if draft.get("budget_level"):
        budget_level = str(draft.get("budget_level")).strip().lower()
        if budget_level in {value for _, value in event_creation.BUDGET_PRESETS}:
            flow_data["budget_level"] = budget_level
    if draft.get("transport_mode"):
        transport_mode = str(draft.get("transport_mode")).strip().lower()
        if transport_mode in {value for _, value in event_creation.TRANSPORT_PRESETS}:
            flow_data["transport_mode"] = transport_mode
    if draft.get("date_preset"):
        date_preset = str(draft.get("date_preset")).strip().lower()
        if date_preset in event_creation.DATE_PRESET_LABELS:
            flow_data["date_preset"] = date_preset
    if draft.get("time_window"):
        time_window = str(draft.get("time_window")).strip().lower()
        if time_window in event_creation.TIME_WINDOWS:
            flow_data["time_window"] = time_window
    if draft.get("planning_notes"):
        notes = draft.get("planning_notes", [])
        flow_data["planning_notes"] = (
            [str(x).strip()[:300] for x in notes if str(x).strip()]
            if isinstance(notes, list)
            else []
        )

    context.user_data[flow_key] = event_flow

    # Notify user about the inferred values and continue the flow
    inferred_msg = "🤖 I've inferred some details from your message:\n\n"
    inferred_items = []
    if flow_data.get("description"):
        inferred_items.append(f"• Description: {flow_data['description']}")
    if flow_data.get("event_type"):
        inferred_items.append(f"• Type: {flow_data['event_type']}")
    if flow_data.get("scheduled_time"):
        inferred_items.append(f"• Time: {flow_data['scheduled_time']}")
    if flow_data.get("location_type"):
        inferred_items.append(f"• Location: {flow_data['location_type']}")

    if inferred_items:
        inferred_msg += "\n".join(inferred_items)
        inferred_msg += (
            "\n\nI'll guide you through the remaining details to set up the event."
        )
        await update.message.reply_text(inferred_msg)
    else:
        await update.message.reply_text(
            "🤖 Let me help you organize an event!\n\n"
            "I'll guide you through the setup process."
        )


async def _handle_organize_event_direct(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str,
    draft: dict,
    chat,
    user,
) -> None:
    """
    Create event from LLM draft, or start interactive flow if parameters are missing.

    If the draft has sufficient information (at minimum a description), creates the event directly.
    Otherwise, starts the interactive event creation flow with pre-filled data from the draft.
    """
    if not settings.db_url:
        await update.message.reply_text("❌ Database configuration is unavailable.")
        return

    # Check if we have minimum required information
    description = draft.get("description")
    has_description = bool(description and str(description).strip())

    # If missing critical info (description), start interactive flow instead
    if not has_description:
        # Start interactive flow with pre-filled data from draft
        await _start_interactive_event_flow(
            update=update,
            context=context,
            mode=mode,
            draft=draft,
            chat=chat,
            user=user,
        )
        return

    # We have a description, proceed with direct creation
    description = str(description).strip()[:500]
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
        if isinstance(notes, list)
        else []
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
        else:
            current_members = group.member_list or []
            if creator_id and creator_id not in current_members:
                group.member_list = [*current_members, creator_id]
                await session.commit()

        commit_by = None
        if scheduled_time:
            commit_by = event_creation.compute_commit_by_time(scheduled_time)

        collapse_raw = draft.get("collapse_at")
        collapse_iso = (
            str(collapse_raw).strip()
            if collapse_raw is not None and str(collapse_raw).strip()
            else None
        )
        collapse_at_dt = _derive_collapse_at(scheduled_time, collapse_iso)

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
            collapse_at=collapse_at_dt,
            duration_minutes=duration,
            threshold_attendance=threshold,
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

        # Add creator as participant using new system
        participant_service = ParticipantService(session)
        await participant_service.join(
            event_id=event.event_id,
            telegram_user_id=creator_id,
            source="mention",
            role="organizer",
        )

        group_members = group.member_list or []

        async with get_session(settings.db_url) as session:
            organizer_user = (
                await session.execute(
                    select(User).where(User.telegram_user_id == creator_id)
                )
            ).scalar_one_or_none()
            organizer_username = organizer_user.username if organizer_user else None
            organizer_display_name = (
                organizer_user.display_name if organizer_user else None
            )

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
                "organizer_display_name": organizer_display_name,
            }

            # Send invitations
            dm_count = 0
            dm_failed = 0

            if invite_all:
                # Public event: DM all group members (excluding creator who gets admin DM)
                logger.info(
                    f"Public event {event.event_id}: Sending DMs to all {len(group_members)} group members"
                )
                for telegram_user_id in group_members:
                    if telegram_user_id and telegram_user_id != creator_id:
                        try:
                            await send_event_invitation_dm(
                                context,
                                int(telegram_user_id),
                                data_for_dm,
                                int(event.event_id),
                            )
                            logger.info(
                                f"DM sent to user {telegram_user_id} for event {event.event_id} (public, all members)"
                            )
                            dm_count += 1
                        except Exception as e:
                            logger.error(
                                f"Error sending DM to user {telegram_user_id}: {e}",
                                exc_info=True,
                            )
                            dm_failed += 1
            else:
                # Private event: DM ONLY invitees + admin (NOT group members)
                logger.info(
                    f"Private event {event.event_id}: Sending DMs to {len(invitees)} invitees only"
                )

                # Send to all listed invitees
                for invite_handle in invitees:
                    if not invite_handle.startswith("@"):
                        continue
                    username = invite_handle[1:]
                    try:
                        user_id = await get_user_id_by_username(session, username)
                        if user_id:
                            result = await session.execute(
                                select(User).where(User.user_id == int(user_id))
                            )
                            invitee_user = result.scalar_one_or_none()
                            if invitee_user and invitee_user.telegram_user_id:
                                await send_event_invitation_dm(
                                    context,
                                    int(invitee_user.telegram_user_id),
                                    data_for_dm,
                                    int(event.event_id),
                                )
                                logger.info(
                                    "DM sent to user %s (@%s) for event %s (private invitee)",
                                    invitee_user.telegram_user_id,
                                    username,
                                    event.event_id,
                                )
                                dm_count += 1
                            else:
                                logger.warning(
                                    f"User @{username} not found or no telegram_user_id for event {event.event_id}"
                                )
                                dm_failed += 1
                        else:
                            logger.warning(
                                f"No user_id found for handle @{username} in event {event.event_id}"
                            )
                            dm_failed += 1
                    except Exception as e:
                        logger.error(
                            f"Error sending DM to @{username}: {e}", exc_info=True
                        )
                        dm_failed += 1

                # Also send to admin/creator
                if creator_id:
                    try:
                        await send_event_invitation_dm(
                            context,
                            int(creator_id),
                            data_for_dm,
                            int(event.event_id),
                        )
                        logger.info(
                            f"DM sent to admin {creator_id} for event {event.event_id} (private event admin)"
                        )
                        dm_count += 1
                    except Exception as e:
                        logger.error(
                            f"Error sending DM to admin {creator_id}: {e}",
                            exc_info=True,
                        )
                        dm_failed += 1

            logger.info(
                f"Event {event.event_id} DM distribution complete: {dm_count} sent, {dm_failed} failed"
            )

            # Prepare display texts for admin summary
            scheduled_time_display = (
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
                "all group members" if invite_all else f"{len(invitees)} users"
            )
            location_text = location_type.replace("_", " ").title()
            budget_text = budget_level.replace("_", " ").title()
            transport_text = transport_mode.replace("_", " ").title()
            date_preset_text = event_creation.DATE_PRESET_LABELS.get(
                date_preset,
                date_preset.title(),
            )
            time_window_text = time_window.title()

            # Escape description for Markdown (avoid parsing errors with special chars)
            escaped_description = _escape_for_markdown(description)

            if creator_id:
                # Send full details to admin via DM
                full_admin_summary = (
                    f"✅ *Event Created Successfully!*\n\n"
                    f"Event ID: `{event.event_id}`\n"
                    f"State: proposed (awaiting confirmations)\n\n"
                    f"Type: {event_type}\n"
                    f"Description: {escaped_description}\n"
                    f"Time: {scheduled_time_display}\n"
                    f"Commit-By: {commit_by_text}\n"
                    f"Date Preset: {date_preset_text}\n"
                    f"Time Window: {time_window_text}\n"
                    f"Duration: {duration} minutes\n"
                    f"Mode: {scheduling_mode}\n"
                    f"Location Type: {location_text}\n"
                    f"Budget: {budget_text}\n"
                    f"Transport: {transport_text}\n"
                    f"Threshold: {threshold}\n"
                    f"Invitees: {invitees_summary}\n\n"
                    f"✅ Event ready for confirmation. Run /confirm {event.event_id} to lock it."
                    + (
                        "\n\nFlexible flow tip:\n"
                        "Each attendee can add availability slots with:\n"
                        f"/constraints {event.event_id} availability <YYYY-MM-DD HH:MM, ...>"
                        if scheduling_mode == "flexible"
                        else ""
                    )
                )

                admin_keyboard = [
                    [
                        InlineKeyboardButton(
                            "View Event Details",
                            callback_data=f"event_details_{event.event_id}",
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            "Manage Event",
                            callback_data=f"event_admin_{event.event_id}",
                        )
                    ],
                ]
                admin_reply_markup = InlineKeyboardMarkup(admin_keyboard)

                await context.bot.send_message(
                    chat_id=creator_id,
                    text=full_admin_summary,
                    reply_markup=admin_reply_markup,
                    parse_mode="Markdown",
                )
                logger.info(
                    f"Full event details sent to admin {creator_id} via DM for event {event.event_id}"
                )

        proposer = f"@{user.username}" if user and user.username else "the group"
        scheduled_time_group = (
            str(scheduled_time_raw).replace("T", " ")
            if scheduled_time_raw
            else "⏳ Time TBD — flexible scheduling"
        )
        location_group = location_type.replace("_", " ").title()
        threshold_call = f"We need {threshold} people on board to make this happen."

        escaped_desc_group = _escape_for_markdown(description)

        group_message = (
            f"🌱 *New event proposed by {proposer}*\n\n"
            f"*{escaped_desc_group}*\n\n"
            f"📅 {scheduled_time_group}\n"
            f"⏱ {duration} min · 📍 {location_group}\n"
            f"👥 {threshold_call}\n\n"
            f"🎉 _Event #{event.event_id} · Tap below to respond_"
        )

        group_keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        "✅ I'm in",
                        callback_data=f"event_join_{event.event_id}",
                    ),
                    InlineKeyboardButton(
                        "📋 Details",
                        callback_data=f"event_details_{event.event_id}",
                    ),
                ],
                [
                    InlineKeyboardButton(
                        "📣 Share",
                        switch_inline_query=f"event {event.event_id}",
                    ),
                ],
            ]
        )

        await update.message.reply_text(
            group_message,
            reply_markup=group_keyboard,
            parse_mode="Markdown",
        )
