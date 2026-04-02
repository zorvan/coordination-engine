#!/usr/bin/env python3
"""
Comprehensive database migration for Coordination Engine v2.
Creates all missing tables, columns, indexes, and enum types.
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncpg


async def run_migration():
    """Run complete v2 migration."""
    db_url = os.environ.get("DB_URL")
    if not db_url:
        print("ERROR: DB_URL environment variable not set")
        sys.exit(1)

    if db_url.startswith("postgresql+asyncpg://"):
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    print("=" * 60)
    print("Coordination Engine v2 - Complete Database Migration")
    print("=" * 60)
    print(f"\nConnecting to database...")
    conn = await asyncpg.connect(db_url)

    try:
        # 1. Create enum types
        print("\n[1/5] Creating enum types...")
        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE participant_status AS ENUM ('joined', 'confirmed', 'cancelled', 'no_show');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        print("  ✓ participant_status")

        await conn.execute("""
            DO $$ BEGIN
                CREATE TYPE participant_role AS ENUM ('organizer', 'participant', 'observer');
            EXCEPTION
                WHEN duplicate_object THEN null;
            END $$;
        """)
        print("  ✓ participant_role")

        # 2. Add missing columns to events table
        print("\n[2/5] Migrating events table...")
        columns_to_add = [
            ("min_participants", "INTEGER DEFAULT 2"),
            ("target_participants", "INTEGER DEFAULT 6"),
            ("collapse_at", "TIMESTAMP"),
            ("lock_deadline", "TIMESTAMP"),
            ("version", "INTEGER DEFAULT 0 NOT NULL"),
        ]

        existing_columns = await conn.fetch("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'events'
        """)
        existing_column_names = {row['column_name'] for row in existing_columns}

        for col_name, col_def in columns_to_add:
            if col_name not in existing_column_names:
                await conn.execute(f"ALTER TABLE events ADD COLUMN {col_name} {col_def}")
                print(f"  ✓ Added column: {col_name}")
            else:
                print(f"  ✓ Column exists: {col_name}")

        # 3. Create new tables
        print("\n[3/5] Creating new tables...")

        # event_participants
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS event_participants (
                event_id INTEGER NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
                telegram_user_id BIGINT NOT NULL,
                status participant_status NOT NULL DEFAULT 'joined',
                role participant_role NOT NULL DEFAULT 'participant',
                joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                confirmed_at TIMESTAMP,
                cancelled_at TIMESTAMP,
                source VARCHAR(50),
                PRIMARY KEY (event_id, telegram_user_id)
            )
        """)
        print("  ✓ event_participants")

        # idempotency_keys
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                idempotency_key VARCHAR(255) PRIMARY KEY,
                command_type VARCHAR(100) NOT NULL,
                user_id INTEGER REFERENCES users(user_id),
                event_id INTEGER REFERENCES events(event_id),
                status VARCHAR(50) DEFAULT 'pending',
                response_hash VARCHAR(255),
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP,
                expires_at TIMESTAMP NOT NULL
            )
        """)
        print("  ✓ idempotency_keys")

        # event_state_transitions
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS event_state_transitions (
                transition_id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
                from_state VARCHAR(20) NOT NULL,
                to_state VARCHAR(20) NOT NULL,
                actor_telegram_user_id BIGINT,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                reason TEXT,
                source VARCHAR(50) NOT NULL
            )
        """)
        print("  ✓ event_state_transitions")

        # event_memories
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS event_memories (
                memory_id SERIAL PRIMARY KEY,
                event_id INTEGER NOT NULL REFERENCES events(event_id) ON DELETE CASCADE UNIQUE,
                fragments JSONB DEFAULT '[]',
                hashtags JSONB DEFAULT '[]',
                outcome_markers JSONB DEFAULT '[]',
                weave_text TEXT,
                lineage_event_ids JSONB DEFAULT '[]',
                tone_palette JSONB DEFAULT '[]',
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("  ✓ event_memories")

        # 4. Create indexes
        print("\n[4/5] Creating indexes...")
        indexes = [
            ("idx_event_participants_event_id", "event_participants", "event_id"),
            ("idx_event_participants_user_id", "event_participants", "telegram_user_id"),
            ("idx_event_participants_status", "event_participants", "status"),
            ("idx_event_state_transitions_event_id", "event_state_transitions", "event_id"),
            ("idx_idempotency_keys_expires", "idempotency_keys", "expires_at"),
        ]

        for idx_name, table, column in indexes:
            try:
                await conn.execute(f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table}({column})")
                print(f"  ✓ {idx_name}")
            except Exception as e:
                print(f"  ⚠ {idx_name} - {e}")

        # 5. Verify schema
        print("\n[5/5] Verifying schema...")

        # Check events table columns
        events_columns = await conn.fetch("""
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'events' ORDER BY ordinal_position
        """)
        print(f"  ✓ events table: {len(events_columns)} columns")

        # Check tables exist
        tables = await conn.fetch("""
            SELECT table_name FROM information_schema.tables
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
            ORDER BY table_name
        """)
        table_names = [t['table_name'] for t in tables]
        required_tables = [
            'users', 'groups', 'events', 'constraints', 'reputation',
            'logs', 'feedback', 'early_feedback', 'ailog', 'user_preferences',
            'event_participants', 'idempotency_keys', 'event_state_transitions', 'event_memories'
        ]
        for table in required_tables:
            if table in table_names:
                print(f"  ✓ {table}")
            else:
                print(f"  ✗ {table} - MISSING!")

        # Check enum types
        enum_types = await conn.fetch("""
            SELECT t.typname FROM pg_type t
            JOIN pg_enum e ON t.oid = e.enumtypid
            GROUP BY t.typname
        """)
        enum_names = [e['typname'] for e in enum_types]
        for enum_name in ['participant_status', 'participant_role']:
            if enum_name in enum_names:
                print(f"  ✓ {enum_name} enum")
            else:
                print(f"  ✗ {enum_name} enum - MISSING!")

        print("\n" + "=" * 60)
        print("✓ Migration completed successfully!")
        print("=" * 60)

    except Exception as e:
        print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(run_migration())
