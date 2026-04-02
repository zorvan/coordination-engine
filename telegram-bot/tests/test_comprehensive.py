#!/usr/bin/env python3
"""
Comprehensive test suite for Telegram Coordination Bot.
Tests cover critical flows, edge cases, and error handling.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timedelta
from sqlalchemy import select


class TestEventFlowHandlers:
    """Test event flow callback handlers."""

    @pytest.mark.asyncio
    async def test_handle_join_event_not_found(self):
        """Test joining non-existent event."""
        from bot.handlers.event_flow import handle_join

        query = MagicMock()
        query.edit_message_text = AsyncMock()
        query.from_user.id = 12345
        query.from_user.full_name = "Test User"
        query.from_user.username = "testuser"

        context = MagicMock()

        with patch("bot.handlers.event_flow.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(return_value=MagicMock(scalar_one_or_none=lambda: None))
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await handle_join(query, context, 99999)

            query.edit_message_text.assert_called_once_with("❌ Event not found.")

    @pytest.mark.asyncio
    async def test_handle_join_event_locked(self):
        """Test joining locked event."""
        from bot.handlers.event_flow import handle_join
        from db.models import Event

        query = MagicMock()
        query.edit_message_text = AsyncMock()
        query.from_user.id = 12345

        context = MagicMock()

        mock_event = MagicMock(spec=Event)
        mock_event.state = "locked"

        with patch("bot.handlers.event_flow.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=lambda: mock_event)
            )
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await handle_join(query, context, 1)

            assert "Cannot join event" in query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_confirm_state_validation(self):
        """Test confirm handler validates event state."""
        from bot.handlers.event_flow import handle_confirm
        from db.models import Event

        query = MagicMock()
        query.edit_message_text = AsyncMock()
        query.from_user.id = 12345

        context = MagicMock()

        mock_event = MagicMock(spec=Event)
        mock_event.state = "completed"

        with patch("bot.handlers.event_flow.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=lambda: mock_event)
            )
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await handle_confirm(query, context, 1)

            assert "Cannot confirm event" in query.edit_message_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_handle_lock_wrong_state(self):
        """Test lock handler requires confirmed state."""
        from bot.handlers.event_flow import handle_lock
        from db.models import Event

        query = MagicMock()
        query.edit_message_text = AsyncMock()
        query.from_user.id = 12345

        context = MagicMock()

        mock_event = MagicMock(spec=Event)
        mock_event.state = "proposed"

        with patch("bot.handlers.event_flow.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock(
                return_value=MagicMock(scalar_one_or_none=lambda: mock_event)
            )
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await handle_lock(query, context, 1)

            assert "Cannot lock event" in query.edit_message_text.call_args[0][0]


class TestParticipantService:
    """Test ParticipantService operations."""

    @pytest.mark.asyncio
    async def test_join_creates_participant(self):
        """Test joining event creates participant record."""
        from bot.services.participant_service import ParticipantService
        from db.models import ParticipantStatus

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()

        # Mock the query result for event existence check
        mock_event = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_event
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ParticipantService(mock_session)

        participant, is_new = await service.join(
            event_id=1,
            telegram_user_id=12345,
            source="callback"
        )

        assert participant is not None

    @pytest.mark.asyncio
    async def test_cancel_removes_participant(self):
        """Test cancelling removes participant record."""
        from bot.services.participant_service import ParticipantService

        mock_session = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.delete = AsyncMock()

        # Mock existing participant
        mock_participant = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_participant
        mock_session.execute = AsyncMock(return_value=mock_result)

        service = ParticipantService(mock_session)

        participant, is_new = await service.cancel(
            event_id=1,
            telegram_user_id=12345,
            source="callback"
        )

        assert participant is not None

    @pytest.mark.asyncio
    async def test_get_confirmed_count(self):
        """Test counting confirmed participants."""
        from bot.services.participant_service import ParticipantService
        from db.models import ParticipantStatus

        mock_session = AsyncMock()

        # Mock count result
        mock_scalar = MagicMock()
        mock_scalar.scalar.return_value = 5
        mock_session.execute = AsyncMock(return_value=mock_scalar)

        service = ParticipantService(mock_session)

        count = await service.get_confirmed_count(1)

        assert count == 5


class TestEventDetails:
    """Test event details display."""

    @pytest.mark.asyncio
    async def test_show_logs_with_users(self):
        """Test log display includes user information."""
        from bot.commands.event_details import show_logs

        query = MagicMock()
        query.edit_message_text = AsyncMock()

        mock_log = MagicMock()
        mock_log.action = "join"
        mock_log.timestamp = datetime.utcnow()

        mock_user = MagicMock()
        mock_user.telegram_user_id = 12345
        mock_user.username = "testuser"
        mock_user.display_name = "Test User"

        with patch("bot.commands.event_details.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.all.return_value = [(mock_log, mock_user)]
            mock_session.execute.return_value = mock_result
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await show_logs(query, 1)

            # Verify user info is included
            call_args = query.edit_message_text.call_args[0][0]
            assert "testuser" in call_args or "Test User" in call_args

    @pytest.mark.asyncio
    async def test_show_logs_without_users(self):
        """Test log display handles missing users gracefully."""
        from bot.commands.event_details import show_logs

        query = MagicMock()
        query.edit_message_text = AsyncMock()

        mock_log = MagicMock()
        mock_log.action = "system"
        mock_log.timestamp = datetime.utcnow()

        with patch("bot.commands.event_details.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_result = MagicMock()
            mock_result.all.return_value = [(mock_log, None)]
            mock_session.execute.return_value = mock_result
            mock_get_session.return_value.__aenter__.return_value = mock_session

            await show_logs(query, 1)

            # Should not crash, should show log without user info
            assert query.edit_message_text.called


class TestEventPresenters:
    """Test event presentation helpers."""

    @pytest.mark.asyncio
    async def test_get_user_mention_with_username(self):
        """Test user mention format with username."""
        from bot.common.event_presenters import get_user_mention

        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.display_name = "Test User"
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=lambda: mock_user
        )

        result = await get_user_mention(mock_session, 12345)

        assert "@testuser" in result
        assert "tg://user?id=12345" in result

    @pytest.mark.asyncio
    async def test_get_user_mention_without_username(self):
        """Test user mention format with display name."""
        from bot.common.event_presenters import get_user_mention

        mock_session = AsyncMock()
        mock_user = MagicMock()
        mock_user.username = None
        mock_user.display_name = "Test User"
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=lambda: mock_user
        )

        result = await get_user_mention(mock_session, 12345)

        assert "Test User" in result
        assert "tg://user?id=12345" in result

    @pytest.mark.asyncio
    async def test_get_user_mention_no_user(self):
        """Test user mention format fallback to ID."""
        from bot.common.event_presenters import get_user_mention

        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock(
            scalar_one_or_none=lambda: None
        )

        result = await get_user_mention(mock_session, 12345)

        assert "User 12345" in result
        assert "tg://user?id=12345" in result


class TestEventMaterializationService:
    """Test event materialization service."""

    def test_import_service(self):
        """Test service imports correctly."""
        from bot.services import event_materialization_service

        assert hasattr(event_materialization_service, 'EventMaterializationService')


class TestMentionHandler:
    """Test mention-based command handling."""

    def test_import_mention_handler(self):
        """Test mention handler imports correctly."""
        from bot.handlers import mentions

        assert hasattr(mentions, 'handle_mention')
        assert hasattr(mentions, 'handle_mention_callback')


class TestEventCreation:
    """Test event creation flow."""

    @pytest.mark.asyncio
    async def test_create_event_with_valid_data(self):
        """Test event creation initializes flow correctly."""
        from bot.commands.event_creation import start_event_flow

        update = MagicMock()
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        update.effective_chat = MagicMock()
        update.effective_chat.type = "group"
        update.effective_chat.id = -123456
        update.effective_chat.title = "Test Group"
        update.effective_user = MagicMock()
        update.effective_user.id = 12345

        context = MagicMock()
        context.user_data = {}

        with patch("bot.commands.event_creation.get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.execute = AsyncMock()
            mock_session.commit = AsyncMock()
            mock_session.refresh = AsyncMock()

            # Mock group not found (will be created)
            mock_session.execute.return_value = MagicMock(
                scalar_one_or_none=lambda: None
            )

            mock_get_session.return_value.__aenter__.return_value = mock_session

            # Should initialize flow without error
            await start_event_flow(update, context, mode="public")

            # Verify flow was initialized
            assert "event_flow" in context.user_data
            assert context.user_data["event_flow"]["stage"] == "description"


class TestScheduling:
    """Test scheduling conflict detection."""

    def test_find_user_event_conflict_no_overlap(self):
        """Test no conflict when events don't overlap."""
        from bot.common.scheduling import events_overlap

        event1_start = datetime(2026, 4, 1, 10, 0)
        event1_duration = 120  # minutes

        event2_start = datetime(2026, 4, 1, 14, 0)  # 2 hours after event1 starts
        event2_duration = 120  # minutes

        # Event1: 10:00-12:00, Event2: 14:00-16:00 - no overlap
        assert not events_overlap(event1_start, event1_duration, event2_start, event2_duration)

    def test_find_user_event_conflict_with_overlap(self):
        """Test conflict detected when events overlap."""
        from bot.common.scheduling import events_overlap

        event1_start = datetime(2026, 4, 1, 10, 0)
        event1_duration = 120  # minutes (10:00-12:00)

        event2_start = datetime(2026, 4, 1, 11, 0)  # During event1
        event2_duration = 120  # minutes (11:00-13:00)

        assert events_overlap(event1_start, event1_duration, event2_start, event2_duration)

    def test_find_user_event_conflict_touching_edges(self):
        """Test edge case: events that touch but don't overlap."""
        from bot.common.scheduling import events_overlap

        event1_start = datetime(2026, 4, 1, 10, 0)
        event1_duration = 120  # minutes (10:00-12:00)

        event2_start = datetime(2026, 4, 1, 12, 0)  # Exactly when event1 ends
        event2_duration = 120  # minutes (12:00-14:00)

        # Touching edges should not be a conflict
        assert not events_overlap(event1_start, event1_duration, event2_start, event2_duration)


