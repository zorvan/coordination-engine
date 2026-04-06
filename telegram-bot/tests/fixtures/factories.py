"""
Test fixtures — database factories, Telegram mocks, time control, and LLM stubs.
Phase 1: Foundation per TEST_SYSTEM_PLAN_v3.2 §6.
"""
from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from db.models import (
    Base, User, Group, Event, EventParticipant,
    ParticipantStatus, ParticipantRole, EventWaitlist,
    EventMemory, GroupEventTypeStats,
)


# ---------------------------------------------------------------------------
# Database fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_session() -> MagicMock:
    """Return a MagicMock that behaves like an AsyncSession."""
    session = MagicMock()
    session.execute = AsyncMock()
    session.add = MagicMock()
    session.delete = AsyncMock()
    session.commit = AsyncMock()
    session.flush = AsyncMock()
    session.refresh = AsyncMock()
    return session


# ---------------------------------------------------------------------------
# Unique ID helpers
# ---------------------------------------------------------------------------

_next_id = 0

def _next_int() -> int:
    global _next_id
    _next_id += 1
    return _next_id

def _tg_id() -> int:
    return int(hashlib.md5(str(uuid.uuid4()).encode()).hexdigest()[:8], 16)

def _future_hours(hours: int) -> datetime:
    return datetime.utcnow() + timedelta(hours=hours)

# ---------------------------------------------------------------------------
# Object factories
# ---------------------------------------------------------------------------

def make_user(
    telegram_user_id: int | None = None,
    username: str | None = None,
    display_name: str | None = None,
    **kwargs: Any,
) -> User:
    tid = telegram_user_id or _tg_id()
    return User(
        telegram_user_id=tid,
        username=username or f"user_{tid}",
        display_name=display_name or f"User {tid}",
        **kwargs,
    )


def make_group(
    telegram_group_id: int | None = None,
    group_name: str | None = None,
    member_list: list[int] | None = None,
    **kwargs: Any,
) -> Group:
    gid = telegram_group_id or _tg_id()
    return Group(
        telegram_group_id=gid,
        group_name=group_name or f"Group {gid}",
        member_list=member_list or [],
        **kwargs,
    )


def make_event(
    group_id: int = 1,
    event_type: str = "social",
    description: str | None = None,
    organizer_telegram_user_id: int | None = None,
    state: str = "proposed",
    scheduled_time: datetime | None = None,
    min_participants: int = 2,
    target_participants: int = 4,
    collapse_at: datetime | None = None,
    **kwargs: Any,
) -> Event:
    eid = _next_int()
    return Event(
        event_id=eid,
        group_id=group_id,
        event_type=event_type,
        description=description or f"Test {event_type} event {eid}",
        organizer_telegram_user_id=organizer_telegram_user_id or _tg_id(),
        state=state,
        scheduled_time=scheduled_time,
        min_participants=min_participants,
        target_participants=target_participants,
        collapse_at=collapse_at,
        **kwargs,
    )


def make_participant(
    event_id: int,
    telegram_user_id: int,
    status: ParticipantStatus = ParticipantStatus.joined,
    role: ParticipantRole = ParticipantRole.participant,
    **kwargs: Any,
) -> EventParticipant:
    return EventParticipant(
        event_id=event_id,
        telegram_user_id=telegram_user_id,
        status=status,
        role=role,
        **kwargs,
    )


def make_waitlist(
    event_id: int,
    telegram_user_id: int,
    status: str = "waiting",
    added_at: datetime | None = None,
    expires_at: datetime | None = None,
    **kwargs: Any,
) -> EventWaitlist:
    return EventWaitlist(
        event_id=event_id,
        telegram_user_id=telegram_user_id,
        status=status,
        added_at=added_at or datetime.utcnow(),
        expires_at=expires_at,
        **kwargs,
    )


def make_event_memory(
    event_id: int,
    fragments: list[dict] | None = None,
    weave_text: str | None = None,
    **kwargs: Any,
) -> EventMemory:
    return EventMemory(
        event_id=event_id,
        fragments=fragments or [],
        weave_text=weave_text,
        **kwargs,
    )


def make_fragment(text: str, tone_tag: str = "neutral", submitted_at: datetime | None = None) -> dict:
    """Create a memory fragment dict with computed word_count."""
    return {
        "text": text,
        "contributor_hash": hashlib.sha256(text.encode()).hexdigest()[:8],
        "tone_tag": tone_tag,
        "submitted_at": (submitted_at or datetime.utcnow()).isoformat(),
        "word_count": len(text.split()),
    }


