"""
Database migration script for Coordination Engine v2.
PRD v2: From Coordination Tool to Shared Experience Engine.

This script migrates the database schema to support:
- Priority 1: Structural foundations (normalized participants, idempotency, state transitions)
- Priority 2: Layer 2 features (threshold fields, materialization)
- Priority 3: Layer 3 features (memory weave)

Usage:
    python scripts/migrate_v2.py
"""
import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker
from db.models import Base, Event, EventParticipant, ParticipantStatus, ParticipantRole
from db.connection import get_sync_engine

# Import all models to ensure they're registered
from db.models import (
    User, Group, Event, UserPreference, Constraint, Reputation,
    Log, Feedback, EarlyFeedback, AILog,
    EventParticipant, IdempotencyKey, EventStateTransition, EventMemory,
)


def check_table_exists(engine, table_name: str) -> bool:
    """Check if a table exists in the database."""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()


def get_existing_columns(engine, table_name: str) -> set:
    """Get set of existing column names for a table."""
    inspector = inspect(engine)
    if table_name not in inspector.get_table_names():
        return set()
    return {col['name'] for col in inspector.get_columns(table_name)}


async def migrate_events_table(engine):
    """Add new columns to events table."""
    print("Migrating events table...")

    columns_to_add = [
        ("min_participants", "INTEGER DEFAULT 2"),
        ("target_participants", "INTEGER DEFAULT 6"),
        ("collapse_at", "TIMESTAMP"),
        ("lock_deadline", "TIMESTAMP"),
        ("version", "INTEGER DEFAULT 0 NOT NULL"),
    ]

    existing_columns = get_existing_columns(engine, "events")

    with engine.connect() as conn:
        for col_name, col_def in columns_to_add:
            if col_name not in existing_columns:
                print(f"  Adding column: {col_name}")
                await conn.execute(text(f"ALTER TABLE events ADD COLUMN {col_name} {col_def}"))
                await conn.commit()
            else:
                print(f"  Column already exists: {col_name}")

    print("  ✓ Events table migration complete")


async def create_new_tables(engine):
    """Create new tables for v2."""
    print("\nCreating new tables...")

    tables_to_create = [
        "event_participants",
        "idempotency_keys",
        "event_state_transitions",
        "event_memories",
    ]

    with engine.connect() as conn:
        for table_name in tables_to_create:
            if not check_table_exists(engine, table_name):
                print(f"  Creating table: {table_name}")
                # Use SQLAlchemy create_all for new tables
                Base.metadata.create_all(engine, tables=[table_name])
            else:
                print(f"  Table already exists: {table_name}")

    print("  ✓ New tables created")


async def migrate_attendance_to_participants(engine):
    """Migrate existing attendance_list JSON to normalized event_participants table."""
    print("\nMigrating attendance data to normalized table...")

    with engine.connect() as conn:
        # Get all events with attendance_list data
        result = await conn.execute(text("""
            SELECT event_id, attendance_list
            FROM events
            WHERE attendance_list IS NOT NULL
            AND json_array_length(attendance_list) > 0
        """))
        events = result.fetchall()

        if not events:
            print("  No attendance data to migrate")
            return

        migrated_count = 0
        for event_id, attendance_json in events:
            # Parse attendance_list and insert into event_participants
            # This is a simplified migration - full logic in ParticipantService
            for item in attendance_json:
                if isinstance(item, str):
                    if ":" in item:
                        parts = item.split(":", 1)
                        telegram_id = parts[0]
                        status_str = parts[1] if len(parts) > 1 else "interested"
                    else:
                        telegram_id = item
                        status_str = "interested"

                    if telegram_id.isdigit():
                        # Map status
                        if status_str in {"committed", "confirmed"}:
                            status = "confirmed"
                        else:
                            status = "joined"

                        # Insert or ignore (in case of duplicates)
                        await conn.execute(text("""
                            INSERT INTO event_participants
                            (event_id, telegram_user_id, status, role, joined_at)
                            VALUES (:event_id, :telegram_id, :status, 'participant', NOW())
                            ON CONFLICT (event_id, telegram_user_id) DO NOTHING
                        """), {
                            "event_id": event_id,
                            "telegram_id": int(telegram_id),
                            "status": status,
                        })
                        migrated_count += 1

        await conn.commit()
        print(f"  ✓ Migrated {migrated_count} participant records")


async def create_indexes(engine):
    """Create performance indexes."""
    print("\nCreating indexes...")

    indexes = [
        ("idx_event_participants_event_id", "event_participants", "event_id"),
        ("idx_event_participants_user_id", "event_participants", "telegram_user_id"),
        ("idx_event_participants_status", "event_participants", "status"),
        ("idx_event_state_transitions_event_id", "event_state_transitions", "event_id"),
        ("idx_idempotency_keys_expires", "idempotency_keys", "expires_at"),
        ("idx_events_state", "events", "state"),
    ]

    with engine.connect() as conn:
        for idx_name, table, column in indexes:
            try:
                await conn.execute(text(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})"))
                print(f"  Created index: {idx_name}")
            except Exception as e:
                print(f"  Index creation failed (may exist): {idx_name} - {e}")

        await conn.commit()

    print("  ✓ Indexes created")


async def run_migration():
    """Run all v2 migrations."""
    print("=" * 60)
    print("Coordination Engine v2 Database Migration")
    print("=" * 60)

    # Get database URL
    db_url = os.environ.get("DB_URL")
    if not db_url:
        print("ERROR: DB_URL environment variable not set")
        sys.exit(1)

    # Convert to sync engine for migration
    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    print(f"\nConnecting to database...")
    engine = get_sync_engine(db_url)

    try:
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            print("  ✓ Database connection successful")

        # Run migrations
        await migrate_events_table(engine)
        await create_new_tables(engine)
        await migrate_attendance_to_participants(engine)
        await create_indexes(engine)

        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Review the migrated data")
        print("2. Update application code to use new services")
        print("3. Enable feature flags in environment")
        print("4. Monitor logs for any issues")

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_migration())
