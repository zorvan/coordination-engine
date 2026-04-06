"""
Unit tests — service-level pure logic (no DB).
Phase 2: Pure Unit Tests per TEST_SYSTEM_PLAN_v3.2 §4A.
"""
from __future__ import annotations

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from tests.fixtures.factories import (
    make_event, make_user, make_fragment, make_waitlist,
    make_participant, make_group_stats,
    ParticipantStatus,
)


class TestWaitlistFIFOOrdering:
    """FIFO by added_at only — never by user history."""

    @pytest.mark.asyncio
    async def test_next_waitlist_is_earliest_added_at(self) -> None:
        from bot.services import WaitlistService

        session = MagicMock()
        bot = MagicMock()
        svc = WaitlistService(session, bot)

        older = make_waitlist(1, 111, added_at=datetime.utcnow() - timedelta(minutes=10))

        result = MagicMock()
        result.scalar_one_or_none.return_value = older
        session.execute = AsyncMock(return_value=result)

        next_up = await svc.get_next_waitlisted(1)
        # Ordering should be by added_at ASC — older first
        assert next_up is older


class TestWaitlistOfferDuration:
    """Time-scaled response windows: >24h→120min, <24h→30min, <2h→15min."""

    @pytest.mark.asyncio
    async def test_far_future_gets_120_minutes(self) -> None:
        from bot.services import WaitlistService
        session = MagicMock()
        bot = MagicMock()
        svc = WaitlistService(session, bot)

        evt = make_event(scheduled_time=datetime.utcnow() + timedelta(hours=48))
        result = MagicMock()
        result.scalar_one_or_none.return_value = evt
        session.execute = AsyncMock(return_value=result)

        duration = await svc._compute_offer_duration(1)
        assert duration == 120

    @pytest.mark.asyncio
    async def test_near_future_gets_30_minutes(self) -> None:
        from bot.services import WaitlistService
        session = MagicMock()
        bot = MagicMock()
        svc = WaitlistService(session, bot)

        evt = make_event(scheduled_time=datetime.utcnow() + timedelta(hours=12))
        result = MagicMock()
        result.scalar_one_or_none.return_value = evt
        session.execute = AsyncMock(return_value=result)

        duration = await svc._compute_offer_duration(1)
        assert duration == 30

    @pytest.mark.asyncio
    async def test_imminent_gets_15_minutes(self) -> None:
        from bot.services import WaitlistService
        session = MagicMock()
        bot = MagicMock()
        svc = WaitlistService(session, bot)

        evt = make_event(scheduled_time=datetime.utcnow() + timedelta(minutes=60))
        result = MagicMock()
        result.scalar_one_or_none.return_value = evt
        session.execute = AsyncMock(return_value=result)

        duration = await svc._compute_offer_duration(1)
        assert duration == 15

    @pytest.mark.asyncio
    async def test_get_waitlist_returns_fifo_entries(self) -> None:
        from bot.services import WaitlistService

        session = MagicMock()
        bot = MagicMock()
        svc = WaitlistService(session, bot)

        older = make_waitlist(1, 111, added_at=datetime.utcnow() - timedelta(minutes=10))
        newer = make_waitlist(1, 222, added_at=datetime.utcnow() - timedelta(minutes=5))
        result = MagicMock()
        result.scalars.return_value.all.return_value = [older, newer]
        session.execute = AsyncMock(return_value=result)

        entries = await svc.get_waitlist(1)
        assert entries == [older, newer]


class TestEventMemoryServiceQualification:
    """Fragment qualification: word_count ≤ max_words."""

    @pytest.mark.asyncio
    async def test_short_fragment_qualifies_for_hook(self) -> None:
        from bot.services.event_memory_service import EventMemoryService

        session = MagicMock()
        bot = MagicMock()
        svc = EventMemoryService(bot, session)

        memory_obj = MagicMock()
        memory_obj.fragments = [
            make_fragment("Good vibes"),          # 2 words
            make_fragment("A really long fragment that exceeds twelve words easily and should not be chosen"),  # 14+ words
        ]

        result = MagicMock()
        result.scalar_one_or_none.return_value = memory_obj
        session.execute = AsyncMock(return_value=result)

        hook = await svc.get_memory_hook(1, "social", max_words=12)
        assert hook == "Good vibes"

    @pytest.mark.asyncio
    async def test_too_long_fragment_excluded(self) -> None:
        from bot.services.event_memory_service import EventMemoryService

        session = MagicMock()
        bot = MagicMock()
        svc = EventMemoryService(bot, session)

        memory_obj = MagicMock()
        memory_obj.fragments = [
            make_fragment("This is a way too long fragment that definitely exceeds the limit of twelve words"),
        ]

        result = MagicMock()
        result.scalar_one_or_none.return_value = memory_obj
        session.execute = AsyncMock(return_value=result)

        hook = await svc.get_memory_hook(1, "social", max_words=12)
        assert hook is None


