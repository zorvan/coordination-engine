"""Clean Architecture Telegram Bot — main entry point.

Wires all layers together:
  - Infrastructure: DB, Telegram API, LLM client
  - Domain: entities, value objects, repository ports
  - Application: command/query handlers, event bus, application service
  - Presentation: Telegram handlers, presenters

This is the composition root — the only place that knows about concrete
implementations. All other code depends on abstractions.
"""

from __future__ import annotations

import logging
import sys

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config.settings import settings, Settings
from config.logging import setup_logging

# Application
from coordination_engine.application.dto import CreateEventCommand
from coordination_engine.application.services import EventApplicationService

# Infrastructure
from coordination_engine.infrastructure.persistence import (
    SQLAlchemyEventStore,
    create_event_store,
)
from coordination_engine.infrastructure.llm_adapter import LLMServiceAdapter
from coordination_engine.infrastructure.telegram_adapter import (
    TelegramMessageService,
    TelegramNotificationService,
)
from ai.llm import LLMClient

# Presentation
from coordination_engine.presentation.presenters import (
    format_event_card,
    format_event_details,
    format_event_list,
)
from coordination_engine.presentation.command_handlers import (
    handle_join_command,
    handle_confirm_command,
)
from coordination_engine.presentation.mention_handler import MentionHandler

logger = logging.getLogger("coord_engine.main")


# ---------------------------------------------------------------------------
# Composition Root
# ---------------------------------------------------------------------------

class App:
    """Application composition root.

    Holds all wired-up dependencies. Bot handlers receive `self`
    and call the appropriate application service method.
    """

    def __init__(
        self,
        event_store: SQLAlchemyEventStore,
        app_service: EventApplicationService,
        llm_service: LLMServiceAdapter,
        msg_service: TelegramMessageService,
        notification_service: TelegramNotificationService,
        mention_handler: MentionHandler,
    ) -> None:
        self.event_store = event_store
        self.app_service = app_service
        self.llm_service = llm_service
        self.msg_service = msg_service
        self.notification_service = notification_service
        self.mention_handler = mention_handler


def build_app(
    telegram_context: ContextTypes.DEFAULT_TYPE,
    database_url: str,
) -> App:
    """Build the application by wiring all layers together."""
    # Infrastructure
    event_store = create_event_store(database_url)

    llm_client = LLMClient()
    llm_service = LLMServiceAdapter(llm_client)

    msg_service = TelegramMessageService(telegram_context)
    notification_service = TelegramNotificationService(
        message_service=msg_service,
        event_store=event_store,
    )

    # Application
    from coordination_engine.application.event_bus import EventBus
    event_bus = EventBus()

    app_service = EventApplicationService(
        store=event_store,
        event_bus=event_bus,
        notifications=notification_service,
    )
    app_service.initialize()

    # Presentation
    mention_handler = MentionHandler(
        app_service=app_service,
        llm_service=llm_service,
        event_store=event_store,
    )

    return App(
        event_store=event_store,
        app_service=app_service,
        llm_service=llm_service,
        msg_service=msg_service,
        notification_service=notification_service,
        mention_handler=mention_handler,
    )


# ---------------------------------------------------------------------------
# Bot Handlers (thin layer — delegates to App)
# ---------------------------------------------------------------------------

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 *Welcome to the Coordination Engine!*\n\n"
        "I help groups organize events and build shared experiences.\n\n"
        "*Commands:*\n"
        "/organize_event — Create a new event\n"
        "/events — List events in this group\n"
        "/join <id> — Join an event\n"
        "/confirm <id> — Confirm your attendance\n"
        "/status <id> — Check event status\n"
        "/event_details <id> — Full event details\n"
        "/profile — Your reliability profile\n"
        "/my_groups — Groups you're in\n\n"
        "You can also @mention me with natural language!"
        , parse_mode="Markdown",
    )