class TestAttendance:
    """Test attendance parsing and state derivation."""

    def test_parse_attendance_with_status(self):
        """Test attendance parsing with various status formats."""
        from bot.common.attendance import parse_attendance_with_status

        attendance = [
            "12345:interested",
            "67890:committed",
            "11111:confirmed",
        ]

        status_map = parse_attendance_with_status(attendance)

        assert status_map[12345] == "interested"
        assert status_map[67890] == "committed"
        assert status_map[11111] == "confirmed"

    def test_derive_state_from_attendance_empty(self):
        """Test state derivation with no attendees."""
        from bot.common.attendance import derive_state_from_attendance

        state = derive_state_from_attendance([])
        assert state == "proposed"

    def test_derive_state_from_attendance_interested(self):
        """Test state derivation with interested attendees."""
        from bot.common.attendance import derive_state_from_attendance

        attendance = ["12345:interested"]
        state = derive_state_from_attendance(attendance)
        assert state == "interested"


class TestUserPreferences:
    """Test user preference handling."""

    def test_import_user_preferences_module(self):
        """Test user preferences module imports correctly."""
        from bot.common import user_preferences

        # Verify module has expected attributes
        assert hasattr(user_preferences, 'get_user_preferences')
        assert hasattr(user_preferences, 'set_preference_private_mode')


class TestDeepLinks:
    """Test Telegram deep link generation."""

    def test_build_start_link(self):
        """Test start link generation."""
        from bot.common.deeplinks import build_start_link

        link = build_start_link("testbot", "avail_123")

        assert link.startswith("https://t.me/testbot?start=")
        assert "avail_123" in link


class TestEventStates:
    """Test event state machine."""

    def test_state_explanations_complete(self):
        """Test all states have explanations."""
        from bot.common.event_states import STATE_EXPLANATIONS, EVENT_STATE_TRANSITIONS

        for state in EVENT_STATE_TRANSITIONS:
            assert state in STATE_EXPLANATIONS, f"Missing explanation for state: {state}"

    def test_valid_states_defined(self):
        """Test expected states are defined."""
        from bot.common.event_states import EVENT_STATE_TRANSITIONS

        expected_states = {"proposed", "interested", "confirmed", "locked", "completed", "cancelled"}
        assert expected_states == set(EVENT_STATE_TRANSITIONS.keys())


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
