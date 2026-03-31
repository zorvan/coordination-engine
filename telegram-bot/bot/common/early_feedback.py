"""Helpers for persistent pre-event behavioral feedback."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from db.models import EarlyFeedback


async def add_early_feedback_signal(
    session,
    *,
    event_id: int,
    target_user_id: int,
    source_type: str,
    value: float,
    weight: float,
    confidence: float,
    signal_type: str = "overall",
    source_user_id: int | None = None,
    sanitized_comment: str | None = None,
    is_private: bool = False,
    metadata: dict[str, Any] | None = None,
) -> EarlyFeedback:
    """Create a normalized early-feedback signal row."""
    row = EarlyFeedback(
        event_id=event_id,
        source_user_id=source_user_id,
        target_user_id=target_user_id,
        source_type=source_type,
        signal_type=signal_type,
        value=max(0.0, min(5.0, float(value))),
        weight=max(0.0, min(1.0, float(weight))),
        confidence=max(0.0, min(1.0, float(confidence))),
        sanitized_comment=(sanitized_comment or "").strip()[:2000] or None,
        is_private=1 if is_private else 0,
        metadata_dict=metadata or {},
        created_at=datetime.utcnow(),
    )
    session.add(row)
    await session.flush()
    return row


async def aggregate_early_feedback_for_user(
    session,
    *,
    event_id: int,
    target_user_id: int,
) -> tuple[float | None, float, int]:
    """Return weighted average score, total weight, and number of signals."""
    result = await session.execute(
        select(EarlyFeedback).where(
            EarlyFeedback.event_id == event_id,
            EarlyFeedback.target_user_id == target_user_id,
        )
    )
    rows = result.scalars().all()
    if not rows:
        return None, 0.0, 0

    weighted_total = 0.0
    total_weight = 0.0
    for row in rows:
        w = max(0.0, min(1.0, float(row.weight or 0.0))) * max(
            0.0, min(1.0, float(row.confidence or 0.0))
        )
        weighted_total += float(row.value or 0.0) * w
        total_weight += w
    if total_weight <= 0:
        return None, 0.0, len(rows)
    return weighted_total / total_weight, total_weight, len(rows)
