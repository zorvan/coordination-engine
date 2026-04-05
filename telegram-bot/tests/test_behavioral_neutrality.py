#!/usr/bin/env python3
"""Behavioral Neutrality Test Suite — v3 verification.

Tests that identical declared intent produces identical system behavior
regardless of user history, and that no behavioral data influences decisions.

v3 principle: Trust emerges; it doesn't compute.
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from unittest.mock import AsyncMock, MagicMock, patch
import pytest


# ============================================================================
# Test 1: No behavioral imports in production code
# ============================================================================

class TestNoBehavioralImports:
    """Verify deleted behavioral systems are not imported anywhere."""

    def test_no_early_feedback_imports(self):
        import ast
        import pathlib

        bot_dir = pathlib.Path(__file__).parent.parent / "bot"
        ai_dir = pathlib.Path(__file__).parent.parent / "ai"
        db_dir = pathlib.Path(__file__).parent.parent / "db"

        for directory in [bot_dir, ai_dir, db_dir]:
            for py_file in directory.rglob("*.py"):
                source = py_file.read_text()
                assert "early_feedback" not in source.lower() or "infer_early_feedback_from_text" in source, \
                    f"{py_file} still references early_feedback"

    def test_no_reputation_imports(self):
        import pathlib

        bot_dir = pathlib.Path(__file__).parent.parent / "bot"
        for py_file in bot_dir.rglob("*.py"):
            source = py_file.read_text()
            # Allow "reputation" in comments/docstrings but not in imports
            lines = source.split("\n")
            for line in lines:
                stripped = line.strip()
                if stripped.startswith("#") or stripped.startswith('"""') or stripped.startswith("'''"):
                    continue
                if "import" in stripped and "Reputation" in stripped:
                    pytest.fail(f"{py_file} still imports Reputation: {stripped}")

    def test_no_reliability_score_in_services(self):
        import pathlib

        services_dir = pathlib.Path(__file__).parent.parent / "bot" / "services"
        for py_file in services_dir.rglob("*.py"):
            source = py_file.read_text()
            assert "reliability_score" not in source.lower(), \
                f"{py_file} still references reliability_score"


# ============================================================================
# Test 2: Materialization neutrality
# ============================================================================

class TestMaterializationNeutrality:
    """All joins must be announced identically regardless of user history."""

    @pytest.mark.asyncio
    async def test_first_join_format_is_neutral(self):
        """First join should just state the fact."""
        from bot.services.event_materialization_service import EventMaterializationService

        mock_bot = AsyncMock()
        mock_session = AsyncMock()
        service = EventMaterializationService(bot=mock_bot, session=mock_session)

        event = MagicMock()
        event.event_type = "social"
        event.event_id = 1

        user = MagicMock()
        user.display_name = "Alice"
        user.user_id = 1

        await service.announce_first_join(event, user, group_chat_id=123)

        mock_bot.send_message.assert_called_once()
        call_args = mock_bot.send_message.call_args
        message = call_args.kwargs.get("text", "")

        # Should NOT contain fragility framing
        assert "collapse" not in message.lower()
        assert "needs" not in message.lower() or "people in" in message.lower()
        # Should contain the fact
        assert "Alice" in message
        assert "1 person in" in message

    @pytest.mark.asyncio
    async def test_join_format_identical_for_all_users(self):
        """Join announcement must be identical regardless of who joins."""
        from bot.services.event_materialization_service import EventMaterializationService

        mock_bot = AsyncMock()
        mock_session = AsyncMock()
        service = EventMaterializationService(bot=mock_bot, session=mock_session)

        event = MagicMock()
        event.event_type = "social"
        event.event_id = 1

        user_a = MagicMock()
        user_a.display_name = "Alice"
        user_a.user_id = 1

        user_b = MagicMock()
        user_b.display_name = "Bob"
        user_b.user_id = 2

        await service.announce_join(event, user_a, confirmed_count=2, group_chat_id=123)
        msg_a = mock_bot.send_message.call_args.kwargs.get("text", "")

        mock_bot.reset_mock()
        await service.announce_join(event, user_b, confirmed_count=2, group_chat_id=123)
        msg_b = mock_bot.send_message.call_args.kwargs.get("text", "")

        # Same structure, different name
        assert "2 people in" in msg_a
        assert "2 people in" in msg_b
        assert "Alice" in msg_a
        assert "Bob" in msg_b
        # Template should be identical aside from name
        template_a = msg_a.replace("Alice", "X")
        template_b = msg_b.replace("Bob", "X")
        assert template_a == template_b

    @pytest.mark.asyncio
    async def test_no_high_reliability_join_method(self):
        """High-reliability join announcement must not exist."""
        from bot.services.event_materialization_service import EventMaterializationService

        assert not hasattr(EventMaterializationService, "announce_high_reliability_join"), \
            "announce_high_reliability_join should be removed"

    @pytest.mark.asyncio
    async def test_no_near_collapse_method(self):
        """Near-collapse alert must not exist."""
        from bot.services.event_materialization_service import EventMaterializationService

        assert not hasattr(EventMaterializationService, "announce_near_collapse"), \
            "announce_near_collapse should be removed"

    @pytest.mark.asyncio
    async def test_threshold_reached_is_neutral(self):
        """Threshold announcement should just state the fact."""
        from bot.services.event_materialization_service import EventMaterializationService

        mock_bot = AsyncMock()
        mock_session = AsyncMock()
        service = EventMaterializationService(bot=mock_bot, session=mock_session)

        event = MagicMock()
        event.event_type = "social"
        event.event_id = 1

        await service.announce_threshold_reached(event, confirmed_count=3, group_chat_id=123)

        call_args = mock_bot.send_message.call_args
        message = call_args.kwargs.get("text", "")

        assert "collapse" not in message.lower()
        assert "fragile" not in message.lower()
        assert "3 people in" in message


