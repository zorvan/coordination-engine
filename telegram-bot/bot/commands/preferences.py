"""User preferences command handler."""
from __future__ import annotations

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from sqlalchemy import select

from config.settings import settings
from db.connection import get_session
from db.models import User, UserPreference
from bot.common.user_preferences import (
    get_user_preferences,
    create_or_update_user_preferences,
    get_preference_defaults,
    get_privacy_defaults,
    set_preference_private_mode,
    get_group_aggregate_preferences,
)
from bot.common.moderation import get_reputation_dashboard
from bot.common.streaks_badges import get_user_streak, get_user_badges, format_badge_display
from bot.common.reputation_trends import get_user_reputation_summary


TIME_PREFERENCES = ["any", "morning", "afternoon", "evening", "night"]
ACTIVITY_PREFERENCES = ["any", "social", "sports", "work", "outdoor", "indoor"]
BUDGET_PREFERENCES = ["any", "free", "low", "medium", "high"]
LOCATION_PREFERENCES = ["any", "home", "outdoor", "cafe", "office", "gym"]
TRANSPORT_PREFERENCES = ["any", "walk", "public_transit", "drive"]


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /preferences command - view and set user preferences."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    telegram_user_id = user.id
    display_name = user.full_name
    
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        # Get or create user
        result = await session.execute(
            select(User).where(User.telegram_user_id == telegram_user_id)
        )
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            db_user = User(
                telegram_user_id=telegram_user_id,
                display_name=display_name,
            )
            session.add(db_user)
            await session.flush()
        
        # Get user preferences
        preferences = await get_user_preferences(session, db_user.user_id)
        
        # Show current preferences
        if not preferences:
            await update.message.reply_text(
                "📋 *Your Preferences*\n\n"
                "You haven't set any preferences yet.\n\n"
                "Set your preferences using:\n"
                "/preferences time <morning|afternoon|evening|night>\n"
                "/preferences activity <social|sports|work|outdoor|indoor>\n"
                "/preferences budget <free|low|medium|high>\n"
                "/preferences location <home|outdoor|cafe|office|gym>\n"
                "/preferences transport <walk|public_transit|drive>\n\n"
                "Or use /preferences wizard to set up your profile."
            )
            return
        
        # Show preferences with privacy indicators
        privacy = preferences.privacy_settings or {}
        
        def format_preference(pref_type: str, value: str) -> str:
            privacy_settings = privacy.get(pref_type, get_privacy_defaults(pref_type))
            if privacy_settings.get("private", False):
                return f"{pref_type}: {value} (private)"
            return f"{pref_type}: {value}"
        
        lines = [
            "📋 *Your Preferences*",
            "",
            format_preference("time", preferences.time_preference or "any"),
            format_preference("activity", preferences.activity_preference or "any"),
            format_preference("budget", preferences.budget_preference or "any"),
            format_preference("location_type", preferences.location_type_preference or "any"),
            format_preference("transport", preferences.transport_preference or "any"),
            "",
            f"Last updated: {preferences.last_updated}",
        ]
        
        await update.message.reply_text("\n".join(lines))


