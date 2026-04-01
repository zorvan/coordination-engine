# Coordination Engine v2 — Implementation Summary

## Overview

This document summarizes the implementation of Coordination Engine v2, transforming the system from a **coordination tool** into a **shared-experience engine** as specified in the PRD (`docs/v2/coordination-engine-PRD.md`).

---

## Architecture Changes

### Three-Layer Architecture (PRD Section 2)

The system is now organized into three purposeful layers:

| Layer | Name | Status |
|-------|------|--------|
| Layer 1 | Coordination (Constraint) | ✅ Hardened with new services |
| Layer 2 | Materialization (Experience) | ✅ Implemented |
| Layer 3 | Memory (Persistence) | ✅ Implemented |

---

## Priority 1: Structural Foundations ✅

### 1.1 Database Schema Updates

**File:** `db/models.py`

#### New Fields on `Event` Model:
- `min_participants` (Integer, default=2) — Absolute floor for viability
- `target_participants` (Integer, default=6) — Desired count for optimal experience
- `collapse_at` (DateTime) — Auto-cancel deadline for underthreshold events
- `lock_deadline` (DateTime) — Cutoff for attendance changes
- `version` (Integer, default=0) — Optimistic concurrency control

#### New Tables:

**`event_participants`** — Normalized participation tracking
- Replaces `attendance_list` JSON column
- Composite PK: `(event_id, telegram_user_id)`
- Fields: `status`, `role`, `joined_at`, `confirmed_at`, `cancelled_at`, `source`
- Enums: `ParticipantStatus`, `ParticipantRole`

**`idempotency_keys`** — Prevents duplicate command execution
- PK: `idempotency_key` (SHA256 hash)
- Fields: `command_type`, `user_id`, `event_id`, `status`, `response_hash`, `expires_at`

**`event_state_transitions`** — Audit trail for state changes
- Records: `from_state`, `to_state`, `actor`, `timestamp`, `reason`, `source`

**`event_memories`** — Memory Weave storage (Layer 3)
- Fields: `fragments`, `hashtags`, `outcome_markers`, `weave_text`, `lineage_event_ids`, `tone_palette`

### 1.2 New Services

#### EventStateTransitionService
**File:** `bot/services/event_state_transition_service.py`

Single write path for all event state transitions.

**Key features:**
- Validates state machine transitions
- Enforces preconditions (e.g., lock requires min_participants)
- Optimistic concurrency control
- Transition audit logging
- Exceptions: `EventStateTransitionError`, `ThresholdNotMetError`, `ConcurrencyConflictError`

**Usage:**
```python
service = EventStateTransitionService(session)
event, transitioned = await service.transition(
    event_id=123,
    target_state="locked",
    actor_telegram_user_id=user_id,
    source="slash",
    expected_version=event.version,
)
```

#### ParticipantService
**File:** `bot/services/participant_service.py`

Single write path for participant management.

**Key methods:**
- `join(event_id, user_id, source)` — Add user as participant
- `confirm(event_id, user_id, source)` — Confirm attendance
- `cancel(event_id, user_id, source)` — Cancel attendance
- `get_confirmed_count(event_id)` — For threshold checks
- `migrate_from_legacy(event)` — Migrate from `attendance_list` JSON

#### IdempotencyService
**File:** `bot/services/idempotency_service.py`

Prevents duplicate command execution from repeated Telegram updates.

**Key methods:**
- `generate_key(command_type, user_id, event_id)` — Deterministic key generation
- `check(key)` — Check if already executed
- `register(key, command_type, user_id, event_id)` — Mark as pending
- `complete(key, response_hash)` — Mark as completed
- `cleanup_expired()` — Remove old records

### 1.3 Structured Logging
**File:** `config/logging.py`

**Features:**
- JSON formatter for production
- Correlation IDs via context variables
- Context fields: `correlation_id`, `event_id`, `user_id`, `chat_id`
- Helper functions: `set_correlation_context()`, `clear_correlation_context()`

**Usage:**
```python
from config.logging import set_correlation_context, clear_correlation_context

set_correlation_context(
    correlation_id=f"command_{update_id}",
    user_id=user.id,
    chat_id=chat.id,
)
try:
    # ... handle command ...
finally:
    clear_correlation_context()
```

### 1.4 Migration Script
**File:** `scripts/migrate_v2.py`

**Run with:**
```bash
python scripts/migrate_v2.py
```

**Migrations:**
1. Adds new columns to `events` table
2. Creates new tables (`event_participants`, `idempotency_keys`, etc.)
3. Migrates existing `attendance_list` JSON to normalized rows
4. Creates performance indexes

---

## Priority 2: Layer 2 — Event Materialization ✅

### 2.1 EventMaterializationService
**File:** `bot/services/event_materialization_service.py`

Posts natural-language updates to group chat at key state transitions.

**Design principles:**
- Recognition over Enforcement
- Gravity over Control
- No public shaming of cancellations