class TestReflexiveFragmentPreference:
    """Lineage door prefers difficulty/adaptation fragments."""

    @pytest.mark.asyncio
    async def test_reflexive_fragment_selected(self) -> None:
        from bot.services.event_memory_service import EventMemoryService

        session = MagicMock()
        bot = MagicMock()
        svc = EventMemoryService(bot, session)

        memory_obj = MagicMock()
        memory_obj.fragments = [
            make_fragment("Amazing day everyone showed up"),  # triumph
            make_fragment("Rain caught us but we adapted anyway"),  # reflexive
        ]

        result = MagicMock()
        result.scalar_one_or_none.return_value = memory_obj
        session.execute = AsyncMock(return_value=result)

        fragment = await svc.get_lineage_door_fragment(1, "outdoor")
        assert fragment == "Rain caught us but we adapted anyway"

    @pytest.mark.asyncio
    async def test_falls_back_to_shortest_when_no_reflexive(self) -> None:
        from bot.services.event_memory_service import EventMemoryService

        session = MagicMock()
        bot = MagicMock()
        svc = EventMemoryService(bot, session)

        memory_obj = MagicMock()
        memory_obj.fragments = [
            make_fragment("Great time"),
            make_fragment("Everyone had wonderful celebrations"),
        ]

        result = MagicMock()
        result.scalar_one_or_none.return_value = memory_obj
        session.execute = AsyncMock(return_value=result)

        fragment = await svc.get_lineage_door_fragment(1, "social")
        assert fragment == "Great time"

    @pytest.mark.asyncio
    async def test_no_fragment_returns_none(self) -> None:
        from bot.services.event_memory_service import EventMemoryService

        session = MagicMock()
        bot = MagicMock()
        svc = EventMemoryService(bot, session)

        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result)

        fragment = await svc.get_lineage_door_fragment(1, "sports")
        assert fragment is None


class TestFailurePattern:
    """Group-level only — no individual attribution."""

    @pytest.mark.asyncio
    async def test_three_failures_surface(self) -> None:
        from bot.services.group_event_type_stats_service import GroupEventTypeStatsService

        session = MagicMock()
        svc = GroupEventTypeStatsService(session)

        stats = make_group_stats(1, "sports", attempt_count=4, completed_count=1, last_dropout_point=3)
        result = MagicMock()
        result.scalar_one_or_none.return_value = stats
        session.execute = AsyncMock(return_value=result)

        pattern = await svc.get_failure_pattern(1, "sports")
        assert pattern is not None
        assert pattern["attempt_count"] == 4
        assert pattern["completed_count"] == 1
        assert pattern["failed_count"] == 3
        assert pattern["last_dropout_point"] == 3

    @pytest.mark.asyncio
    async def test_two_failures_hidden(self) -> None:
        from bot.services.group_event_type_stats_service import GroupEventTypeStatsService

        session = MagicMock()
        svc = GroupEventTypeStatsService(session)

        stats = make_group_stats(1, "sports", attempt_count=2, completed_count=0, last_dropout_point=2)
        result = MagicMock()
        result.scalar_one_or_none.return_value = stats
        session.execute = AsyncMock(return_value=result)

        pattern = await svc.get_failure_pattern(1, "sports")
        assert pattern is None

    @pytest.mark.asyncio
    async def test_no_stats_returns_none(self) -> None:
        from bot.services.group_event_type_stats_service import GroupEventTypeStatsService

        session = MagicMock()
        svc = GroupEventTypeStatsService(session)

        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=result)

        pattern = await svc.get_failure_pattern(1, "sports")
        assert pattern is None


class TestConfirmationHelpers:
    """Modification reset should operate on normalized participant rows only."""

    @pytest.mark.asyncio
    async def test_invalidate_confirmations_downgrades_confirmed_participants(self) -> None:
        from bot.common.confirmation import invalidate_confirmations_and_notify

        confirmed = make_participant(1, 111, status=ParticipantStatus.confirmed)
        joined = make_participant(1, 222, status=ParticipantStatus.joined)
        event = make_event()
        event.event_id = 1
        event.participants = [confirmed, joined]
        bot = MagicMock()
        bot.send_message = AsyncMock()
        context = MagicMock(bot=bot)

        invalidated = await invalidate_confirmations_and_notify(
            context=context,
            event=event,
            reason="time changed",
        )

        assert invalidated == 1
        assert confirmed.status == ParticipantStatus.joined
        assert confirmed.confirmed_at is None
        assert event.state == "interested"
        bot.send_message.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_notify_attendees_of_modification_skips_cancelled(self) -> None:
        from bot.common.confirmation import notify_attendees_of_modification

        joined = make_participant(1, 111, status=ParticipantStatus.joined)
        confirmed = make_participant(1, 222, status=ParticipantStatus.confirmed)
        cancelled = make_participant(1, 333, status=ParticipantStatus.cancelled)
        event = make_event()
        event.event_id = 1
        event.participants = [joined, confirmed, cancelled]
        bot = MagicMock()
        bot.send_message = AsyncMock()
        context = MagicMock(bot=bot)

        notified = await notify_attendees_of_modification(
            context=context,
            event=event,
            reason="location changed",
        )

        assert notified == 2
        assert bot.send_message.await_count == 2