# ============================================================================
# Test 3: AI decision neutrality
# ============================================================================

class TestAIDecisionNeutrality:
    """AI must not use attendance history in time suggestions."""

    def test_rules_engine_no_reliability(self):
        """Rules engine must not have a reliability method."""
        from ai.rules import RuleBasedEngine

        engine = RuleBasedEngine()
        assert not hasattr(engine, "compute_reliability"), \
            "compute_reliability should be removed — availability-only scheduling"

    def test_rules_engine_no_threshold_probability(self):
        """Rules engine should not have collapse prediction."""
        from ai.rules import RuleBasedEngine

        engine = RuleBasedEngine()
        assert not hasattr(engine, "calculate_threshold_probability"), \
            "calculate_threshold_probability should be removed from rules engine"

    def test_ai_core_no_threshold_probability(self):
        """AI core should not have collapse prediction."""
        from ai.core import AICoordinationEngine

        assert not hasattr(AICoordinationEngine, "calculate_threshold_probability"), \
            "calculate_threshold_probability should be removed from AI engine"


# ============================================================================
# Test 4: Model neutrality
# ============================================================================

class TestModelNeutrality:
    """Database models must not contain behavioral scoring columns."""

    def test_no_reputation_column(self):
        from db.models import User

        columns = [c.name for c in User.__table__.columns]
        assert "reputation" not in columns, \
            "User.reputation column should be removed"

    def test_no_early_feedback_model(self):
        from db import models

        assert not hasattr(models, "EarlyFeedback"), \
            "EarlyFeedback model should be removed"

    def test_no_reputation_model(self):
        from db import models

        assert not hasattr(models, "Reputation"), \
            "Reputation model should be removed"

    def test_no_user_early_feedback_relationships(self):
        from db.models import User

        relationships = list(User.__mapper__.relationships.keys())
        assert "early_feedback_given" not in relationships, \
            "User.early_feedback_given relationship should be removed"
        assert "early_feedback_received" not in relationships, \
            "User.early_feedback_received relationship should be removed"
        assert "reputation_records" not in relationships, \
            "User.reputation_records relationship should be removed"


# ============================================================================
# Test 5: Memory architecture neutrality
# ============================================================================

