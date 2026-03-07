#!/usr/bin/env python3
"""Private event organization command handler."""
from calendar import Calendar, month_name
from datetime import date, datetime, timedelta
import re
from typing import Any
from telegram import (
    Update,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import ContextTypes

from bot.common.event_notifications import (
    send_event_modification_request_dm,
    build_event_invitation_keyboard,
)
from bot.common.keyboards import build_threshold_markup
from config.settings import settings
from db.connection import get_session
from db.models import Event, Group, User
from sqlalchemy import select


TELEGRAM_HANDLE_PATTERN = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")
ALLOWED_EVENT_TYPES = {"social", "sports", "work"}
DEFAULT_COMMIT_BY_OFFSET_HOURS = 12
TIME_WINDOWS: dict[str, list[str]] = {
    "morning": ["08:00", "09:00", "10:00", "11:00"],
    "afternoon": ["12:00", "13:00", "14:00", "15:00"],
    "evening": ["17:00", "18:00", "19:00", "20:00"],
    "night": ["21:00", "22:00", "23:00"],
}
LOCATION_PRESETS = [
    ("🏠 Home", "home"),
    ("🌳 Outdoor", "outdoor"),
    ("☕ Cafe", "cafe"),
    ("🏢 Office", "office"),
    ("🏋️ Gym", "gym"),
]
BUDGET_PRESETS = [
    ("🆓 Free", "free"),
    ("💸 Low", "low"),
    ("💰 Medium", "medium"),
    ("💎 High", "high"),
]
TRANSPORT_PRESETS = [
    ("🚶 Walk", "walk"),
    ("🚌 Public Transit", "public_transit"),
    ("🚗 Drive", "drive"),
    ("🤝 Any", "any"),
]
DATE_PRESET_LABELS = {
    "today": "Today",
    "tomorrow": "Tomorrow",
    "weekend": "Weekend",
    "nextweek": "Next Week",
}
WEEKDAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def compute_commit_by_time(scheduled_time: datetime | None) -> datetime | None:
    """Derive default commit-by deadline from scheduled time."""
    if scheduled_time is None:
        return None
    return scheduled_time - timedelta(hours=DEFAULT_COMMIT_BY_OFFSET_HOURS)


def build_compact_markup(
    options: list[tuple[str, str]],
    *,
    columns: int = 2,
    footer: list[tuple[str, str]] | None = None,
) -> InlineKeyboardMarkup:
    """Build compact inline keyboard with optional footer rows."""
    rows: list[list[InlineKeyboardButton]] = []
    current_row: list[InlineKeyboardButton] = []
    for index, (label, callback_data) in enumerate(options):
        current_row.append(
            InlineKeyboardButton(label, callback_data=callback_data)
        )
        if len(current_row) == columns or index == len(options) - 1:
            rows.append(current_row)
            current_row = []
    for label, callback_data in footer or []:
        rows.append([InlineKeyboardButton(label, callback_data=callback_data)])
    return InlineKeyboardMarkup(rows)


def build_date_preset_markup() -> InlineKeyboardMarkup:
    """Build quick date preset keyboard."""
    options = [
        ("Today", "private_event_date_preset_today"),
        ("Tomorrow", "private_event_date_preset_tomorrow"),
        ("Weekend", "private_event_date_preset_weekend"),
        ("Next Week", "private_event_date_preset_nextweek"),
    ]
    footer = [
        ("📅 Custom Calendar", "private_event_date_preset_custom"),
        ("✏️ Edit Previous", "private_event_edit_type"),
    ]
    return build_compact_markup(options, columns=2, footer=footer)


def build_date_options_markup(dates: list[date], preset: str) -> InlineKeyboardMarkup:
    """Build date choice keyboard for multi-date presets."""
    options = [
        (
            f"{WEEKDAY_LABELS[d.weekday()]} {d.strftime('%m-%d')}",
            f"private_event_date_pick_{d.strftime('%Y%m%d')}",
        )
        for d in dates
    ]
    footer = [("✏️ Edit Previous", "private_event_edit_date_preset")]
    if preset in {"weekend", "nextweek"}:
        footer.insert(0, ("📅 Custom Calendar", "private_event_date_preset_custom"))
    return build_compact_markup(options, columns=2, footer=footer)


def build_time_window_markup() -> InlineKeyboardMarkup:
    """Build quick time-window keyboard."""
    options = [
        ("🌅 Morning", "private_event_time_window_morning"),
        ("🌤 Afternoon", "private_event_time_window_afternoon"),
        ("🌆 Evening", "private_event_time_window_evening"),
        ("🌙 Night", "private_event_time_window_night"),
    ]
    footer = [
        ("📅 Change Date", "private_event_date_preset_custom"),
        ("✏️ Edit Previous", "private_event_edit_date_preset"),
    ]
    return build_compact_markup(options, columns=2, footer=footer)


def build_time_options_markup(window: str) -> InlineKeyboardMarkup:
    """Build compact keyboard for concrete time options by window."""
    time_options = TIME_WINDOWS.get(window, [])
    options = [
        (time_value, f"private_event_time_option_{time_value.replace(':', '')}")
        for time_value in time_options
    ]
    footer = [
        ("⌨️ Enter Time Manually", "private_event_time_manual"),
        ("✏️ Edit Previous", "private_event_edit_time_window"),
    ]
    return build_compact_markup(options, columns=3, footer=footer)


def build_location_type_markup() -> InlineKeyboardMarkup:
    """Build location type presets."""
    options = [
        (label, f"private_event_location_{value}")
        for label, value in LOCATION_PRESETS
    ]
    return build_compact_markup(
        options,
        columns=2,
        footer=[("✏️ Edit Previous", "private_event_edit_duration")],
    )


def build_budget_markup() -> InlineKeyboardMarkup:
    """Build budget presets."""
    options = [
        (label, f"private_event_budget_{value}")
        for label, value in BUDGET_PRESETS
    ]
    return build_compact_markup(
        options,
        columns=2,
        footer=[("✏️ Edit Previous", "private_event_edit_location")],
    )


def build_transport_markup() -> InlineKeyboardMarkup:
    """Build transport mode presets."""
    options = [
        (label, f"private_event_transport_{value}")
        for label, value in TRANSPORT_PRESETS
    ]
    return build_compact_markup(
        options,
        columns=2,
        footer=[("✏️ Edit Previous", "private_event_edit_budget")],
    )


def build_invitee_mode_markup() -> InlineKeyboardMarkup:
    """Build invitee entry mode keyboard."""
    options = [
        ("👥 Invite All Members", "private_event_invite_all"),
        ("✍️ Enter Handles", "private_event_invite_custom"),
    ]
    return build_compact_markup(
        options,
        columns=1,
        footer=[("✏️ Edit Previous", "private_event_edit_transport")],
    )


def resolve_date_preset(preset: str, now: datetime | None = None) -> list[date]:
    """Resolve date preset into one or more candidate dates."""
    base = (now or datetime.now()).date()
    if preset == "today":
        return [base]
    if preset == "tomorrow":
        return [base + timedelta(days=1)]
    if preset == "weekend":
        days_until_saturday = (5 - base.weekday()) % 7
        saturday = base + timedelta(days=days_until_saturday)
        sunday = saturday + timedelta(days=1)
        return [saturday, sunday]
    if preset == "nextweek":
        days_until_next_monday = (7 - base.weekday()) % 7
        if days_until_next_monday == 0:
            days_until_next_monday = 7
        monday = base + timedelta(days=days_until_next_monday)
        return [monday + timedelta(days=offset) for offset in range(7)]
    return []


def build_calendar_markup(year: int, month: int) -> InlineKeyboardMarkup:
    """Build month-view inline calendar keyboard."""
    rows: list[list[InlineKeyboardButton]] = []
    rows.append(
        [InlineKeyboardButton(
            f"{month_name[month]} {year}", callback_data="private_event_cal_ignore"
        )]
    )
    rows.append(
        [
            InlineKeyboardButton(day, callback_data="private_event_cal_ignore")
            for day in ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        ]
    )

    cal = Calendar(firstweekday=0)
    for week in cal.monthdayscalendar(year, month):
        row = []
        for day in week:
            if day == 0:
                row.append(
                    InlineKeyboardButton(" ", callback_data="private_event_cal_ignore")
                )
            else:
                row.append(
                    InlineKeyboardButton(
                        str(day),
                        callback_data=f"private_event_cal_day_{year}_{month}_{day}",
                    )
                )
        rows.append(row)

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)
    rows.append(
        [
            InlineKeyboardButton(
                "◀️",
                callback_data=f"private_event_cal_nav_{prev_year}_{prev_month}",
            ),
            InlineKeyboardButton(" ", callback_data="private_event_cal_ignore"),
            InlineKeyboardButton(
                "▶️",
                callback_data=f"private_event_cal_nav_{next_year}_{next_month}",
            ),
        ]
    )
    rows.append(
        [InlineKeyboardButton("✏️ Edit Previous", callback_data="private_event_edit_date_preset")]
    )

    return InlineKeyboardMarkup(rows)


