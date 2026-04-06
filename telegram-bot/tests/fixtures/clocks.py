"""
Clock/time-control utilities for deterministic tests.
Phase 1: §6 — Time Control.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import patch


class FrozenClock:
    """Context manager that freezes datetime.utcnow().

    Usage:
        with FrozenClock() as clock:
            # datetime.utcnow() returns clock.now
            clock.advance(hours=2)
    """

    def __init__(self, start: datetime | None = None) -> None:
        self._now = start or datetime(2026, 4, 6, 12, 0, 0)

    @property
    def now(self) -> datetime:
        return self._now

    def advance(self, hours: int = 0, minutes: int = 0, seconds: int = 0) -> None:
        self._now += timedelta(hours=hours, minutes=minutes, seconds=seconds)

    def set(self, dt: datetime) -> None:
        self._now = dt

    def _mock_utcnow(self) -> datetime:
        return self._now

    def __enter__(self) -> "FrozenClock":
        self._patcher = patch("datetime.datetime", wraps=datetime)
        self._patcher.start()
        import datetime as dt_mod
        self._original_utcnow = dt_mod.datetime.utcnow
        dt_mod.datetime.utcnow = self._mock_utcnow  # type: ignore[attr-defined]
        return self

    def __exit__(self, *args: object) -> None:
        self._patcher.stop()
        import datetime as dt_mod
        dt_mod.datetime.utcnow = self._original_utcnow  # type: ignore[attr-defined]
