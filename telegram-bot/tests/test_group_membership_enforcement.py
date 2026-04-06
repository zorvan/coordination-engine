#!/usr/bin/env python3
"""
Integration tests for group membership-based event access control.

NOTE: These tests use simplified mocks that don't fully match the real rbac.py
call patterns (multiple sequential execute calls, Telegram API fallbacks, etc.).
They verify the test structure and imports work. For real integration testing,
use tests/integration/ and tests/scenarios/ which use proper DB sessions.

TODO: Rewrite these tests to properly mock sequential session.execute calls
or migrate to the scenario simulator approach.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from bot.common.rbac import (
    check_group_membership,
    check_event_visibility_and_get_event,
)


class MockEvent:
    """Simple mock event object."""
    def __init__(self, event_id=1, group_id=1, organizer_id=100, admin_id=None, state="proposed"):
        self.event_id = event_id
        self.group_id = group_id
        self.organizer_telegram_user_id = organizer_id
        self.admin_telegram_user_id = admin_id
        self.state = state
        self.event_type = "social"


class MockGroup:
    """Simple mock group object."""
    def __init__(self, group_id=1, telegram_group_id=1001, member_list=None):
        self.group_id = group_id
        self.telegram_group_id = telegram_group_id
        self.member_list = member_list or []
        self.group_name = "Test Group"


class TestCheckGroupMembership:
    """Tests for check_group_membership helper."""

    @pytest.mark.asyncio
    async def test_member_in_group(self):
        """User in member_list should be recognized as member."""
        session = AsyncMock(spec=AsyncSession)
        group = MockGroup(group_id=1, member_list=[100, 200, 300])
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = group
        session.execute = AsyncMock(return_value=mock_result)

        is_member, error_msg = await check_group_membership(session, 1, 200)

        assert is_member is True
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_non_member_in_group(self):
        """User NOT in member_list should be denied (no chat context)."""
        session = AsyncMock(spec=AsyncSession)
        group = MockGroup(group_id=1, member_list=[100, 200, 300])

        # Multiple execute calls: 1) group lookup, 2) participant check
        group_result = MagicMock()
        group_result.scalar_one_or_none.return_value = group
        participant_result = MagicMock()
        participant_result.scalar_one_or_none.return_value = None  # No prior participation
        session.execute = AsyncMock(side_effect=[group_result, participant_result])

        is_member, error_msg = await check_group_membership(session, 1, 999)

        assert is_member is False
        assert error_msg is not None
        assert "not a member" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_implicit_membership_via_group_chat(self):
        """User interacting from the same group chat should be auto-enrolled."""
        session = AsyncMock(spec=AsyncSession)
        group = MockGroup(group_id=1, telegram_group_id=1001, member_list=[100])
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = group
        session.execute = AsyncMock(return_value=mock_result)
        session.flush = AsyncMock()

        is_member, error_msg = await check_group_membership(
            session, 1, 999, telegram_chat_id=1001
        )

        assert is_member is True
        assert error_msg is None
        # Verify auto-enrollment
        assert 999 in group.member_list
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_group_not_found(self):
        """Non-existent group should return error."""
        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        is_member, error_msg = await check_group_membership(session, 999, 100)

        assert is_member is False
        assert error_msg is not None
        assert "not found" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_empty_member_list_no_chat_context(self):
        """Empty member_list without chat context should deny all users."""
        session = AsyncMock(spec=AsyncSession)
        group = MockGroup(group_id=1, member_list=[])
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = group

        # First execute for Group lookup
        participant_mock = MagicMock()
        participant_mock.scalar_one_or_none.return_value = None  # No participant record

        call_count = [0]
        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            return participant_mock

        session.execute = mock_execute

        is_member, error_msg = await check_group_membership(session, 1, 100)

        assert is_member is False

    @pytest.mark.asyncio
    async def test_proven_member_via_participation(self):
        """User with a participant record in any event in the group should be allowed."""
        session = AsyncMock(spec=AsyncSession)
        group = MockGroup(group_id=1, member_list=[])  # NOT in member_list
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = group

        # Simulate user has a participant record in an event in this group
        participant_mock = MagicMock()
        participant_mock.scalar_one_or_none.return_value = 42  # Has participant record

        call_count = [0]
        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            return participant_mock

        session.execute = mock_execute
        session.flush = AsyncMock()

        is_member, error_msg = await check_group_membership(session, 1, 500)

        assert is_member is True
        assert error_msg is None
        # Auto-enrolled
        assert 500 in group.member_list

    @pytest.mark.asyncio
    async def test_null_member_list_no_chat_context(self):
        """None member_list without chat context or participation should deny all users."""
        session = AsyncMock(spec=AsyncSession)
        group = MockGroup(group_id=1, member_list=None)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = group

        # No participant record either
        participant_mock = MagicMock()
        participant_mock.scalar_one_or_none.return_value = None

        call_count = [0]
        async def mock_execute(query):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result
            return participant_mock

        session.execute = mock_execute

        is_member, error_msg = await check_group_membership(session, 1, 100)

        assert is_member is False


class TestCheckEventVisibilityAndGetEvent:
    """Tests for check_event_visibility_and_get_event helper.

    NOTE: These tests mock session.execute with side_effect for multiple calls:
    1) event+group JOIN query, 2) optional membership checks
    """

    def _mock_event_group_session(self, event, group):
        """Helper to create session mock for event+group lookup queries."""
        session = AsyncMock(spec=AsyncSession)
        event_group_result = MagicMock()
        event_group_result.one_or_none.return_value = (event, group)
        session.execute = AsyncMock(return_value=event_group_result)
        return session

    @pytest.mark.asyncio
    async def test_organizer_can_see_event(self):
        """Organizer should always see the event regardless of member_list."""
        event = MockEvent(event_id=1, group_id=1, organizer_id=100)
        group = MockGroup(group_id=1, member_list=[])
        session = self._mock_event_group_session(event, group)

        is_visible, vis_event, vis_group, error_msg = (
            await check_event_visibility_and_get_event(session, 1, 100)
        )

        assert is_visible is True
        assert vis_event is event
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_admin_can_see_event(self):
        """Admin should always see the event regardless of member_list."""
        event = MockEvent(event_id=1, group_id=1, organizer_id=100, admin_id=200)
        group = MockGroup(group_id=1, member_list=[100])
        session = self._mock_event_group_session(event, group)

        is_visible, vis_event, vis_group, error_msg = (
            await check_event_visibility_and_get_event(session, 1, 200)
        )

        assert is_visible is True
        assert vis_event is event
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_group_member_can_see_event(self):
        """Group member should see the event."""
        event = MockEvent(event_id=1, group_id=1, organizer_id=100)
        group = MockGroup(group_id=1, member_list=[100, 300, 400])
        session = self._mock_event_group_session(event, group)

        is_visible, vis_event, vis_group, error_msg = (
            await check_event_visibility_and_get_event(session, 1, 300)
        )

        assert is_visible is True
        assert vis_event is event
        assert error_msg is None

    @pytest.mark.asyncio
    async def test_non_member_cannot_see_event(self):
        """Non-member should NOT see the event (no chat context)."""
        event = MockEvent(event_id=1, group_id=1, organizer_id=100)
        group = MockGroup(group_id=1, member_list=[100, 200, 300])

        session = AsyncMock(spec=AsyncSession)
        event_group_result = MagicMock()
        event_group_result.one_or_none.return_value = (event, group)
        participant_result = MagicMock()
        participant_result.scalar_one_or_none.return_value = None
        telegram_membership_result = MagicMock()
        telegram_membership_result.scalar_one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[
            event_group_result,             # event+group lookup
            participant_result,             # prior participation check
            telegram_membership_result,     # Telegram API fallback
        ])

        is_visible, vis_event, vis_group, error_msg = (
            await check_event_visibility_and_get_event(session, 1, 999)
        )

        assert is_visible is False
        assert vis_event is None
        assert error_msg is not None
        assert "access" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_implicit_membership_via_group_chat(self):
        """User in the same group chat should see the event and be auto-enrolled."""
        event = MockEvent(event_id=1, group_id=1, organizer_id=100)
        group = MockGroup(group_id=1, telegram_group_id=5001, member_list=[100])
        session = self._mock_event_group_session(event, group)
        session.flush = AsyncMock()

        is_visible, vis_event, vis_group, error_msg = (
            await check_event_visibility_and_get_event(
                session, 1, 999, telegram_chat_id=5001
            )
        )

        assert is_visible is True
        assert vis_event is event
        assert error_msg is None
        assert 999 in group.member_list
        session.flush.assert_called_once()

    @pytest.mark.asyncio
    async def test_event_not_found(self):
        """Non-existent event should return not found error."""
        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = None
        session.execute = AsyncMock(return_value=mock_result)

        is_visible, vis_event, vis_group, error_msg = (
            await check_event_visibility_and_get_event(session, 999, 100)
        )

        assert is_visible is False
        assert vis_event is None
        assert "not found" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_orphaned_event_denied(self):
        """Event with no group should be denied for non-organizer."""
        event = MockEvent(event_id=1, group_id=1, organizer_id=100)
        mock_result = MagicMock()
        mock_result.one_or_none.return_value = (event, None)  # No group
        session = AsyncMock(spec=AsyncSession)
        session.execute = AsyncMock(return_value=mock_result)

        is_visible, vis_event, vis_group, error_msg = (
            await check_event_visibility_and_get_event(session, 1, 999)
        )

        assert is_visible is False
        assert "not found" in error_msg.lower()


class TestCrossGroupIsolation:
    """Integration-style tests for cross-group isolation scenarios."""

    def _mock_event_group_session(self, event, group):
        """Helper to create session mock for event+group lookup queries."""
        session = AsyncMock(spec=AsyncSession)
        event_group_result = MagicMock()
        event_group_result.one_or_none.return_value = (event, group)
        session.execute = AsyncMock(return_value=event_group_result)
        return session

    @pytest.mark.asyncio
    async def test_user_cannot_see_events_from_other_group(self):
        """User in Group A should not see events from Group B (no chat context)."""
        group_b = MockGroup(group_id=2, telegram_group_id=2002, member_list=[100, 200])
        event_b = MockEvent(event_id=2, group_id=2, organizer_id=100)

        session = AsyncMock(spec=AsyncSession)
        event_group_result = MagicMock()
        event_group_result.one_or_none.return_value = (event_b, group_b)
        participant_result = MagicMock()
        participant_result.scalar_one_or_none.return_value = None
        telegram_membership_result = MagicMock()
        telegram_membership_result.scalar_one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[
            event_group_result,             # event+group lookup
            participant_result,             # prior participation check
            telegram_membership_result,     # Telegram API fallback
        ])

        is_visible, _, _, error_msg = (
            await check_event_visibility_and_get_event(session, 2, 999)
        )

        assert is_visible is False
        assert "access" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_user_in_both_groups(self):
        """User member of both groups should see events from either."""
        group = MockGroup(group_id=1, member_list=[100, 200, 300])
        event = MockEvent(event_id=1, group_id=1, organizer_id=200)
        session = self._mock_event_group_session(event, group)

        is_visible, vis_event, _, error_msg = (
            await check_event_visibility_and_get_event(session, 1, 100)
        )

        assert is_visible is True
        assert vis_event is event

    @pytest.mark.asyncio
    async def test_organizer_from_other_group_can_see_own_event(self):
        """Organizer of event in Group B can see it even if not in Group B's member_list."""
        group_b = MockGroup(group_id=2, member_list=[200, 300])  # 100 NOT in list
        event_b = MockEvent(event_id=2, group_id=2, organizer_id=100)  # 100 is organizer
        session = self._mock_event_group_session(event_b, group_b)

        is_visible, vis_event, _, error_msg = (
            await check_event_visibility_and_get_event(session, 2, 100)
        )

        assert is_visible is True
        assert vis_event is event_b

    @pytest.mark.asyncio
    async def test_cross_group_chat_denied(self):
        """User in Group A chat cannot see events from Group B."""
        group_b = MockGroup(group_id=2, telegram_group_id=2002, member_list=[100, 200])
        event_b = MockEvent(event_id=2, group_id=2, organizer_id=100)

        session = AsyncMock(spec=AsyncSession)
        event_group_result = MagicMock()
        event_group_result.one_or_none.return_value = (event_b, group_b)
        participant_result = MagicMock()
        participant_result.scalar_one_or_none.return_value = None
        telegram_membership_result = MagicMock()
        telegram_membership_result.scalar_one_or_none.return_value = None

        session.execute = AsyncMock(side_effect=[
            event_group_result,             # event+group lookup
            participant_result,             # prior participation check
            telegram_membership_result,     # Telegram API fallback
        ])

        is_visible, _, _, error_msg = (
            await check_event_visibility_and_get_event(
                session, 2, 999, telegram_chat_id=3001
            )
        )

        assert is_visible is False
        assert "access" in error_msg.lower()

    @pytest.mark.asyncio
    async def test_same_group_chat_allowed(self):
        """User in the same group chat as the event can access it."""
        group = MockGroup(group_id=1, telegram_group_id=1001, member_list=[100])
        event = MockEvent(event_id=1, group_id=1, organizer_id=100)
        session = self._mock_event_group_session(event, group)
        session.flush = AsyncMock()

        is_visible, vis_event, _, error_msg = (
            await check_event_visibility_and_get_event(
                session, 1, 999, telegram_chat_id=1001
            )
        )

        assert is_visible is True
        assert vis_event is event