def parse_invitee_handles(raw_text: str) -> list[str]:
    """Parse comma-separated @handles and return normalized unique handles."""
    handles: list[str] = []
    seen: set[str] = set()
    tokens = [token.strip() for token in raw_text.split(",") if token.strip()]
    if not tokens:
        raise ValueError("No handles provided")

    for token in tokens:
        if not token.startswith("@"):
            raise ValueError("Handle must start with @")

        handle = token[1:]
        if not TELEGRAM_HANDLE_PATTERN.fullmatch(handle):
            raise ValueError("Invalid Telegram handle")

        normalized = f"@{handle.lower()}"
        if normalized not in seen:
            seen.add(normalized)
            handles.append(normalized)

    return handles


def parse_invitee_input(raw_text: str) -> tuple[list[str], bool]:
    """Parse invitee input and support @all shortcut."""
    normalized = raw_text.strip().lower()
    if normalized == "@all":
        return ["@all"], True
    return parse_invitee_handles(raw_text), False


def build_event_type_markup() -> InlineKeyboardMarkup:
    """Build event type selection keyboard."""
    return build_compact_markup(
        [
            ("Social", "private_event_type_social"),
            ("Sports", "private_event_type_sports"),
            ("Work", "private_event_type_work"),
        ],
        columns=2,
        footer=[("✏️ Edit Previous", "private_event_edit_description")],
    )


def build_duration_markup() -> InlineKeyboardMarkup:
    """Build compact duration selection keyboard."""
    options = [
        ("30m", "private_event_duration_30"),
        ("60m", "private_event_duration_60"),
        ("90m", "private_event_duration_90"),
        ("120m", "private_event_duration_120"),
        ("180m", "private_event_duration_180"),
    ]
    return build_compact_markup(
        options,
        columns=2,
        footer=[("✏️ Edit Previous", "private_event_edit_threshold")],
    )


