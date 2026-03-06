#!/usr/bin/env python3
"""Group membership/user sync handler."""
from telegram import Update, User
from telegram.ext import ContextTypes
from sqlalchemy import select

from config.settings import settings
from db.connection import get_session
from db.models import Group
from db.users import get_or_create_user_id


async def track_group_members(
    update: Update, _context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Sync users/groups from group messages and new member events."""
    chat = update.effective_chat
    message = update.effective_message
    if not chat or not message:
        return
    if chat.type not in {"group", "supergroup"}:
        return
    if not settings.db_url:
        return

    users_to_sync: dict[int, User] = {}
    if update.effective_user:
        users_to_sync[update.effective_user.id] = update.effective_user
    for member in (message.new_chat_members or []):
        users_to_sync[member.id] = member
    if not users_to_sync:
        return

    chat_id = chat.id
    chat_title = chat.title or str(chat_id)

    async with get_session(settings.db_url) as session:
        result = await session.execute(
            select(Group).where(Group.telegram_group_id == chat_id)
        )
        group = result.scalar_one_or_none()

        member_ids = list(users_to_sync.keys())
        if not group:
            group = Group(
                telegram_group_id=chat_id,
                group_name=chat_title,
                member_list=member_ids,
            )
            session.add(group)
        else:
            changed = False
            if group.group_name != chat_title:
                group.group_name = chat_title
                changed = True
            current_members = group.member_list or []
            new_members = [
                member_id
                for member_id in member_ids
                if member_id not in current_members
            ]
            if new_members:
                group.member_list = [*current_members, *new_members]
                changed = True
            if changed:
                session.add(group)

        for user in users_to_sync.values():
            await get_or_create_user_id(
                session,
                telegram_user_id=user.id,
                display_name=user.full_name,
                username=user.username,
            )

        await session.commit()