**Key methods:**
- `announce_first_join(event, user, group_chat_id)` — "🌱 [Name] just joined..."
- `announce_join(event, user, confirmed_count, group_chat_id)` — "👋 [Name] just joined..."
- `announce_threshold_reached(event, confirmed_count, group_chat_id)` — "✨ We have enough..."
- `announce_high_reliability_join(event, user, reliability_signal, group_chat_id)` — "🌟 [Name] just committed..."
- `announce_event_locked(event, participants, group_chat_id)` — "🔒 [Event] is locked..."
- `announce_cancellation_private(event, user, organizer_chat_id, remaining_count)` — **DM only**
- `announce_near_collapse(event, confirmed_count, group_chat_id)` — "⚠️ Heads up..."
- `announce_event_completed(event, participant_count, group_chat_id)` — "✅ [Event] is complete!"

### 2.2 Recognition-Based Nudges
**File:** `bot/utils/nudges.py`

Complete rewrite to use recognition framing instead of shame-based messaging.

**PRD compliance:**
- ✅ No public shaming of cancellations
- ✅ No "low reliability" labels
- ✅ Frame as mutual dependence, not penalties
- ✅ "People are counting on you" not "you're unreliable"

**New functions:**
- `generate_cancellation_notice()` — Private notice to organizer only
- `generate_personalized_reconfirmation()` — "We want to make sure you can make it"
- `generate_threshold_celebration()` — Celebration when threshold reached
- `generate_mutual_dependence_reminder()` — "X people are counting on you"
- `generate_near_collapse_alert()` — Threshold fragility awareness
- `generate_reliability_trend_message()` — Personal trend (private, no leaderboard)

---

## Priority 3: Layer 3 — Memory ✅

### 3.1 EventMemoryService
**File:** `bot/services/event_memory_service.py`

Manages the Memory Layer — transforming coordination into shared meaning.

**Design principles:**
- Memory over Surveillance
- Preserve plurality (co-existing voices)
- Bot as "absent friend"

**Key methods:**
- `start_memory_collection(event)` — Triggered on event completion
- `_send_memory_request(participant, event)` — DM requesting memory fragment
- `collect_memory_fragment(event_id, user_id, fragment_text)` — Collect from user
- `add_fragment_to_memory(event_id, fragment)` — Add to EventMemory
- `generate_memory_weave(event)` — Generate multi-narrative weave
- `post_memory_weave(event, group_chat_id)` — Post to group
- `add_hashtags(event_id, hashtags)` — Add 1-3 natural language tags
- `add_outcome_marker(event_id, marker)` — "Led to collaboration X"
- `link_lineage(current_event_id, prior_event_ids)` — Reference prior events
- `get_memory_weave(event_id)` — Retrieve weave
- `get_recent_memories(group_id, limit)` — For /recall
- `suggest_hashtags_from_lineage(event_type, group_id)` — Suggest from history

### 3.2 Memory Commands
**File:** `bot/commands/memory.py`

#### `/memory [event_id]`
View the memory weave for a past event.

**Example:**
```
/memory 123
```

**Response:**
```
📿 How people remember: Badminton • 15 Dec 2025

• "The moment when everyone laughed at the rain" (playful)
• "Intense rallies! My arms are sore" (competitive)
• "So welcoming — felt like home" (warm)

_Tones: playful, competitive, warm_

#badminton #rainyday #sundayfun
```

#### `/recall`
List recent memory weaves for the group.

**Response:**
```
📿 Recent memories for Sunday Sports

• Badminton • 15 Dec
  "The moment when everyone laughed at the rain" #badminton #rainyday

• Hiking • 08 Dec
  "Summit views were worth the climb" #hiking #nature

• Tennis • 01 Dec
  "First time playing — everyone was so encouraging" #tennis #beginner

Use /memory [event_id] to view full weave
```

#### `/remember [event_id] [your memory]`
Add a memory fragment outside the DM window.

**Example:**
```
/remember 123 The moment when everyone laughed at the rain
```

**Response:**
```
✓ Memory added!

Thank you for sharing. This will be woven into the group's memory of the event.
```

---

## Configuration Updates

### New Settings
**File:** `config/settings.py`

```python
# Logging
self.json_logs: bool = os.environ.get("JSON_LOGS", "false").lower() == "true"

# PRD v2: Feature flags
self.enable_materialization: bool = os.environ.get("ENABLE_MATERIALIZATION", "true")
self.enable_memory_layer: bool = os.environ.get("ENABLE_MEMORY_LAYER", "true")
self.enable_reputation_effects: bool = os.environ.get("ENABLE_REPUTATION_EFFECTS", "false")

# PRD v2: Production settings
self.environment: str = os.environ.get("ENVIRONMENT", "development")
self.enable_idempotency: bool = os.environ.get("ENABLE_IDEMPOTENCY", "false")
```

### Environment Variables Template
Create `.env` with:
```bash
# Existing
TELEGRAM_TOKEN=your_bot_token
DB_URL=postgresql+asyncpg://user:pass@localhost/dbname

# v2: Logging
JSON_LOGS=false

# v2: Feature flags
ENABLE_MATERIALIZATION=true
ENABLE_MEMORY_LAYER=true
ENABLE_REPUTATION_EFFECTS=false

# v2: Production
ENVIRONMENT=development
ENABLE_IDEMPOTENCY=false
```