def build_final_confirmation_markup() -> InlineKeyboardMarkup:
    """Build final confirmation keyboard with revision support."""
    keyboard = [
        [InlineKeyboardButton("✅ Confirm & Lock", callback_data="private_event_final_yes")],
        [InlineKeyboardButton("🛠 Modify", callback_data="private_event_final_edit")],
        [InlineKeyboardButton("❌ Cancel", callback_data="private_event_cancel_no")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_event_summary_text(data: dict[str, Any]) -> str:
    """Build event draft summary text."""
    scheduled_time = (
        str(data.get("scheduled_time", "TBD")).replace("T", " ")
        if data.get("scheduled_time")
        else "TBD (flexible scheduling)"
    )
    invitees = data.get("invitees", [])
    if not isinstance(invitees, list):
        invitees = []
    invite_all = bool(data.get("invite_all_members"))
    invitees_summary = (
        "all group members"
        if invite_all else f"{len(invitees)} users ({', '.join(invitees) if invitees else 'none'})"
    )
    
    location_type = str(data.get("location_type", "any")).replace("_", " ")
    budget_level = str(data.get("budget_level", "any")).replace("_", " ")
    transport_mode = str(data.get("transport_mode", "any")).replace("_", " ")
    date_preset = str(data.get("date_preset", "custom")).lower()
    time_window = str(data.get("time_window", "custom")).lower()
    date_preset_label = DATE_PRESET_LABELS.get(date_preset, date_preset.title())
    time_window_label = time_window.title()
    
    commit_by_text = "N/A"
    if isinstance(data.get("commit_by"), str):
        commit_by_text = str(data["commit_by"]).replace("T", " ")
    elif data.get("scheduled_time"):
        try:
            derived = compute_commit_by_time(
                datetime.fromisoformat(str(data["scheduled_time"]))
            )
            if derived is not None:
                commit_by_text = derived.isoformat(timespec="minutes").replace("T", " ")
        except ValueError:
            commit_by_text = "N/A"

    return (
        f"✨ *Event Summary*\n\n"
        f"Type: {data.get('event_type', 'N/A')}\n"
        f"Description: {data.get('description', 'N/A')}\n"
        f"Time: {scheduled_time}\n"
        f"Date Preset: {date_preset_label}\n"
        f"Time Window: {time_window_label}\n"
        f"Commit-By: {commit_by_text}\n"
        f"Duration: {data.get('duration_minutes', 120)} minutes\n"
        f"Location Type: {location_type.title()}\n"
        f"Budget: {budget_level.title()}\n"
        f"Transport: {transport_mode.title()}\n"
        f"Threshold: {data.get('threshold_attendance', 'N/A')}\n"
        f"Invitees: {invitees_summary}\n\n"
        "Press *Confirm & Lock* to finalize and lock this event."
    )


def _normalize_patch_invitees(values: Any) -> list[str]:
    """Normalize invitee list from patch values."""
    if not isinstance(values, list):
        return []
    normalized: list[str] = []
    for raw in values:
        text = str(raw).strip()
        if not text:
            continue
        if not text.startswith("@"):
            text = f"@{text}"
        handle = text[1:]
        if TELEGRAM_HANDLE_PATTERN.fullmatch(handle):
            normalized.append(f"@{handle.lower()}")
    deduped: list[str] = []
    seen: set[str] = set()
    for handle in normalized:
        if handle not in seen:
            seen.add(handle)
            deduped.append(handle)
    return deduped


async def _apply_final_stage_patch(
    flow_data: dict[str, Any],
    message_text: str,
) -> tuple[bool, list[str], str | None]:
    """Apply LLM-inferred patch to event draft data."""
    try:
        from ai.llm import LLMClient
        llm = LLMClient()
        try:
            patch = await llm.infer_event_draft_patch(flow_data, message_text)
        finally:
            await llm.close()
    except Exception:
        return False, [], "LLM unavailable for modifications"

    changes: list[str] = []
    warnings: list[str] = []
    changed = False

    description = patch.get("description")
    if isinstance(description, str) and description.strip():
        next_description = description.strip()[:500]
        if next_description != str(flow_data.get("description", "")):
            flow_data["description"] = next_description
            changes.append("description updated")
            changed = True

    event_type_raw = patch.get("event_type")
    if event_type_raw is not None:
        normalized = str(event_type_raw).strip().lower()
        if normalized in ALLOWED_EVENT_TYPES:
            if normalized != str(flow_data.get("event_type", "")).lower():
                flow_data["event_type"] = normalized
                changes.append(f"type set to {normalized}")
                changed = True

    threshold_raw = patch.get("threshold_attendance")
    if threshold_raw is not None:
        try:
            threshold = int(threshold_raw)
            if threshold < 1:
                warnings.append("Threshold must be at least 1.")
            else:
                flow_data["threshold_attendance"] = threshold
                changes.append(f"threshold set to {threshold}")
                changed = True
        except (TypeError, ValueError):
            warnings.append("Invalid threshold format; ignored.")

    duration_raw = patch.get("duration_minutes")
    if duration_raw is not None:
        try:
            duration = int(duration_raw)
            if duration <= 0 or duration > 720:
                warnings.append("Duration must be between 1 and 720 minutes.")
            else:
                flow_data["duration_minutes"] = duration
                changes.append(f"duration set to {duration} minutes")
                changed = True
        except (TypeError, ValueError):
            warnings.append("Invalid duration format; ignored.")

    location_raw = patch.get("location_type")
    if location_raw is not None:
        normalized_location = str(location_raw).strip().lower().replace(" ", "_")
        valid_locations = {value for _, value in LOCATION_PRESETS}
        if normalized_location in valid_locations:
            flow_data["location_type"] = normalized_location
            changes.append(f"location type set to {normalized_location}")
            changed = True

    budget_raw = patch.get("budget_level")
    if budget_raw is not None:
        normalized_budget = str(budget_raw).strip().lower().replace(" ", "_")
        valid_budgets = {value for _, value in BUDGET_PRESETS}
        if normalized_budget in valid_budgets:
            flow_data["budget_level"] = normalized_budget
            changes.append(f"budget set to {normalized_budget}")
            changed = True

    transport_raw = patch.get("transport_mode")
    if transport_raw is not None:
        normalized_transport = str(transport_raw).strip().lower().replace(" ", "_")
        valid_transport = {value for _, value in TRANSPORT_PRESETS}
        if normalized_transport in valid_transport:
            flow_data["transport_mode"] = normalized_transport
            changes.append(f"transport set to {normalized_transport}")
            changed = True

    time_window_raw = patch.get("time_window")
    if time_window_raw is not None:
        normalized_window = str(time_window_raw).strip().lower()
        if normalized_window in TIME_WINDOWS:
            flow_data["time_window"] = normalized_window
            changes.append(f"time window set to {normalized_window}")
            changed = True

    date_preset_raw = patch.get("date_preset")
    if date_preset_raw is not None:
        normalized_preset = str(date_preset_raw).strip().lower()
        if normalized_preset in DATE_PRESET_LABELS or normalized_preset == "custom":
            flow_data["date_preset"] = normalized_preset
            changes.append(f"date preset set to {normalized_preset}")
            changed = True

    scheduled_time_iso = patch.get("scheduled_time_iso")
    if scheduled_time_iso is not None:
        try:
            parsed = datetime.fromisoformat(str(scheduled_time_iso).strip())
            flow_data["scheduled_time"] = parsed.isoformat(timespec="minutes")
            flow_data["scheduling_mode"] = "fixed"
            changes.append(f"time set to {parsed.strftime('%Y-%m-%d %H:%M')}")
            changed = True
        except ValueError:
            warnings.append("Invalid datetime format; use YYYY-MM-DDTHH:MM.")

    invitees_add = _normalize_patch_invitees(patch.get("invitees_add"))
    if invitees_add:
        if bool(flow_data.get("invite_all_members")):
            flow_data["invite_all_members"] = False
            flow_data["invitees"] = []
        existing = list(flow_data.get("invitees", []))
        for handle in invitees_add:
            if handle not in existing:
                existing.append(handle)
        flow_data["invitees"] = existing
        changes.append(f"added invitees: {', '.join(invitees_add)}")
        changed = True

    invitees_remove = _normalize_patch_invitees(patch.get("invitees_remove"))
    if invitees_remove:
        existing = list(flow_data.get("invitees", []))
        reduced = [h for h in existing if h not in set(invitees_remove)]
        flow_data["invitees"] = reduced
        if flow_data.get("invite_all_members"):
            flow_data["invite_all_members"] = False
        changes.append(f"removed invitees: {', '.join(invitees_remove)}")
        changed = True

    if patch.get("invite_all_members") is True:
        flow_data["invite_all_members"] = True
        flow_data["invitees"] = ["@all"]
        changes.append("invitees set to all group members")
        changed = True
    elif patch.get("invite_all_members") is False and flow_data.get("invite_all_members"):
        flow_data["invite_all_members"] = False
        if flow_data.get("invitees") == ["@all"]:
            flow_data["invitees"] = []
        changes.append("invite-all disabled")
        changed = True

    note = patch.get("note")
    if isinstance(note, str) and note.strip():
        notes = flow_data.get("planning_notes")
        if not isinstance(notes, list):
            notes = []
        notes.append(note.strip()[:300])
        flow_data["planning_notes"] = notes[-10:]
        changes.append("added planning note")
        changed = True

    if str(flow_data.get("scheduling_mode", "fixed")) == "fixed" and not flow_data.get("scheduled_time"):
        warnings.append("Fixed mode requires a date/time before final confirm.")

    warning_text = "\n".join(f"- {w}" for w in warnings) if warnings else None
    return changed, changes, warning_text


async def handle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /private_organize_event command - start private event creation flow."""
    if not update.message or not update.effective_user:
        return

    user_id = update.effective_user.id
    user_data = context.user_data

    if user_data is None:
        await update.message.reply_text("❌ Session data unavailable.")
        return

    user_data["private_event_flow"] = {
        "stage": "description",
        "data": {
            "creator": user_id,
            "date_preset": "custom",
            "time_window": "evening",
            "location_type": "cafe",
            "budget_level": "medium",
            "transport_mode": "any",
            "planning_notes": [],
        },
    }

    await update.message.reply_text(
        "📝 *Event Description*\n\n"
        "Send a short description for the event.\n\n"
        "Example: Friendly football match at the central field.",
    )


async def handle_callback(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle callback queries for private event creation flow."""
    query = update.callback_query
    if not query:
        return

    await query.answer()

    data = query.data
    user_data = context.user_data

    if user_data is None:
        await query.edit_message_text("❌ Session data unavailable.")
        return

    event_flow_raw = user_data.get("private_event_flow")
    event_flow: dict[str, Any] = (
        event_flow_raw if isinstance(event_flow_raw, dict) else {}
    )
    if not event_flow:
        await query.edit_message_text(
            "❌ Event setup session expired. Please run /private_organize_event again."
        )
        return
    flow_data = event_flow.get("data")
    if not isinstance(flow_data, dict):
        flow_data = {}
        event_flow["data"] = flow_data

    if data and data.startswith("private_event_edit_"):
        target = data.replace("private_event_edit_", "")
        scheduling_mode = str(flow_data.get("scheduling_mode", "fixed"))
        
        if target == "description":
            event_flow["stage"] = "description"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "📝 *Edit Description*\n\nSend a new event description."
            )
        elif target == "type":
            event_flow["stage"] = "type"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "📋 *Event Type*\n\nChoose event type:",
                reply_markup=build_compact_markup(
                    [
                        ("Social", "private_event_type_social"),
                        ("Sports", "private_event_type_sports"),
                        ("Work", "private_event_type_work"),
                    ],
                    columns=2,
                    footer=[("✏️ Edit Previous", "private_event_edit_description")],
                ),
            )
        elif target == "date_preset":
            event_flow["stage"] = "date_preset"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "📅 *Quick Date Selection*\n\nChoose a date preset:",
                reply_markup=build_date_preset_markup(),
            )
        elif target == "time_window":
            event_flow["stage"] = "time_window"
            user_data["private_event_flow"] = event_flow
            selected_date = flow_data.get("scheduled_date", "N/A")
            await query.edit_message_text(
                f"⏰ *Time Window*\n\nDate: {selected_date}\nChoose a window:",
                reply_markup=build_time_window_markup(),
            )
        elif target == "threshold":
            event_flow["stage"] = "threshold"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "👥 *Attendance Threshold*\n\nSet minimum attendance:",
                reply_markup=build_threshold_markup("private_event_edit_type"),
            )
        elif target == "duration":
            event_flow["stage"] = "duration"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "⏳ *Duration*\n\nSelect event duration:",
                reply_markup=build_duration_markup(),
            )
        elif target == "location":
            event_flow["stage"] = "location"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "📍 *Location Type*\n\nPick one option:",
                reply_markup=build_location_type_markup(),
            )
        elif target == "budget":
            event_flow["stage"] = "budget"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "💳 *Budget*\n\nPick one option:",
                reply_markup=build_budget_markup(),
            )
        elif target == "transport":
            event_flow["stage"] = "transport"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "🚗 *Transport Mode*\n\nPick one option:",
                reply_markup=build_transport_markup(),
            )
        elif target == "invitees":
            event_flow["stage"] = "invitees"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                "👥 *Invitees*\n\nChoose invite mode:",
                reply_markup=build_invitee_mode_markup(),
            )
        elif target == "final":
            event_flow["stage"] = "final"
            user_data["private_event_flow"] = event_flow
            await query.edit_message_text(
                build_event_summary_text(flow_data),
                reply_markup=build_final_confirmation_markup(),
            )

    elif data and data.startswith("private_event_type_"):
        event_type = data.replace("private_event_type_", "")
        scheduling_mode = str(flow_data.get("scheduling_mode", "fixed"))
        flow_data["event_type"] = event_type
        user_data["private_event_flow"] = event_flow
        event_flow["stage"] = "date_preset"
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            f"📅 *Event Type: {event_type}*\n\n"
            "Choose a quick date preset:",
            reply_markup=build_date_preset_markup(),
        )

    elif data and data.startswith("private_event_date_preset_"):
        preset = data.replace("private_event_date_preset_", "")
        flow_data["date_preset"] = preset
        if preset == "custom":
            event_flow["stage"] = "date"
            user_data["private_event_flow"] = event_flow
            now = datetime.now()
            await query.edit_message_text(
                "📅 *Custom Date*\n\nSelect a date from the inline calendar:",
                reply_markup=build_calendar_markup(now.year, now.month),
            )
        else:
            choices = resolve_date_preset(preset)
            if not choices:
                await query.edit_message_text(
                    "❌ Could not resolve that date preset. Please try again.",
                    reply_markup=build_date_preset_markup(),
                )
                return
            if len(choices) == 1:
                selected_date = choices[0].strftime("%Y-%m-%d")
                flow_data["scheduled_date"] = selected_date
                event_flow["stage"] = "time_window"
                user_data["private_event_flow"] = event_flow
                await query.edit_message_text(
                    f"📆 *Date selected: {selected_date}*\n\nChoose a time window:",
                    reply_markup=build_time_window_markup(),
                )
            else:
                event_flow["stage"] = "date_options"
                user_data["private_event_flow"] = event_flow
                await query.edit_message_text(
                    f"📆 *{DATE_PRESET_LABELS.get(preset, preset.title())}*\n\nPick a specific date:",
                    reply_markup=build_date_options_markup(choices, preset),
                )

    elif data and data.startswith("private_event_date_pick_"):
        token = data.replace("private_event_date_pick_", "")
        try:
            picked = datetime.strptime(token, "%Y%m%d").date()
        except ValueError:
            await query.edit_message_text("❌ Invalid date option selected.")
            return
        selected_date = picked.strftime("%Y-%m-%d")
        flow_data["scheduled_date"] = selected_date
        event_flow["stage"] = "time_window"
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            f"📆 *Date selected: {selected_date}*\n\nChoose a time window:",
            reply_markup=build_time_window_markup(),
        )

    elif data and data.startswith("private_event_cal_"):
        await handle_private_calendar_callback(query, context, event_flow, flow_data)

    elif data and data.startswith("private_event_time_window_"):
        window = data.replace("private_event_time_window_", "")
        if window not in TIME_WINDOWS:
            await query.edit_message_text("❌ Unsupported time window.")
            return
        flow_data["time_window"] = window
        event_flow["stage"] = "time_option"
        user_data["private_event_flow"] = event_flow
        selected_date = flow_data.get("scheduled_date", "N/A")
        await query.edit_message_text(
            f"⏰ *{window.title()} window*\n\nDate: {selected_date}\nPick a start time:",
            reply_markup=build_time_options_markup(window),
        )

    elif data == "private_event_time_manual":
        event_flow["stage"] = "time_manual"
        user_data["private_event_flow"] = event_flow
        selected_date = flow_data.get("scheduled_date", "N/A")
        await query.edit_message_text(
            f"⌨️ *Manual Time Entry*\n\nDate: {selected_date}\n"
            "Send time in format `HH:MM` (e.g., `18:30`)."
        )

    elif data and data.startswith("private_event_time_option_"):
        option = data.replace("private_event_time_option_", "")
        if len(option) != 4 or not option.isdigit():
            await query.edit_message_text("❌ Invalid time option.")
            return
        hour = int(option[:2])
        minute = int(option[2:])
        scheduled_date = flow_data.get("scheduled_date")
        if not isinstance(scheduled_date, str):
            await query.edit_message_text(
                "❌ Event date is missing. Please pick date again.",
                reply_markup=build_date_preset_markup(),
            )
            return
        try:
            parsed_date = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
            scheduled_time = datetime.combine(
                parsed_date,
                datetime.strptime(f"{hour:02d}:{minute:02d}", "%H:%M").time(),
            )
        except ValueError:
            await query.edit_message_text("❌ Failed to parse selected time.")
            return
        flow_data["scheduled_time"] = scheduled_time.isoformat(timespec="minutes")
        event_flow["stage"] = "threshold"
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            f"⏱️ *Time: {scheduled_time.strftime('%Y-%m-%d %H:%M')}*\n\n"
            "What is the minimum attendance threshold?",
            reply_markup=build_threshold_markup("private_event_edit_time_window"),
        )

    elif data and data.startswith("private_event_threshold_"):
        threshold = int(data.replace("private_event_threshold_", ""))
        event_flow["stage"] = "duration"
        flow_data["threshold_attendance"] = threshold
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            f"✅ *Threshold: {threshold}*\n\nSelect event duration:",
            reply_markup=build_duration_markup(),
        )

    elif data and data.startswith("private_event_duration_"):
        duration = int(data.replace("private_event_duration_", ""))
        event_flow["stage"] = "location"
        flow_data["duration_minutes"] = duration
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            f"⏳ *Duration: {duration} minutes*\n\nSelect location type:",
            reply_markup=build_location_type_markup(),
        )

    elif data and data.startswith("private_event_location_"):
        location_type = data.replace("private_event_location_", "")
        flow_data["location_type"] = location_type
        event_flow["stage"] = "budget"
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            f"📍 *Location: {location_type.replace('_', ' ').title()}*\n\nSelect budget:",
            reply_markup=build_budget_markup(),
        )

    elif data and data.startswith("private_event_budget_"):
        budget_level = data.replace("private_event_budget_", "")
        flow_data["budget_level"] = budget_level
        event_flow["stage"] = "transport"
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            f"💳 *Budget: {budget_level.title()}*\n\nSelect transport mode:",
            reply_markup=build_transport_markup(),
        )

    elif data and data.startswith("private_event_transport_"):
        transport_mode = data.replace("private_event_transport_", "")
        flow_data["transport_mode"] = transport_mode
        event_flow["stage"] = "invitees"
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            f"🚗 *Transport: {transport_mode.replace('_', ' ').title()}*\n\nChoose invite mode:",
            reply_markup=build_invitee_mode_markup(),
        )

    elif data == "private_event_invite_all":
        event_flow["stage"] = "final"
        flow_data["invitees"] = ["@all"]
        flow_data["invite_all_members"] = True
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            build_event_summary_text(flow_data),
            reply_markup=build_final_confirmation_markup(),
        )

    elif data == "private_event_invite_custom":
        event_flow["stage"] = "invitees"
        user_data["private_event_flow"] = event_flow
        await query.edit_message_text(
            "✍️ *Custom Invitees*\n\n"
            "Enter comma-separated handles.\n"
            "Example: @alice, @bob_builder\n"
            "Or send @all",
            reply_markup=build_compact_markup(
                [],
                columns=1,
                footer=[("✏️ Edit Previous", "private_event_edit_transport")],
            ),
        )

    elif data == "private_event_final_yes":
        await finalize_private_event(query, context)
    elif data == "private_event_final_edit":
        await query.edit_message_text(
            "🛠 Send your modification in natural language.\n\n"
            "Examples:\n"
            "- Change time to 2026-03-10 19:30\n"
            "- Make duration 90 minutes\n"
            "- Increase threshold to 5\n"
            "- Set location to outdoor and budget to low\n"
            "- Add @alice and remove @bob"
        )
    elif data and data.startswith("private_event_cancel_"):
        user_data.pop("private_event_flow", None)
        await query.edit_message_text("❌ Event creation cancelled.")


