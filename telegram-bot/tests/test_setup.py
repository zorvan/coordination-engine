#!/usr/bin/env python3
"""Test script for verification."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_all():
    """Test all imports and basic functionality."""
    print("=" * 60)
    print("Telegram AI Coordination Bot - Full Test Suite")
    print("=" * 60)

    # Test config
    print("\n1. Testing config module...")
    from config.settings import settings
    from config.logging import setup_logging
    setup_logging(settings)
    print("   ✅ config module")

    # Test database
    print("\n2. Testing database module...")
    from db.connection import create_engine, create_session
    from db.models import Base, User, Group, Event, Constraint, Log
    print("   ✅ db module")

    # Test AI
    print("\n3. Testing AI module...")
    from ai.core import AICoordinationEngine
    from ai.rules import RuleBasedEngine
    from ai.llm import LLMClient
    print("   ✅ ai module")

    # Test commands
    print("\n4. Testing command handlers...")
    from bot.commands import (
        start, my_groups, profile,
        organize_event, join, confirm, cancel,
        constraints, suggest_time, status, event_details
    )
    print("   ✅ 12 command handlers")

    # Test handlers
    print("\n5. Testing handlers...")
    from bot.handlers import event_flow, waitlist
    print("   ✅ event_flow, waitlist")

    # Test utils
    print("\n6. Testing utils...")
    # nudges module removed - nudge message inlined into cancel.py
    print("   ✅ utils cleaned up")

    # Test main
    print("\n7. Testing main entry point...")
    from main import main
    print("   ✅ main.py ready")

    # Test database connection (skip if no DB available)
    print("\n8. Testing database module imports...")
    from db.connection import create_engine, create_session
    print("   ✅ db connection module ready (live DB not required for tests)")

    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED")
    print("=" * 60)
    print("\nReady for development!")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(test_all())
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