---

## Integration Points

### main.py Updates
**File:** `main.py`

1. Import memory commands:
```python
from bot.commands import (..., memory)
```

2. Register new commands:
```python
command_map = {
    # ... existing commands ...
    # PRD v2: Memory layer commands
    "memory": memory.memory,
    "recall": memory.recall,
    "remember": memory.remember,
}
```

---

## Migration Guide

### Step 1: Database Migration
```bash
# Backup database first!
pg_dump your_database > backup.sql

# Run migration
python scripts/migrate_v2.py
```

### Step 2: Update Dependencies
Check `requirements.txt` — no new dependencies required for core v2 features.

### Step 3: Update Environment
Add v2 feature flags to `.env` (see above).

### Step 4: Test Services
```python
# Test EventStateTransitionService
from bot.services import EventStateTransitionService

async with get_session(db_url) as session:
    service = EventStateTransitionService(session)
    validation = await service.validate_transition(event_id=1, target_state="locked")
    print(validation)  # {"valid": True, "reason": None, "preconditions": {...}}
```

### Step 5: Enable Gradually
1. Start with `ENABLE_MATERIALIZATION=true` only
2. Monitor logs for issues
3. Enable `ENABLE_MEMORY_LAYER=true`
4. Test memory collection flow with a real event
5. Consider `ENABLE_REPUTATION_EFFECTS=true` later (requires more testing)

---

## What's Next (Remaining Work)

### Priority 2 (Remaining)
- [ ] **Wire reputation into priority ordering** — Operational effects for event access
- [ ] **Reconfirmation window logic** — Reliability-informed confirmation deadlines
- [ ] **Visibility of mutual dependence in event detail view** — Show "who is counting on you"

### Priority 3 (Remaining)
- [ ] **Data minimization policy** — Log pruning after 90 days
- [ ] **Weekly group digest** — Recent memories + upcoming events

### Production Hardening (Priority 4)
- [ ] **Webhook + worker queue** — Replace `run_polling()`
- [ ] **RBAC** — Role matrix with permission checks
- [ ] **Rate limiting** — Per-user and per-group limits
- [ ] **CI/CD pipeline** — Lint, tests, security scan, migration validation
- [ ] **Observability** — Prometheus metrics, distributed tracing
- [ ] **Secret management** — No plaintext credentials

---

## Testing Checklist

### Unit Tests
- [ ] `EventStateTransitionService` — All transitions, precondition checks
- [ ] `ParticipantService` — Join/confirm/cancel operations
- [ ] `IdempotencyService` — Duplicate detection, expiry
- [ ] `EventMaterializationService` — Message formatting
- [ ] `EventMemoryService` — Weave generation, fragment collection

### Integration Tests
- [ ] Full event lifecycle: propose → join → confirm → lock → complete → memory
- [ ] Concurrent join/cancel operations (race conditions)
- [ ] Idempotency: duplicate command handling
- [ ] Memory collection DM flow

### Manual Testing
- [ ] Run migration on test database
- [ ] Create event with new threshold fields
- [ ] Test materialization announcements in group
- [ ] Test memory collection after event completion
- [ ] Test /memory, /recall, /remember commands

---

## Design Principles Compliance

### PRD Section 1.3: Three Principles

#### ✅ Recognition over Enforcement
- Cancellations handled privately, no public shaming
- Reliability trends shown as personal feedback, not penalties
- Mutual dependence framing: "people are counting on you"

#### ✅ Gravity over Control
- Event materialization makes events feel real
- Threshold celebrations create momentum
- Visible participant lists build social weight

#### ✅ Memory over Surveillance
- Memory Weaves store what mattered, not everything
- Contributor-anonymous fragments by default
- Detailed logs pruned after 90 days (TODO)

### PRD Section 5.2: Bot Persona

#### ✅ Background Orchestrator
- Materialization messages are facilitator-style, not center stage
- Memory flow: "absent friend" persona
- No gamification language (points, badges, leaderboards)

#### ✅ Relational, Not Administrative
- Messages use "we", "us", "the group"
- Celebration language, not rule enforcement
- No "you have been penalized" messaging

---

## Files Created/Modified

### New Files
```
bot/services/__init__.py
bot/services/event_state_transition_service.py
bot/services/participant_service.py
bot/services/idempotency_service.py
bot/services/event_materialization_service.py
bot/services/event_memory_service.py
bot/commands/memory.py
scripts/migrate_v2.py
```

### Modified Files
```
db/models.py — New fields, new tables
config/settings.py — Feature flags, production settings
config/logging.py — Structured JSON logging, correlation IDs
db/connection.py — Sync engine for migrations
bot/utils/nudges.py — Recognition-based framing
main.py — Register memory commands
```

---

## Support & Documentation

- **PRD:** `docs/v2/coordination-engine-PRD.md`
- **Migration Script:** `scripts/migrate_v2.py`
- **Service Layer:** `bot/services/`
- **Memory Commands:** `bot/commands/memory.py`

For questions about implementation details, refer to inline code comments — each service includes docstrings explaining design decisions aligned with PRD requirements.