async def handle_private_message(
    update: Update, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Handle text messages during private event creation flow."""
    if not update.message or not update.effective_user:
        return

    user_data = context.user_data
    if user_data is None:
        return

    event_flow_raw = user_data.get("private_event_flow")
    if not isinstance(event_flow_raw, dict) or not event_flow_raw:
        return

    event_flow: dict[str, Any] = event_flow_raw
    flow_data = event_flow.get("data")
    if not isinstance(flow_data, dict):
        flow_data = {}
        event_flow["data"] = flow_data

    stage = event_flow.get("stage")
    user_id = update.effective_user.id

    if stage == "description":
        text = update.message.text
        if not text or not text.strip():
            await update.message.reply_text(
                "❌ Description cannot be empty. Please send a short description."
            )
            return
        description = text.strip()
        if len(description) > 500:
            await update.message.reply_text(
                "❌ Description is too long. Keep it under 500 characters."
            )
            return

        flow_data["description"] = description
        event_flow["stage"] = "type"
        user_data["private_event_flow"] = event_flow

        await update.message.reply_text(
            "📋 *Event Type*\n\n"
            "What type of event would you like to organize?",
            reply_markup=build_event_type_markup(),
        )

    elif stage == "time_manual":
        text = update.message.text
        if text is None:
            await update.message.reply_text(
                "❌ Please send time as text in format: HH:MM"
            )
            return

        scheduled_date = flow_data.get("scheduled_date")
        if not isinstance(scheduled_date, str):
            await update.message.reply_text(
                "❌ Event date is missing. Please reselect date from calendar."
            )
            return

        try:
            parsed_time = datetime.strptime(text.strip(), "%H:%M").time()
            parsed_date = datetime.strptime(scheduled_date, "%Y-%m-%d").date()
            scheduled_time = datetime.combine(parsed_date, parsed_time)
            event_flow["stage"] = "threshold"
            flow_data["scheduled_time"] = scheduled_time.isoformat()
            user_data["private_event_flow"] = event_flow

            await update.message.reply_text(
                f"⏱️ *Time: {scheduled_time.strftime('%Y-%m-%d %H:%M')}*\n\n"
                "What is the minimum attendance threshold?",
                reply_markup=build_threshold_markup("private_event_edit_time_window"),
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid time format. Please use: HH:MM"
            )

    elif stage == "invitees":
        text = update.message.text
        if text is None:
            await update.message.reply_text(
                "❌ Invalid input. Please enter comma-separated handles like @alice, @bob."
            )
            return

        try:
            invitees, invite_all = parse_invitee_input(text)
            event_flow["stage"] = "final"
            flow_data["invitees"] = invitees
            flow_data["invite_all_members"] = invite_all
            flow_data["creator"] = user_id
            user_data["private_event_flow"] = event_flow

            data = flow_data
            await update.message.reply_text(
                build_event_summary_text(data),
                reply_markup=build_final_confirmation_markup(),
            )
        except ValueError:
            await update.message.reply_text(
                "❌ Invalid handle list. Use comma-separated @handles.\n"
                "Example: @alice, @bob_builder\n"
                "Or use: @all",
                reply_markup=build_compact_markup(
                    [],
                    columns=1,
                    footer=[("✏️ Edit Previous", "private_event_edit_transport")],
                ),
            )

    elif stage == "final":
        text = (update.message.text or "").strip()
        if not text:
            await update.message.reply_text(
                "❌ Send text modifications, or press Confirm/Cancel."
            )
            return

        changed, changes, warning_text = await _apply_final_stage_patch(
            flow_data=flow_data,
            message_text=text,
        )
        user_data["private_event_flow"] = event_flow
        if not changed:
            await update.message.reply_text(
                "⚠️ I could not apply any clear modification.\n"
                "Try specific edits like: `set time to 2026-03-10 19:30`."
            )
            return

        revision_lines = "\n".join(f"- {item}" for item in changes)
        warning_block = f"\nWarnings:\n{warning_text}\n" if warning_text else ""
        await update.message.reply_text(
            "🔁 *Draft Updated*\n"
            f"{revision_lines}\n"
            f"{warning_block}\n"
            f"{build_event_summary_text(flow_data)}",
            reply_markup=build_final_confirmation_markup(),
        )


async def handle_private_calendar_callback(
    query: CallbackQuery,
    context: ContextTypes.DEFAULT_TYPE,
    event_flow: dict[str, Any],
    flow_data: dict[str, Any],
) -> None:
    """Handle inline calendar callbacks for date selection."""
    data = query.data
    if not data:
        return

    if data == "private_event_cal_ignore":
        return

    if data.startswith("private_event_cal_nav_") or data.startswith("private_event_cal_open_"):
        parts = data.split("_")
        if len(parts) < 5:
            return
        try:
            year = int(parts[-2])
            month = int(parts[-1])
            if month < 1 or month > 12:
                return
        except ValueError:
            return

        event_type = str(flow_data.get("event_type", "N/A"))
        await query.edit_message_text(
            f"📅 *Event Type: {event_type}*\n\n"
            "Select a date from the inline calendar:",
            reply_markup=build_calendar_markup(year, month),
        )
        return

    if data.startswith("private_event_cal_day_"):
        parts = data.split("_")
        if len(parts) != 6:
            return
        try:
            year = int(parts[3])
            month = int(parts[4])
            day = int(parts[5])
            selected = datetime(year, month, day)
        except ValueError:
            return

        selected_date = selected.strftime("%Y-%m-%d")
        flow_data["scheduled_date"] = selected_date
        flow_data["date_preset"] = "custom"
        event_flow["stage"] = "time_window"
        context.user_data["private_event_flow"] = event_flow

        await query.edit_message_text(
            f"📆 *Date selected: {selected_date}*\n\n"
            "Choose a time window:",
            reply_markup=build_time_window_markup(),
        )


async def finalize_private_event(
    query: CallbackQuery, context: ContextTypes.DEFAULT_TYPE
) -> None:
    """Finalize and create the private event in database."""
    if context.user_data is None:
        await query.edit_message_text("❌ Session data unavailable.")
        return

    event_flow_raw = context.user_data.get("private_event_flow")
    if not isinstance(event_flow_raw, dict):
        await query.edit_message_text("❌ Event flow not found.")
        return

    event_flow: dict[str, Any] = event_flow_raw
    data_raw = event_flow.get("data")
    if not isinstance(data_raw, dict):
        await query.edit_message_text("❌ Event flow data is invalid.")
        return
    data: dict[str, Any] = data_raw

    scheduled_time_raw = data.get("scheduled_time")
    scheduling_mode = str(data.get("scheduling_mode", "fixed"))
    if scheduling_mode != "flexible" and not isinstance(scheduled_time_raw, str):
        await query.edit_message_text("❌ Event time is missing.")
        return

    creator_id = int(data.get("creator", query.from_user.id))

    async with get_session(settings.db_url) as session:
        candidate_time = (
            datetime.fromisoformat(scheduled_time_raw)
            if isinstance(scheduled_time_raw, str)
            else None
        )
        commit_by = compute_commit_by_time(candidate_time)
        duration_minutes = int(data.get("duration_minutes", 120))
        
        try:
            from bot.common.scheduling import find_user_event_conflict
            conflict = await find_user_event_conflict(
                session=session,
                telegram_user_id=creator_id,
                start_time=candidate_time,
                duration_minutes=duration_minutes,
            )
            if conflict:
                await query.edit_message_text(
                    "❌ Creator has a conflicting event.\n"
                    f"Conflicting Event ID: {conflict.event_id}\n"
                    f"Time: {conflict.scheduled_time}\n"
                    f"Duration: {conflict.duration_minutes or 120} minutes"
                )
                return
        except ImportError:
            pass

        event = Event(
            group_id=0,
            event_type=data.get("event_type", "general"),
            description=data.get("description"),
            organizer_telegram_user_id=creator_id,
            scheduled_time=candidate_time,
            commit_by=commit_by,
            duration_minutes=duration_minutes,
            threshold_attendance=data.get("threshold_attendance", 5),
            attendance_list=[f"{creator_id}:interested"],
            planning_prefs={
                "date_preset": data.get("date_preset"),
                "time_window": data.get("time_window"),
                "location_type": data.get("location_type"),
                "budget_level": data.get("budget_level"),
                "transport_mode": data.get("transport_mode"),
            },
            state="confirmed",
            locked_at=datetime.utcnow(),
        )
        session.add(event)
        await session.commit()
        await session.refresh(event)

    context.user_data.pop("private_event_flow", None)

    keyboard = [
        [
            InlineKeyboardButton(
                "View Event", callback_data=f"private_event_details_{event.event_id}"
            )
        ],
    ]
    
    bot_username = context.bot.username if context.bot else None
    avail_link = f"https://t.me/{bot_username}?start=avail_{event.event_id}" if bot_username else None
    feedback_link = f"https://t.me/{bot_username}?start=feedback_{event.event_id}" if bot_username else None
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    scheduled_time = (
        str(data.get("scheduled_time", "TBD")).replace("T", " ")
        if data.get("scheduled_time")
        else "TBD (flexible scheduling)"
    )
    
    commit_by_text = (
        commit_by.isoformat(timespec="minutes").replace("T", " ")
        if commit_by is not None
        else "N/A"
    )
    
    invitees_summary = (
        "all group members"
        if data.get("invite_all_members")
        else f"{len(data.get('invitees', []))} users"
    )
    
    location_text = str(data.get("location_type", "any")).replace("_", " ").title()
    budget_text = str(data.get("budget_level", "any")).replace("_", " ").title()
    transport_text = str(data.get("transport_mode", "any")).replace("_", " ").title()
    date_preset_text = DATE_PRESET_LABELS.get(
        str(data.get("date_preset", "custom")),
        str(data.get("date_preset", "custom")).title(),
    )
    time_window_text = str(data.get("time_window", "custom")).title()

    await query.edit_message_text(
        f"✅ *Event Created & Locked!*\n\n"
        f"Event ID: {event.event_id}\n"
        f"Type: {data.get('event_type', 'N/A')}\n"
        f"Description: {data.get('description', 'N/A')}\n"
        f"Time: {scheduled_time}\n"
        f"Commit-By: {commit_by_text}\n"
        f"Date Preset: {date_preset_text}\n"
        f"Time Window: {time_window_text}\n"
        f"Duration: {data.get('duration_minutes', 120)} minutes\n"
        f"Mode: {scheduling_mode}\n"
        f"Location Type: {location_text}\n"
        f"Budget: {budget_text}\n"
        f"Transport: {transport_text}\n"
        f"Threshold: {data.get('threshold_attendance', 'N/A')}\n"
        f"Invitees: {invitees_summary}\n\n"
        f"✅ Event has been automatically locked.\n"
        f"Status: Locked - No further changes allowed.\n\n"
        f"Event Admin: {query.from_user.mention_html() if query.from_user else 'Unknown'}",
        reply_markup=reply_markup,
    )