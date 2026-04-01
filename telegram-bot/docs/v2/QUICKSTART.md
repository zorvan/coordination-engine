# Coordination Engine v2 — Quick Start Guide

## Getting Started with v2

This guide helps you start using Coordination Engine v2 features immediately.

---

## 1. Run the Database Migration

```bash
# Navigate to bot directory
cd telegram-bot

# Set database URL (if not in .env)
export DB_URL="postgresql+asyncpg://user:password@localhost/coordination_db"

# Run migration
python scripts/migrate_v2.py
```

**Expected output:**
```
============================================================
Coordination Engine v2 Database Migration
============================================================

Connecting to database...
  ✓ Database connection successful
Migrating events table...
  Adding column: min_participants
  Adding column: target_participants
  ...
  
Creating new tables...
  Creating table: event_participants
  ...

✓ Migration completed successfully!
```

---

## 2. Update Environment Variables

Add to your `.env` file:

```bash
# v2 Features (start with these enabled)
ENABLE_MATERIALIZATION=true
ENABLE_MEMORY_LAYER=true

# Optional: Structured logging
JSON_LOGS=false

# Optional: Enable later
ENABLE_REPUTATION_EFFECTS=false
ENABLE_IDEMPOTENCY=false
```

---

## 3. Start the Bot

```bash
# Standard start
python main.py

# Or with docker
docker-compose up
```

---

## 4. Test New Features

### Test Event Materialization

1. Create an event:
   ```
   /organize_event
   ```

2. Join the event:
   ```
   /join [event_id]
   ```

3. **Expected:** Bot posts to group chat:
   > 🌱 [Your Name] just joined the [event type].
   > We need [N] more for it to happen.

### Test Memory Layer

1. After an event completes, wait for DM from bot:
   > Hey — how was [event type]?
   > Anything that stuck with you? A word, a moment, a photo is enough.

2. Reply with a memory fragment

3. View the weave:
   ```
   /memory [event_id]
   ```

4. View recent memories:
   ```
   /recall
   ```

5. Add memory manually:
   ```
   /remember [event_id] The best part was when everyone laughed at the rain
   ```

---

## 5. Using New Services in Code

### EventStateTransitionService

```python
from bot.services import EventStateTransitionService

async with get_session(db_url) as session:
    service = EventStateTransitionService(session)
    
    # Validate before transitioning
    validation = await service.validate_transition(
        event_id=123,
        target_state="locked"
    )
    
    if validation["valid"]:
        # Execute transition
        event, transitioned = await service.transition(
            event_id=123,
            target_state="locked",
            actor_telegram_user_id=user_id,
            source="slash",
            expected_version=event.version,
        )
```

### ParticipantService

```python
from bot.services import ParticipantService
from db.models import ParticipantRole

async with get_session(db_url) as session:
    service = ParticipantService(session)
    
    # Join event
    participant, is_new = await service.join(
        event_id=123,
        telegram_user_id=user_id,
        source="slash",
        role=ParticipantRole.participant,
    )
    
    # Confirm attendance
    participant, is_new = await service.confirm(
        event_id=123,
        telegram_user_id=user_id,
        source="callback",
    )
    
    # Get confirmed count
    count = await service.get_confirmed_count(event_id=123)
```

### EventMemoryService

```python
from bot.services import EventMemoryService

async with get_session(db_url) as session:
    service = EventMemoryService(bot, session)
    
    # Collect memory fragment
    fragment = await service.collect_memory_fragment(
        event_id=123,
        user_id=user_id,
        fragment_text="The best part was...",
        tone_tag="playful",
    )
    
    # Add to memory
    await service.add_fragment_to_memory(123, fragment)
    
    # Generate and post weave
    await service.post_memory_weave(event, group_chat_id)
```

---

## 6. Monitoring & Debugging

### Check Logs

With `JSON_LOGS=false` (development):
```
2025-12-20 10:30:45 - coord_bot.services.event_state - INFO - Event state transition
```

With `JSON_LOGS=true` (production):
```json
{
  "timestamp": "2025-12-20T10:30:45.123Z",
  "level": "INFO",
  "logger": "coord_bot.services.event_state",
  "message": "Event state transition",
  "event_id": 123,
  "from_state": "confirmed",
  "to_state": "locked",
  "actor": 456,
  "source": "slash"
}
```

### Check Database

```sql
-- Check event state transitions
SELECT * FROM event_state_transitions 
WHERE event_id = 123 
ORDER BY timestamp;

-- Check participants
SELECT * FROM event_participants 
WHERE event_id = 123;

-- Check memory weaves
SELECT event_id, weave_text, hashtags 
FROM event_memories 
WHERE event_id = 123;

-- Check idempotency keys
SELECT * FROM idempotency_keys 
WHERE expires_at > NOW() 
ORDER BY created_at DESC 
LIMIT 10;
```

---

## 7. Common Issues

### Migration Fails

**Error:** `column "min_participants" of relation "events" already exists`

**Solution:** Migration was partially run. Check which columns exist:
```sql
\d events
```

Then manually run remaining migrations or drop and re-run.

---

### Materialization Messages Not Appearing

**Check:** Is `ENABLE_MATERIALIZATION=true` in `.env`?

**Check:** Is bot an admin in the group chat?

**Check:** Bot logs for errors:
```
grep "materialization" bot.log
```

---

### Memory Collection Not Starting

**Check:** Is event state `completed`?

**Check:** Is `ENABLE_MEMORY_LAYER=true`?

**Check:** Were there confirmed participants?

```sql
SELECT event_id, state, completed_at 
FROM events 
WHERE event_id = 123;

SELECT * FROM event_participants 
WHERE event_id = 123 
AND status IN ('confirmed', 'joined');
```

---

## 8. Feature Flags

Control v2 features with environment variables:

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLE_MATERIALIZATION` | `true` | Event materialization announcements |
| `ENABLE_MEMORY_LAYER` | `true` | Memory collection and weaves |
| `ENABLE_REPUTATION_EFFECTS` | `false` | Reputation-based priority (coming soon) |
| `ENABLE_IDEMPOTENCY` | `false` | Idempotency checks (use in production) |
| `JSON_LOGS` | `false` | Structured JSON logging |

---

## 9. Next Steps

### Learn More
- Read the full PRD: `docs/v2/coordination-engine-PRD.md`
- Implementation details: `docs/v2/IMPLEMENTATION_SUMMARY.md`

### Contribute
- Add unit tests for new services
- Implement remaining Priority 2/3 features
- Improve memory weave generation with LLM

### Production Deployment
- Enable `ENABLE_IDEMPOTENCY=true`
- Enable `JSON_LOGS=true`
- Set up monitoring dashboards
- Configure log retention (90 days)

---

## Support

For issues or questions:
1. Check logs first
2. Review implementation summary
3. Test with small group before rolling out widely

Happy coordinating! 🎉
