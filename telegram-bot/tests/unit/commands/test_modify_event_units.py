"""
Unit tests for modify-event request UX and patch application.
"""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from bot.commands.modify_event import _apply_inferred_event_patch
from bot.handlers.mentions import _submit_modify_request_via_message


class TestModifyRequestSubmission:
    """Requester-visible confirmation should not expose admin controls."""

    @pytest.mark.asyncio
    async def test_requester_message_has_no_approval_buttons(self) -> None:
        update = MagicMock()
        update.message.reply_text = AsyncMock()

        context = MagicMock()
        context.bot_data = {}

        with patch(
            "bot.common.event_notifications.send_event_modification_request_dm",
            AsyncMock(return_value=True),
        ):
            await _submit_modify_request_via_message(
                update=update,
                context=context,
                request_id="abc12345",
                event_id=77,
                admin_id=999,
                change_text="Move the location to home",
                requester_id=111,
                requester_username="alice",
            )

        _, kwargs = update.message.reply_text.call_args
        assert "reply_markup" not in kwargs


class TestApplyInferredEventPatch:
    """Shared patch application should treat planning-preference changes as real edits."""

    def test_location_type_change_is_recorded(self) -> None:
        event = SimpleNamespace(
            description="Board games",
            event_type="social",
            scheduled_time=None,
            duration_minutes=120,
            min_participants=3,
            target_participants=5,
            planning_prefs={"location_type": "cafe"},
        )

        changed_fields, reason_parts = _apply_inferred_event_patch(
            event,
            {"location_type": "home"},
        )

        assert "location_type" in changed_fields
        assert "location_type changed to home" in reason_parts
        assert event.planning_prefs["location_type"] == "home"
