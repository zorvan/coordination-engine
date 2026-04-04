"""LLM service adapter — implements ILLMService."""

from __future__ import annotations

import logging
from typing import Any

from coordination_engine.application.ports import ILLMService

logger = logging.getLogger("coord_engine.llm_adapter")


class LLMServiceAdapter(ILLMService):
    """Wraps the existing ai.llm.LLMClient behind the ILLMService port."""

    def __init__(self, llm_client: Any) -> None:
        # ai.llm.LLMClient instance
        self._client = llm_client

    async def infer_event_draft(
        self,
        message_text: str,
        history: list[dict[str, Any]] | None = None,
        scheduling_mode: str = "fixed",
    ) -> dict[str, Any]:
        try:
            return await self._client.infer_event_draft_from_context(
                message_text=message_text,
                history=history,
                scheduling_mode=scheduling_mode,
            )
        except Exception:
            logger.exception("LLM event draft inference failed")
            return {
                "description": message_text or "Group planned event",
                "event_type": "social",
                "scheduled_time": None,
                "collapse_at": None,
                "duration_minutes": 120,
                "threshold_attendance": 3,
                "invite_all_members": True,
                "invitees": ["@all"],
                "planning_notes": [],
                "inferred_constraints": [],
            }

    async def infer_modification_patch(
        self,
        current_draft: dict[str, Any],
        change_text: str,
    ) -> dict[str, Any]:
        try:
            return await self._client.infer_event_draft_patch(current_draft, change_text)
        except Exception:
            logger.exception("LLM modification patch inference failed")
            return {}

    async def infer_mention_action(
        self,
        text: str,
        history: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        try:
            return await self._client.infer_group_mention_action(
                text=text, history=history
            )
        except Exception:
            logger.exception("LLM mention action inference failed")
            return {
                "action_type": "opinion",
                "event_id": None,
                "target_username": None,
                "constraint_type": None,
                "assistant_response": "",
            }

    async def infer_constraint(self, text: str) -> dict[str, Any]:
        try:
            return await self._client.infer_constraint_from_text(text)
        except Exception:
            logger.exception("LLM constraint inference failed")
            return {}

    async def generate_memory_weave(
        self, fragments: list[str], event_type: str
    ) -> dict[str, Any]:
        # Not yet implemented in LLMClient
        return {"weave_text": "\n".join(fragments[:5]), "tone_palette": ["neutral"]}