async def cmd_organize_event(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    app: App = context.bot_data["app"]
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    args = context.args or []
    if len(args) >= 2:
        # Direct creation: /organize_event "Board games" 5
        description = args[0].strip('"\'')
        try:
            threshold = int(args[1])
        except (ValueError, IndexError):
            threshold = 3

        from coordination_engine.application.dto import CreateEventCommand
        result = await app.app_service.create_event(
            CreateEventCommand(
                group_telegram_id=chat.id,
                organizer_telegram_id=user.id,
                description=description,
                threshold_attendance=threshold,
                scheduling_mode="fixed",
            )
        )
        if result.success:
            event = result.data
            await update.message.reply_text(
                f"🌱 *Event #{event.event_id} created!*\n\n"
                f"{event.description}\n\n"
                f"Threshold: {event.threshold_attendance} · State: {event.state}",
                parse_mode="Markdown",
            )
        else:
            await update.message.reply_text(f"❌ {result.errors[0]}")
        return

    # Interactive flow — start FSM
    user_data = context.user_data
    user_data["event_flow"] = {
        "stage": "description",
        "mode": "public",
    }
    await update.message.reply_text(
        "🗓 *Let's organize an event!*\n\n"
        "Tell me about the event. What are we planning?",
        parse_mode="Markdown",
    )


async def cmd_events(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    app: App = context.bot_data["app"]
    chat = update.effective_chat
    if not chat:
        return

    result = await app.app_service.get_events_for_group(chat.id)
    if result.success and result.data:
        text = format_event_list(result.data, "Events in this group")
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text("📋 No events found in this group.")


async def cmd_event_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    app: App = context.bot_data["app"]
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /event_details <event_id>")
        return

    try:
        event_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    result = await app.app_service.get_event(event_id)
    if result.success:
        text = format_event_details(result.data)
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ {result.errors[0]}")


async def cmd_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    app: App = context.bot_data["app"]
    user = update.effective_user
    args = context.args
    if not user or not args:
        await update.message.reply_text("Usage: /join <event_id>")
        return

    try:
        event_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    await handle_join_command(update, context, app.app_service, event_id, user.id)


async def cmd_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    app: App = context.bot_data["app"]
    user = update.effective_user
    args = context.args
    if not user or not args:
        await update.message.reply_text("Usage: /confirm <event_id>")
        return

    try:
        event_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    await handle_confirm_command(update, context, app.app_service, event_id, user.id)


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    app: App = context.bot_data["app"]
    args = context.args
    if not args:
        await update.message.reply_text("Usage: /status <event_id>")
        return

    try:
        event_id = int(args[0])
    except ValueError:
        await update.message.reply_text("❌ Event ID must be a number.")
        return

    result = await app.app_service.get_event(event_id)
    if result.success:
        text = format_event_card(result.data)
        await update.message.reply_text(text, parse_mode="Markdown")
    else:
        await update.message.reply_text(f"❌ {result.errors[0]}")


async def cmd_my_groups(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "📋 *My Groups*\n\n"
        "Group tracking is automatic — I sync membership whenever you message in a group."
        , parse_mode="Markdown",
    )


async def cmd_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    app: App = context.bot_data["app"]
    user = update.effective_user
    if not user:
        return

    result = await app.app_service.get_events_for_user(user.id)
    if result.success and result.data:
        events = result.data
        total = len(events)
        confirmed = sum(1 for e in events if e.state in {"confirmed", "locked"})
        await update.message.reply_text(
            f"👤 *Your Profile*\n\n"
            f"Events participating: {total}\n"
            f"Events confirmed: {confirmed}\n"
            , parse_mode="Markdown",
        )
    else:
        await update.message.reply_text(
            "👤 *Your Profile*\n\n"
            "You haven't joined any events yet. Use /events to find one!",
            parse_mode="Markdown",
        )


# ---------------------------------------------------------------------------
# Callback Router
# ---------------------------------------------------------------------------

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Central callback router for all inline button clicks."""
    query = update.callback_query
    if not query or not query.data:
        return
    await query.answer()

    app: App = context.bot_data["app"]
    user = query.from_user
    if not user:
        return

    data = query.data

    # Event actions: event_{action}_{event_id}
    if data.startswith("event_join_"):
        event_id = int(data.replace("event_join_", ""))
        await handle_join_command(update, context, app.app_service, event_id, user.id)
        return

    if data.startswith("event_confirm_"):
        event_id = int(data.replace("event_confirm_", ""))
        await handle_confirm_command(update, context, app.app_service, event_id, user.id)
        return

    if data.startswith("event_details_"):
        event_id = int(data.replace("event_details_", ""))
        result = await app.app_service.get_event(event_id)
        if result.success:
            text = format_event_details(result.data)
            await query.message.reply_text(text, parse_mode="Markdown")
        else:
            await query.message.reply_text(f"❌ {result.errors[0]}")
        return

    if data.startswith("event_status_"):
        event_id = int(data.replace("event_status_", ""))
        result = await app.app_service.get_event(event_id)
        if result.success:
            text = format_event_card(result.data)
            await query.message.reply_text(text, parse_mode="Markdown")
        else:
            await query.message.reply_text(f"❌ {result.errors[0]}")
        return

    if data.startswith("mention_start_organize"):
        user_data = context.user_data
        user_data["event_flow"] = {
            "stage": "description",
            "mode": "public",
        }
        await query.edit_message_text(
            "🗓 *Let's organize an event!*\n\n"
            "Tell me about the event. What are we planning?",
            parse_mode="Markdown",
        )
        return

    if data.startswith("mention_show_status"):
        chat = query.message.chat
        if chat:
            result = await app.app_service.get_events_for_group(chat.id)
            if result.success and result.data:
                text = format_event_list(result.data, "Active Events")
                await query.message.reply_text(text, parse_mode="Markdown")
            else:
                await query.message.reply_text("📋 No active events in this group.")
        return

    # Fall through to legacy handler
    logger.debug("Unhandled callback: %s", data)


# ---------------------------------------------------------------------------
# Message Handler (for mention detection + event creation FSM)
# ---------------------------------------------------------------------------

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle text messages — mentions and FSM text input."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or not user or not message.text:
        return

    text = message.text.strip()
    if not text:
        return

    app: App = context.bot_data["app"]

    # Check if user is in event creation FSM
    user_data = context.user_data
    event_flow = user_data.get("event_flow")
    if isinstance(event_flow, dict) and event_flow.get("stage") == "description":
        # Create event from description
        result = await app.app_service.create_event(
            CreateEventCommand(
                group_telegram_id=chat.id,
                organizer_telegram_id=user.id,
                description=text[:500],
                event_type="social",
                scheduling_mode="fixed",
            )
        )
        if result.success:
            event = result.data
            user_data["event_flow"] = None
            await message.reply_text(
                f"🌱 *Event #{event.event_id} created!*\n\n"
                f"{event.description}\n\n"
                f"Threshold: {event.threshold_attendance} · State: {event.state}\n\n"
                f"Share this with your group to invite members!",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("📋 View Details", callback_data=f"event_details_{event.event_id}")],
                ]),
            )
        else:
            await message.reply_text(f"❌ {result.errors[0]}")
        return

    # Check for @bot mention
    bot_username = (context.bot.username or "").lower()
    has_mention = f"@{bot_username}" in text.lower() if bot_username else False

    if chat.type in {"group", "supergroup"} and has_mention:
        # Get chat history from context
        history = context.bot_data.get("chat_history", {}).get(chat.id, [])
        await app.mention_handler.handle(
            update=update,
            context=context,
            message_text=text,
            chat_id=chat.id,
            user_id=user.id,
            username=user.username,
            history=history,
        )
        return


async def record_group_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Record group chat history for LLM context."""
    message = update.effective_message
    chat = update.effective_chat
    user = update.effective_user
    if not message or not chat or chat.type not in {"group", "supergroup"}:
        return

    text = (message.text or message.caption or "").strip()
    if not text or text.startswith("/"):
        return

    history_root = context.bot_data.setdefault("chat_history", {})
    chat_history = history_root.setdefault(chat.id, [])
    chat_history.append({
        "user_id": user.id if user else None,
        "username": user.username if user else None,
        "display_name": user.full_name if user else None,
        "text": text,
        "timestamp": __import__("datetime").datetime.utcnow().isoformat(),
    })

    # Keep last 40 messages
    if len(chat_history) > 40:
        del chat_history[:-40]


# ---------------------------------------------------------------------------
# Periodic Tasks
# ---------------------------------------------------------------------------

async def run_scheduled_tasks(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Periodic background tasks."""
    # This would use a proper scheduler in production
    logger.debug("Running scheduled tasks...")


# ---------------------------------------------------------------------------
# Startup / Shutdown
# ---------------------------------------------------------------------------

async def on_startup(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Application startup hook."""
    logger.info("Coordination Engine starting up...")

    # Build the application and store in bot_data
    app = build_app(context, settings.db_url)
    context.bot_data["app"] = app

    # Check LLM availability
    try:
        client = LLMClient()
        # Simple connectivity test
        await client.close()
        logger.info("LLM client initialized: %s", settings.ai_endpoint)
    except Exception as e:
        logger.warning("LLM client unavailable: %s", e)

    # Check DB
    try:
        from db.connection import check_db_connection
        await check_db_connection(settings.db_url)
        logger.info("Database connected: %s", settings.db_url.split("@")[-1])
    except Exception as e:
        logger.error("Database connection failed: %s", e)

    logger.info("Coordination Engine ready.")


async def on_shutdown(context: ContextTypes.DEFAULT_TYPE) -> None:
    """Application shutdown hook."""
    logger.info("Shutting down Coordination Engine...")

    app: App | None = context.bot_data.get("app")
    if app:
        try:
            await app.event_store.close()
        except Exception:
            logger.exception("Error closing event store")

    logger.info("Shutdown complete.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    """Application entry point."""
    settings = Settings()
    setup_logging(settings)

    if not settings.telegram_token:
        logger.error("TELEGRAM_TOKEN is not set")
        sys.exit(1)

    if not settings.db_url:
        logger.error("DB_URL is not set")
        sys.exit(1)

    # Build application
    app_builder = (
        ApplicationBuilder()
        .token(settings.telegram_token)
        .get_updates_connection_pool_size(4)
        .concurrent_updates(True)
    )

    application = app_builder.build()

    # Startup / Shutdown
    application.job_queue.run_repeating(
        run_scheduled_tasks,
        interval=1800,  # 30 minutes
        first=60,
    )

    # Register handlers
    # Group -2: Chat history recording
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            record_group_history,
        ),
        group=-2,
    )

    # Group -1: Mention + FSM message handling
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            handle_message,
        ),
        group=-1,
    )

    # Group 0: Commands
    commands = [
        ("start", cmd_start),
        ("help", cmd_start),
        ("events", cmd_events),
        ("event_details", cmd_event_details),
        ("status", cmd_status),
        ("join", cmd_join),
        ("confirm", cmd_confirm),
        ("my_groups", cmd_my_groups),
        ("profile", cmd_profile),
    ]

    for name, handler in commands:
        application.add_handler(CommandHandler(name, handler))

    # Organize event (special — starts FSM)
    application.add_handler(CommandHandler("organize_event", cmd_organize_event))

    # Callbacks (group 1)
    application.add_handler(CallbackQueryHandler(handle_callback), group=1)

    # Run
    logger.info("Starting bot in polling mode...")
    application.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
