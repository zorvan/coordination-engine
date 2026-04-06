"""
LLM stubs for deterministic memory mosaic tests.
Phase 1: §6 — LLM Boundary.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch
from typing import Any


class DeterministicLLM:
    """LLM stub that returns pre-configured responses.

    Usage:
        llm = DeterministicLLM()
        llm.respond_with("Hello world")
        with llm.patched():
            # LLMClient._call_llm() returns "Hello world"
    """

    def __init__(self) -> None:
        self._responses: list[str] = []
        self._call_count = 0
        self._fallback = None

    def respond_with(self, text: str) -> None:
        """Queue a response."""
        self._responses.append(text)

    def raise_on_next(self, exc: Exception) -> None:
        """Make the next call raise an exception."""
        self._responses.append(exc)  # type: ignore[arg-type]

    def next_response(self) -> str | None:
        if self._call_count < len(self._responses):
            val = self._responses[self._call_count]
            self._call_count += 1
            if isinstance(val, Exception):
                raise val
            return val
        return self._fallback

    def patched(self):
        """Return a context manager that patches LLMClient._call_llm."""
        async def _stub(self_llm: Any, prompt: str) -> str | None:
            return self.next_response()

        return patch("ai.llm.LLMClient._call_llm", new=_stub)