def make_group_stats(
    group_id: int,
    event_type: str,
    attempt_count: int = 0,
    completed_count: int = 0,
    last_dropout_point: int | None = None,
    **kwargs: Any,
) -> GroupEventTypeStats:
    return GroupEventTypeStats(
        group_id=group_id,
        event_type=event_type,
        attempt_count=attempt_count,
        completed_count=completed_count,
        last_dropout_point=last_dropout_point,
        **kwargs,
    )


# ---------------------------------------------------------------------------
# Fixture families (pre-built common scenarios)
# ---------------------------------------------------------------------------

@pytest.fixture
def organizer_user() -> User:
    return make_user(display_name="Organizer")


@pytest.fixture
def admin_user() -> User:
    return make_user(display_name="Admin")


@pytest.fixture
def group_member_user() -> User:
    return make_user(display_name="Member")


@pytest.fixture
def non_member_user() -> User:
    return make_user(display_name="Outsider")


@pytest.fixture
def participant_user() -> User:
    return make_user(display_name="Participant")


@pytest.fixture
def event_at_light_tier() -> Event:
    """Event 96h in the future — light tier."""
    return make_event(scheduled_time=_future_hours(96))


@pytest.fixture
def event_at_warm_tier() -> Event:
    """Event 48h in the future — warm tier."""
    return make_event(scheduled_time=_future_hours(48))


@pytest.fixture
def event_at_urgent_tier() -> Event:
    """Event 12h in the future — urgent tier."""
    return make_event(scheduled_time=_future_hours(12))


@pytest.fixture
def event_at_immediate_tier() -> Event:
    """Event 1h in the future — immediate tier."""
    return make_event(scheduled_time=_future_hours(1))


@pytest.fixture
def full_event_with_waitlist() -> dict:
    """
    Build a confirmed event with participants and a waitlist.
    Returns dict with event, participants, waitlist entries.
    """
    org = make_user(display_name="Organizer")
    p1 = make_user(display_name="Alice")
    p2 = make_user(display_name="Bob")
    w1 = make_user(display_name="Waiter1")
    w2 = make_user(display_name="Waiter2")
    evt = make_event(
        state="confirmed",
        scheduled_time=_future_hours(24),
        min_participants=2,
        target_participants=2,
        organizer_telegram_user_id=org.telegram_user_id,
    )
    org_p = make_participant(evt.event_id, org.telegram_user_id, ParticipantRole.organizer)
    alice = make_participant(evt.event_id, p1.telegram_user_id, ParticipantStatus.confirmed)
    bob = make_participant(evt.event_id, p2.telegram_user_id, ParticipantStatus.confirmed)
    wl1 = make_waitlist(evt.event_id, w1.telegram_user_id, added_at=datetime.utcnow() - timedelta(minutes=10))
    wl2 = make_waitlist(evt.event_id, w2.telegram_user_id, added_at=datetime.utcnow() - timedelta(minutes=5))
    return {
        "event": evt,
        "organizer": org,
        "participants": [org_p, alice, bob],
        "waitlist": [wl1, wl2],
        "waitlist_users": [w1, w2],
    }


@pytest.fixture
def completed_event_with_memory() -> dict:
    """Build a completed event with memory weave and fragments."""
    evt = make_event(state="completed", event_type="outdoor")
    memory = make_event_memory(
        event_id=evt.event_id,
        fragments=[
            make_fragment("Rain caught us off guard but we laughed", tone_tag="surprised"),
            make_fragment("Beautiful sunset view from the trail", tone_tag="celebration"),
            make_fragment("Almost didn't make it but we adapted anyway", tone_tag="difficult"),
        ],
        weave_text="📿 How people remember: outdoor\n\n• Almost didn't make it but we adapted anyway\n• Rain caught us off guard but we laughed\n• Beautiful sunset view from the trail",
        hashtags=["trail", "rain", "sunset"],
    )
    return {"event": evt, "memory": memory}


@pytest.fixture
def group_with_failure_pattern() -> dict:
    """Build group stats showing 3+ failed attempts."""
    stats = make_group_stats(
        group_id=1,
        event_type="sports",
        attempt_count=4,
        completed_count=1,
        last_dropout_point=3,
    )
    return {"stats": stats, "group_id": 1, "event_type": "sports"}


# ---------------------------------------------------------------------------
# Telegram bot mocks
# ---------------------------------------------------------------------------

class MockBot:
    """Minimal mock for telegram.Bot that records send_message calls."""

    def __init__(self) -> None:
        self.sent: list[dict[str, Any]] = []
        self.send_message = AsyncMock(side_effect=self._record_send)
        self.username = "test_bot"

    async def _record_send(self, chat_id: int, text: str, **kwargs: Any) -> None:
        self.sent.append({"chat_id": chat_id, "text": text, **kwargs})

    @property
    def dm_messages(self) -> list[dict[str, Any]]:
        return self.sent  # caller filters by chat_id

    def reset(self) -> None:
        self.sent.clear()
