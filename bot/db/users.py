"""User identity helpers for mapping Telegram IDs to internal user IDs."""
from sqlalchemy import select

from db.models import User


async def get_or_create_user_id(
    session,
    telegram_user_id: int,
    display_name: str | None = None,
) -> int:
    """Return internal users.user_id for a Telegram user, creating row if needed."""
    result = await session.execute(
        select(User).where(User.telegram_user_id == telegram_user_id)
    )
    user = result.scalar_one_or_none()

    if user:
        if display_name and user.display_name != display_name:
            user.display_name = display_name
            await session.flush()
        return int(user.user_id)

    user = User(
        telegram_user_id=telegram_user_id,
        display_name=display_name,
    )
    session.add(user)
    await session.flush()
    return int(user.user_id)
