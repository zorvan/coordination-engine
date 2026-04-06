"""
Contract tests for legacy cleanup and v3.2 philosophy boundaries.
"""
from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]


def _read(rel_path: str) -> str:
    return (REPO_ROOT / rel_path).read_text()


def test_event_presenters_do_not_show_ai_score() -> None:
    source = _read("bot/common/event_presenters.py")
    assert "AI Score:" not in source


def test_event_presenters_do_not_use_collapse_dread_copy() -> None:
    source = _read("bot/common/event_presenters.py")
    assert "If one more person drops" not in source
    assert "this event collapses" not in source


def test_active_entry_points_do_not_route_to_feedback() -> None:
    start_source = _read("bot/commands/start.py")
    main_source = _read("main.py")
    event_flow_source = _read("bot/handlers/event_flow.py")
    event_details_source = _read("bot/commands/event_details.py")

    assert "feedback_" not in start_source
    assert '"feedback":' not in main_source
    assert "^feedback_" not in main_source
    assert "Give Feedback in DM" not in event_flow_source
    assert "event_feedback_" not in event_flow_source
    assert "Give Feedback in DM" not in event_details_source


def test_profile_no_longer_reports_feedback_scores() -> None:
    source = _read("bot/commands/profile.py")
    assert "Feedback Entries" not in source
    assert "Avg Feedback Score" not in source


def test_settings_define_webhook_fields_for_production_mode() -> None:
    source = _read("config/settings.py")
    assert "self.webhook_url" in source
    assert "self.webhook_port" in source
    assert "self.webhook_secret" in source


def test_active_runtime_no_longer_uses_legacy_participation_fields() -> None:
    active_sources = [
        "bot/commands/event_creation.py",
        "bot/commands/event_details.py",
        "bot/commands/modify_event.py",
        "bot/common/confirmation.py",
        "bot/common/deadline_check.py",
        "bot/common/event_access.py",
        "bot/common/event_notifications.py",
        "bot/common/event_presenters.py",
        "bot/handlers/mentions.py",
        "bot/services/event_state_transition_service.py",
        "ai/llm.py",
        "ai/schemas.py",
    ]

    for rel_path in active_sources:
        source = _read(rel_path)
        assert "threshold_attendance" not in source, rel_path
        assert "attendance_list" not in source, rel_path


def test_legacy_attendance_module_removed() -> None:
    assert not (REPO_ROOT / "bot/common/attendance.py").exists()
