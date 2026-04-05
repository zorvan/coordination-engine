#!/usr/bin/env python3
"""Memory-First Event Creation — v3 entry point.

When a user signals intent to organize, prior event memories surface
in the group chat BEFORE any creation questions. Then the bot asks
clarifying questions until intent is clear. No timeout forces structure.
"""
from __future__ import annotations

import logging
from typing import Any

from telegram import Update
from telegram.ext import ContextTypes

from config.settings import settings
from db.connection import get_session
from db.models import Group
from bot.services.event_memory_service import EventMemoryService

logger = logging.getLogger("coord_bot.commands.meaning_formation")


async def start_meaning_formation(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str = "public",
    event_type_hint: str | None = None,
) -> None:
    """
    Begin memory-first event creation.

    v3 flow:
    1. Surface prior same-type event memories in group chat
    2. THEN ask "What are you trying to bring together?"
    3. Clarify intent through open-ended questions
    4. Transition to structured creation when ready
    """
    message = update.effective_message
    if not message or not update.effective_chat or not update.effective_user:
        return

    chat = update.effective_chat
    chat_id = chat.id
    chat_title = chat.title or str(chat_id)
    telegram_user_id = update.effective_user.id

    if not settings.db_url:
        await message.reply_text("❌ Database configuration is unavailable.")
        return

    group_id = None
    if mode == "public":
        if chat.type not in {"group", "supergroup"}:
            await message.reply_text(
                "❌ This command can only be used in a Telegram group."
            )
            return

        async with get_session(settings.db_url) as session:
            result = await session.execute(
                select(Group).where(Group.telegram_group_id == chat_id)
            )
            group = result.scalar_one_or_none()

            if not group:
                group = Group(
                    telegram_group_id=chat_id,
                    group_name=chat_title,
                    member_list=[telegram_user_id],
                )
                session.add(group)
                await session.commit()
                await session.refresh(group)

            group_id = group.group_id

            # v3: Surface prior memories BEFORE any creation prompt
            memory_service = EventMemoryService(update.get_bot(), session)
            prior_memories = await memory_service.get_prior_event_memories(
                event_type=event_type_hint or "",
                group_id=group.group_id,
                limit=3,
            )

    # Store formation state in user_data
    flow_key = "private_event_flow" if mode == "private" else "event_flow"
    context.user_data[flow_key] = {
        "stage": "meaning_formation",
        "data": {
            "creator": telegram_user_id,
            "scheduling_mode": "fixed" if mode == "public" else "flexible",
            "formation_turns": 0,
            "clarified": {},
            "group_id": group_id,
        },
    }

    if group_id:
        context.user_data[flow_key]["group_title"] = chat_title

    # Surface memories in group chat (if any)
    if prior_memories:
        memory_lines = ["📿 Prior memories from similar events:\n"]
        for mem in prior_memories:
            if mem.weave_text:
                # Show just the header — users can /recall for full text
                first_line = (mem.weave_text or "").split("\n")[0]
                memory_lines.append(f"• {first_line}")

        if len(memory_lines) > 1:
            await message.reply_text("\n\n".join(memory_lines))

    # Opening prompt — vague, open-ended
    if event_type_hint:
        prompt = (
            f"Here's what this group has done before as {event_type_hint} events. "
            "Now — what are you trying to bring together?\n\n"
            "It can be as vague as 'something outdoors' or as specific as "
            "'Friday evening football'. I'll help you figure it out."
        )
    else:
        prompt = (
            "What kind of event are you thinking about?\n\n"
            "It can be as vague as 'something outdoors' or as specific as "
            "'Friday evening football'. I'll help you figure it out."
        )

    await message.reply_text(prompt)


async def handle_meaning_formation_message(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    mode: str,
) -> bool:
    """
    Process a user message during meaning-formation mode.

    Returns True if the flow should continue in meaning-formation mode,
    False if it's ready to transition to structured event creation.
    """
    if not update.effective_message or not context.user_data:
        return False

    flow_key = "private_event_flow" if mode == "private" else "event_flow"
    flow_data = context.user_data.get(flow_key, {})

    if flow_data.get("stage") != "meaning_formation":
        return False

    text = (update.effective_message.text or "").strip()
    if not text:
        return False

    formation_data = flow_data.get("data", {})
    turns = formation_data.get("formation_turns", 0)
    clarified = formation_data.get("clarified", {})

    # Simple heuristic: extract what we can from the user's text
    _extract_intent_from_text(text, clarified)

    formation_data["formation_turns"] = turns + 1
    formation_data["clarified"] = clarified

    # After 2-3 turns, check if we have enough to start structured creation
    has_enough = (
        "description" in clarified or
        "event_type" in clarified
    )

    if turns >= 2 and has_enough:
        # Transition to structured flow
        flow_data["stage"] = "structured_transition"
        flow_data["data"].update(clarified)

        description = clarified.get("description", "Group event")
        event_type = clarified.get("event_type", "social")
        scheduling_mode = formation_data.get("scheduling_mode", "fixed")

        mode_label = "fixed date/time" if scheduling_mode == "fixed" else "flexible"

        await update.effective_message.reply_text(
            f"Got it — a {description} ({event_type}).\n\n"
            f"Let me set up the details. Mode: {mode_label}.\n"
            f"I'll guide you through the rest inline."
        )
        return False  # Signal to transition out

    # Continue with another clarifying question
    next_question = _next_clarifying_question(clarified, turns)
    await update.effective_message.reply_text(next_question)
    return True


def _extract_intent_from_text(text: str, clarified: dict[str, Any]) -> None:
    """Extract basic intent from user text — lightweight, no behavioral inference."""
    lower = text.lower()

    # Event type detection
    type_keywords = {
        "football": "sports", "soccer": "sports", "basketball": "sports",
        "hiking": "outdoor", "walk": "outdoor", "run": "outdoor",
        "board game": "social", "game night": "social", "dinner": "social",
        "lunch": "social", "coffee": "social", "drinks": "social",
        "meeting": "work", "workshop": "work", "study": "work",
    }
    for keyword, etype in type_keywords.items():
        if keyword in lower:
            clarified.setdefault("event_type", etype)
            break

    # Description extraction — just use the text itself
    if "description" not in clarified and len(text) > 5:
        clarified["description"] = text[:500]


def _next_clarifying_question(
    clarified: dict[str, Any],
    turns: int,
) -> str:
    """Ask the next clarifying question based on what we already know."""
    if "description" not in clarified:
        return (
            "Can you describe it a bit more? What would people actually do? "
            "Even a sentence helps."
        )

    if "event_type" not in clarified:
        return (
            "What kind of event is this — social, sports, outdoor, work, "
            "or something else?"
        )

    # If we have basics, offer to proceed
    return (
        "Sounds good. Want me to set up the details (time, place, etc.) "
        "or is there anything else you want to clarify first?"
    )


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /plan command — start memory-first event creation."""
    await start_meaning_formation(update, context, mode="public")