async def handle_wizard(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /preferences wizard - interactive preference setup."""
    if not update.message or not update.effective_user:
        return
    
    # Start preference wizard
    await update.message.reply_text(
        "🤖 *Preference Setup Wizard*\n\n"
        "Let's set up your preferences for better event matching!\n\n"
        "First, what time of day do you prefer for events?\n\n"
        "Please select:",
        reply_markup=InlineKeyboardMarkup([
            [
                InlineKeyboardButton("Any time", callback_data="pref_wizard_time_any"),
                InlineKeyboardButton("Morning", callback_data="pref_wizard_time_morning"),
            ],
            [
                InlineKeyboardButton("Afternoon", callback_data="pref_wizard_time_afternoon"),
                InlineKeyboardButton("Evening", callback_data="pref_wizard_time_evening"),
            ],
            [
                InlineKeyboardButton("Night", callback_data="pref_wizard_time_night"),
            ],
        ])
    )


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle callback queries for preference wizard."""
    query = update.callback_query
    if not query:
        return
    
    await query.answer()
    
    data = query.data
    if not data.startswith("pref_wizard_"):
        return
    
    parts = data.split("_")
    if len(parts) < 4:
        return
    
    pref_type = parts[2]  # time, activity, etc.
    pref_value = parts[3]  # the selected value
    
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        user = update.effective_user
        if not user:
            return
        
        # Get user ID
        result = await session.execute(
            select(User).where(User.telegram_user_id == user.id)
        )
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            await query.edit_message_text("❌ User not found. Please start the bot first.")
            return
        
        # Update preference
        preferences = await create_or_update_user_preferences(
            session=session,
            telegram_user_id=db_user.user_id,
            **{f"{pref_type}_preference": pref_value},
        )
        
        await session.commit()
        
        await query.edit_message_text(
            f"✅ *Preference saved!*\n\n"
            f"{pref_type.replace('_', ' ').title()}: {pref_value}\n\n"
            "Set more preferences or use /preferences to view your current settings."
        )


async def set_preference(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Set a specific preference value."""
    if not update.message or not update.effective_user:
        return
    
    args = context.args or []
    if len(args) < 2:
        await update.message.reply_text(
            "Usage: /preferences <type> <value>\n\n"
            "Types: time, activity, budget, location, transport\n"
            "Example: /preferences time evening"
        )
        return
    
    pref_type = args[0].lower()
    pref_value = args[1].lower()
    
    # Validate preference type
    valid_types = {
        "time": TIME_PREFERENCES,
        "activity": ACTIVITY_PREFERENCES,
        "budget": BUDGET_PREFERENCES,
        "location": LOCATION_PREFERENCES,
        "transport": TRANSPORT_PREFERENCES,
    }
    
    if pref_type not in valid_types:
        await update.message.reply_text(
            f"❌ Invalid preference type. Use: {', '.join(valid_types.keys())}"
        )
        return
    
    if pref_value not in valid_types[pref_type]:
        await update.message.reply_text(
            f"❌ Invalid value for {pref_type}. Use: {', '.join(valid_types[pref_type])}"
        )
        return
    
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        user = update.effective_user
        result = await session.execute(
            select(User).where(User.telegram_user_id == user.id)
        )
        db_user = result.scalar_one_or_none()
        
        if not db_user:
            await update.message.reply_text("❌ User not found. Please start the bot first.")
            return
        
        # Update preference
        preferences = await create_or_update_user_preferences(
            session=session,
            telegram_user_id=db_user.user_id,
            **{f"{pref_type.replace('location', 'location_type')}_preference": pref_value},
        )
        
        await session.commit()
        
        await update.message.reply_text(
            f"✅ *Preference updated!*\n\n"
            f"{pref_type.replace('_', ' ').title()}: {pref_value}"
        )


async def show_reputation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's reputation summary."""
    if not update.message or not update.effective_user:
        return
    
    user = update.effective_user
    telegram_user_id = user.id
    
    db_url = settings.db_url or ""
    async with get_session(db_url) as session:
        summary = await get_user_reputation_summary(session, telegram_user_id)
        
        if "error" in summary:
            await update.message.reply_text("❌ User not found.")
            return
        
        lines = [
            f"⭐ *Reputation Summary for {summary.get('display_name', 'User')}*",
            "",
            f"Global Reputation: {summary.get('global_reputation', 0):.2f}",
            "",
            "Activity-specific scores:",
        ]
        
        for activity, score in summary.get('activity_reputations', {}).items():
            lines.append(f"  - {activity}: {score:.2f}")
        
        reliability = summary.get('reliability_trend', {})
        lines.extend([
            "",
            f"Current Reliability Score: {reliability.get('current_score', 0):.2f}",
            f"Events participated: {reliability.get('total_events', 0)}",
            f"Confirmation rate: {reliability.get('confirmation_rate', 0)*100:.1f}%",
        ])
        
        await update.message.reply_text("\n".join(lines))