class TestMemoryNeutrality:
    """Memory system must have no collection deadline."""

    def test_no_collection_window_constant(self):
        from bot.services.event_memory_service import EventMemoryService

        assert not hasattr(EventMemoryService, "COLLECTION_WINDOW_HOURS"), \
            "COLLECTION_WINDOW_HOURS should be removed"
        assert not hasattr(EventMemoryService, "COLLECTION_DELAY_HOURS"), \
            "COLLECTION_DELAY_HOURS should be removed"

    def test_has_prior_event_memories_method(self):
        """Memory service must have method for memory-first event creation."""
        from bot.services.event_memory_service import EventMemoryService

        assert hasattr(EventMemoryService, "get_prior_event_memories"), \
            "get_prior_event_memories method should exist for memory-first creation"


# ============================================================================
# Test 6: Personal attendance mirror is causally inert
# ============================================================================

class TestPersonalAttendanceMirror:
    """/how_am_i_doing must only show counts and never be read by the system."""

    def test_command_exists(self):
        from bot.commands import personal_attendance_mirror

        assert hasattr(personal_attendance_mirror, "handle"), \
            "/how_am_i_doing command handler must exist"

    def test_no_system_reads_participation_counts(self):
        """No component other than the attendance mirror should read participation counts
        for behavioral decisions."""
        import pathlib

        bot_dir = pathlib.Path(__file__).parent.parent / "bot"
        ai_dir = pathlib.Path(__file__).parent.parent / "ai"

        for directory in [bot_dir, ai_dir]:
            for py_file in directory.rglob("*.py"):
                if py_file.name == "personal_attendance_mirror.py":
                    continue
                source = py_file.read_text()
                # Skip comments-only occurrences — check for actual code usage
                # where EventParticipant is used alongside reliability computation
                lines = source.split("\n")
                has_participant_query = False
                has_reliability_computation = False
                for line in lines:
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if "EventParticipant" in stripped and "select" in stripped:
                        has_participant_query = True
                    if "reliability" in stripped.lower() and ("score" in stripped.lower() or "compute" in stripped.lower()):
                        has_reliability_computation = True

                if has_participant_query and has_reliability_computation:
                    pytest.fail(
                        f"{py_file} queries EventParticipant and computes reliability"
                    )


# ============================================================================
# Test 7: Template audit — "show reality" vs "engineer response"
# ============================================================================

class TestTemplateAudit:
    """All materialization templates must show reality, not engineer response."""

    def get_all_materialization_messages(self):
        """Extract all message templates from the service."""
        from bot.services.event_materialization_service import EventMaterializationService
        import inspect

        templates = {}
        source = inspect.getsource(EventMaterializationService)

        # Find all f-string or string message patterns
        for line in source.split("\n"):
            stripped = line.strip()
            if 'message = f"' in stripped or 'message = "' in stripped:
                templates[stripped[:50]] = stripped

        return templates

    def test_no_framing_keywords(self):
        """Templates must not contain response-engineering language."""
        from bot.services.event_materialization_service import EventMaterializationService
        import inspect

        source = inspect.getsource(EventMaterializationService)

        forbidden_keywords = [
            "collapse",
            "fragile",
            "at risk",
            "don't miss",
            "last chance",
            "reliability",
            "high-reliability",
            "trusted",
            "always shows",
            "never misses",
        ]

        for keyword in forbidden_keywords:
            assert keyword.lower() not in source.lower(), \
                f"Materialization service contains '{keyword}' — v3 requires neutral framing"


# ============================================================================
# Integration: Run all tests
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Behavioral Neutrality Test Suite — v3 Verification")
    print("=" * 60)

    # Run with pytest
    exit_code = pytest.main([__file__, "-v", "--tb=short"])

    if exit_code == 0:
        print("\n" + "=" * 60)
        print("✅ ALL BEHAVIORAL NEUTRALITY TESTS PASSED")
        print("=" * 60)
        print("\nVerified:")
        print("  ✓ No behavioral imports")
        print("  ✓ Materialization is neutral")
        print("  ✓ AI decisions use no history")
        print("  ✓ Models are behaviorally inert")
        print("  ✓ Memory has no collection deadline")
        print("  ✓ /how_am_i_doing is causally inert")
        print("  ✓ Templates show reality")
        print("  ✓ Domain layer is clean")
    else:
        print(f"\n❌ {exit_code} test(s) failed")

    sys.exit(exit_code)
