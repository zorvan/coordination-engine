"""
Unit tests for LLM fallbacks and parsing helpers.
"""
from __future__ import annotations

import pytest

from ai.llm import LLMClient


class TestInferEventDraftPatchFallback:
    """Fallback parser should still recognize basic modify intents."""

    @pytest.mark.asyncio
    async def test_move_location_to_home_sets_location_type_home(self) -> None:
        client = LLMClient()
        try:
            async def failing_call(_: str) -> str:
                raise RuntimeError("network unavailable")

            client._call_llm = failing_call  # type: ignore[method-assign]

            patch = await client.infer_event_draft_patch(
                {"description": "Game night", "location_type": "cafe"},
                "Move the location to home",
            )
        finally:
            await client.close()

        assert patch["location_type"] == "home"

    @pytest.mark.asyncio
    async def test_time_parsing_7pm_sets_correct_time(self) -> None:
        client = LLMClient()
        try:
            async def failing_call(_: str) -> str:
                raise RuntimeError("network unavailable")

            client._call_llm = failing_call  # type: ignore[method-assign]

            patch = await client.infer_event_draft_patch(
                {"description": "Game night"},
                "change time to 7pm",
            )
        finally:
            await client.close()

        assert "scheduled_time_iso" in patch
        assert patch["scheduled_time_iso"].endswith("T19:00")
