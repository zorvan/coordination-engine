"""Shared event state definitions."""

from typing import Dict, List

EVENT_STATE_TRANSITIONS: Dict[str, List[str]] = {
    "proposed": ["interested", "cancelled"],
    "interested": ["confirmed", "cancelled"],
    "confirmed": ["interested", "proposed", "locked", "cancelled"],
    "locked": ["completed", "cancelled"],
    "cancelled": [],
    "completed": [],
}

STATE_EXPLANATIONS = {
    "proposed": "Event created; participants should join.",
    "interested": "People joined; waiting for commitments.",
    "confirmed": "At least one participant committed attendance.",
    "locked": "Event is finalized; attendance is closed.",
    "cancelled": "Event was cancelled.",
    "completed": "Event finished.",
}


def can_transition(current_state: str, target_state: str) -> bool:
    """Check if a state transition is valid."""
    return target_state in EVENT_STATE_TRANSITIONS.get(current_state, [])
