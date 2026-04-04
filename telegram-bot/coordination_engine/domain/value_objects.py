"""Value objects — immutable, equality by value, self-validating."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum


# ---------------------------------------------------------------------------
# Enums (used across the domain)
# ---------------------------------------------------------------------------

class EventType(Enum):
    SOCIAL = "social"
    SPORTS = "sports"
    WORK = "work"


class EventState(Enum):
    PROPOSED = "proposed"
    INTERESTED = "interested"
    CONFIRMED = "confirmed"
    LOCKED = "locked"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class ParticipantStatus(Enum):
    JOINED = "joined"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"


class ParticipantRole(Enum):
    ORGANIZER = "organizer"
    PARTICIPANT = "participant"
    OBSERVER = "observer"


class ConstraintType(Enum):
    IF_JOINS = "if_joins"
    IF_ATTENDS = "if_attends"
    UNLESS_JOINS = "unless_joins"


class SchedulingMode(Enum):
    FIXED = "fixed"
    FLEXIBLE = "flexible"


class LocationType(Enum):
    HOME = "home"
    OUTDOOR = "outdoor"
    CAFE = "cafe"
    OFFICE = "office"
    GYM = "gym"


class BudgetLevel(Enum):
    FREE = "free"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TransportMode(Enum):
    WALK = "walk"
    PUBLIC_TRANSIT = "public_transit"
    DRIVE = "drive"
    ANY = "any"


# ---------------------------------------------------------------------------
# Telegram Handle
# ---------------------------------------------------------------------------

_HANDLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]{4,31}$")


@dataclass(frozen=True)
class TelegramHandle:
    """Validated Telegram username."""

    value: str

    def __post_init__(self) -> None:
        raw = self.value.lstrip("@").lower()
        if not _HANDLE_RE.match(raw):
            raise ValueError(f"Invalid Telegram handle: {self.value}")
        object.__setattr__(self, "value", raw)

    def __str__(self) -> str:
        return f"@{self.value}"


# ---------------------------------------------------------------------------
# Time Window
# ---------------------------------------------------------------------------

class TimeWindow(Enum):
    EARLY_MORNING = "early-morning"
    MORNING = "morning"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"


# ---------------------------------------------------------------------------
# Date Preset
# ---------------------------------------------------------------------------

class DatePreset(Enum):
    TODAY = "today"
    TOMORROW = "tomorrow"
    WEEKEND = "weekend"
    NEXT_WEEK = "nextweek"
    CUSTOM = "custom"
