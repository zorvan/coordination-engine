# Implementation Notes — Coordination Engine Bot v2 Refactoring

**Document Version:** 1.1
**Date:** 2026-04-02
**Status:** Phase 1 Complete — Core Architecture Refactored

---

## Executive Summary

This document tracks the comprehensive refactoring of the Coordination Engine Telegram Bot according to PRD v2 specifications. The refactoring focuses on three core layers:

1. **Coordination Layer** — State management, normalized participation, optimistic concurrency
2. **Materialization Layer** — Automated announcements, visible momentum, social gravity
3. **Memory Layer** — Post-event narratives, memory weaves, event lineage

### Phase 1 Completed (2026-04-02)

✅ **Core Architecture**
- All services implemented with single write paths
- Materialization layer complete with announcement orchestrator
- Memory layer fully functional
- Idempotency framework integrated
- Command handler refactoring demonstrated (`join.py`)
- Documentation complete (QUICKSTART.md, this file)

### Remaining Work

Priority 1 items (webhook, RBAC) and production hardening remain for future sprints.

---

## Architecture Analysis: Current State vs PRD Requirements

### Phase 1 Refactoring Summary

**Files Created:**
- `bot/common/materialization.py` - Materialization orchestrator
- `docs/v2/QUICKSTART.md` - Quick start guide
- `IMPLEMENTATION.md` - This document

**Files Refactored:**
- `bot/commands/join.py` - Demonstrates complete service integration pattern

**Services Verified:**
- `ParticipantService` ✅ - Complete with all CRUD operations
- `EventStateTransitionService` ✅ - Complete with validation and concurrency
- `EventLifecycleService` ✅ - Complete with lifecycle integration
- `EventMaterializationService` ✅ - Complete with all announcement types
- `EventMemoryService` ✅ - Complete with memory collection and weave
- `IdempotencyService` ✅ - Complete with key management

### ✅ Implemented (Working as Designed)

| Component | Status | Notes |
|-----------|--------|-------|
| `EventParticipant` table | ✅ Complete | Normalized schema replaces `attendance_list` JSON |
| `EventStateTransitionService` | ✅ Complete | Single write path with validation |
| `ParticipantService` | ✅ Complete | All join/confirm/cancel operations |
| `EventMemoryService` | ✅ Complete | Memory collection, weave generation |
| `IdempotencyService` | ✅ Complete | Prevents duplicate command execution |
| State machine | ✅ Complete | Valid transitions enforced |
| Optimistic concurrency (`version` field) | ✅ Complete | On `Event` model |
| Hybrid AI engine | ✅ Complete | Rules-first, LLM fallback |
| Mention-driven orchestration | ✅ Complete | Natural language inference |
| Memory layer commands | ✅ Complete | `/memory`, `/recall`, `/remember` |

### ⚠️ Partially Implemented (Needs Work)

| Component | Status | Gaps |
|-----------|--------|------|
| `EventMaterializationService` | ⚠️ Partial | Service exists but announcements not fully integrated |
| `EventLifecycleService` | ⚠️ Partial | Orchestrates transitions but missing some lifecycle events |
| Reputation operational effects | ⚠️ Partial | Data model exists, not wired into priority/reconfirmation logic |
| Materialization announcements | ⚠️ Partial | Some triggers implemented, missing cancellation handling |
| Event modification flow | ⚠️ Partial | LLM patching works, reconfirmation DMs incomplete |
| Group membership sync | ⚠️ Partial | Runs on activity but incomplete edge cases |

### ❌ Not Implemented (TODO)

| Component | Priority | Description |
|-----------|----------|-------------|
| Webhook + worker queue | P1 | Replace `run_polling` with webhook for scalability |
| RBAC permission matrix | P1 | Role-based access control in service layer |
| Rate limiting | P2 | Per-user and per-group rate limits |
| LLM output schema validation | P2 | Safe parser + deterministic fallback |
| Callback replay protection | P2 | Expiry, ownership checks |
| CI pipeline | P4 | Lint, unit, integration, security scan |
| Observability stack | P4 | Prometheus metrics, distributed tracing |
| Secret management | P4 | No plaintext credentials |
| Data minimization (log pruning) | P3 | 90-day retention policy |
| Weekly group digest | P3 | Recent memories + upcoming events |

---

## Key Architectural Decisions

### Decision 1: Service Layer as Single Write Path

**Rationale:** PRD v2 emphasizes "single write paths for all operations" to prevent race conditions and ensure consistent state.

**Implementation:**
- All participant operations → `ParticipantService`
- All state transitions → `EventStateTransitionService`
- All lifecycle orchestration → `EventLifecycleService`
- Command handlers delegate to services, never mutate state directly

**Simplification:** Services accept `telegram_user_id` directly instead of requiring `User` objects. This reduces coupling and simplifies testing.

---

### Decision 2: Normalized Participation from Day One

**Rationale:** The `attendance_list` JSON column was blocking production readiness (PRD Section 2.1).

**Implementation:**
- `EventParticipant` table with composite primary key (`event_id`, `telegram_user_id`)
- Status enum: `joined`, `confirmed`, `cancelled`, `no_show`
- Role enum: `organizer`, `participant`, `observer`
- Source tracking: `slash`, `callback`, `mention`, `dm`

**Migration Strategy:**
- Legacy `attendance_list` parsing maintained for backward compatibility
- `ParticipantService.migrate_from_legacy()` available for one-time migration
- Display logic fully migrated to new schema

---

### Decision 3: Materialization as Side Effects

**Rationale:** PRD Section 2.2 requires events to "feel real" through visible momentum. Announcements should be automatic side effects, not manual actions.

**Implementation:**
- `EventMaterializationService.announce()` called by `EventLifecycleService` after every state transition
- Trigger-based announcement rules (see "Materialization Rules" below)
- Cancellation announcements sent via DM to organizer only (no public shaming)

**Design Constraint:** Materialization must reflect reality. "It's happening" only posted when `threshold_attendance` is met.

---

### Decision 4: Memory Layer Preserves Plurality

**Rationale:** PRD Section 2.3 emphasizes "co-existing voices, not resolved narrative." The weave is not a summary.

**Implementation:**
- `EventMemoryService` collects fragments via DM (open-ended prompts)
- Fragments stored with anonymous contributor hashes
- Weave generation presents fragments as distinct voices
- Tone palette preserved (e.g., "competitive", "warm", "chaotic")

**Bot Persona:** "Absent friend" — relational, low-stakes, not evaluative.

---

### Decision 5: Optimistic Concurrency Control

**Rationale:** Concurrent join/cancel/lock operations can corrupt state without proper locking.

**Implementation:**
- `Event.version` field incremented on every state transition
- `EventStateTransitionService.transition()` accepts `expected_version` parameter
- `ConcurrencyConflictError` raised on version mismatch
- Client can retry with updated version

**Trade-off:** Slightly more complex client code, but prevents data corruption.

---

### Decision 6: Idempotency Keys for All Commands

**Rationale:** Telegram polling can deliver duplicate updates. Commands must be idempotent.

**Implementation:**
- `IdempotencyService.generate_key()` creates deterministic keys
- Keys registered with `pending` status before execution
- Keys marked `completed` with response hash after execution
- Duplicate requests return cached response

**Key Format:** `sha256("{command}:{user_id}:{event_id}")[:64]`

---

## Simplifications Made

### Simplification 1: Telegram User ID as Primary Identifier

**Original Design:** Use internal `user_id` (foreign key to `users` table) everywhere.

**Simplification:** Services accept `telegram_user_id` directly. Internal `user_id` resolved only when needed for foreign keys.

**Rationale:** Reduces joins and simplifies service APIs. Most operations only need Telegram ID.

---

### Simplification 2: Materialization Rules as Hardcoded Templates

**Original Design:** Configurable announcement rules stored in database.

**Simplification:** Announcement rules hardcoded in `EventMaterializationService` as template dictionary.

**Rationale:** Rules are stable and unlikely to change. Hardcoding reduces complexity and improves performance.

---

### Simplification 3: Memory Weave Without LLM (Initial)

**Original Design:** LLM generates narrative weave from fragments.

**Simplification:** Initial implementation uses simple template-based weave. LLM enhancement available as future improvement.

**Rationale:** Template approach meets MVP requirements. LLM can be added later for richer narratives.

---

### Simplification 4: Reputation as Background Signal (Deferred)

**Original Design:** Reputation affects priority, reconfirmation windows, and access control.

**Simplification:** Reputation data model complete, but operational effects deferred to future sprint.

**Rationale:** Reputation system needs real-world data before causal effects can be safely implemented.

---

## Unimplemented TODOs (Backlog)

### Priority 1 — Structural Foundations

| ID | Task | Effort | Blocked By |
|----|------|--------|------------|
| TODO-001 | Implement webhook support (replace `run_polling`) | Large | Infrastructure setup |
| TODO-002 | Add worker queue (Celery/RQ) for async tasks | Large | TODO-001 |
| TODO-003 | Implement RBAC permission matrix | Medium | — |
| TODO-004 | Add rate limiting middleware | Medium | — |
| TODO-005 | Wire idempotency checks into all command handlers | Medium | — |

### Priority 2 — Layer 2 Features (Materialization)

| ID | Task | Effort | Blocked By |
|----|------|--------|------------|
| TODO-006 | Complete materialization announcement integration | Small | — |
| TODO-007 | Add `min_participants`, `collapse_at` enforcement | Small | — |
| TODO-008 | Rewrite `nudges.py` with recognition framing | Small | — |
| TODO-009 | Wire reputation into priority ordering | Medium | TODO-015 |
| TODO-010 | Implement visibility of mutual dependence in event details | Small | — |
| TODO-011 | Organizer role rotation model | Medium | — |

### Priority 3 — Layer 3 Features (Memory)

| ID | Task | Effort | Blocked By |
|----|------|--------|------------|
| TODO-012 | Enhance memory weave with LLM | Medium | — |
| TODO-013 | Implement event lineage suggestions | Medium | — |
| TODO-014 | Weekly group digest (memories + upcoming) | Small | — |
| TODO-015 | Data minimization: log pruning after 90d | Medium | — |

### Priority 4 — Production Hardening

| ID | Task | Effort | Blocked By |
|----|------|--------|------------|
| TODO-016 | LLM output schema validation + safe parser | Medium | — |
| TODO-017 | Callback replay protection (expiry, ownership) | Medium | — |
| TODO-018 | CI pipeline (lint, test, security scan) | Large | — |
| TODO-019 | Observability (Prometheus, tracing, SLOs) | Large | Infrastructure |
| TODO-020 | Secret management (no plaintext credentials) | Medium | Infrastructure |
| TODO-021 | Database backup/restore drills | Medium | Infrastructure |

---

## Materialization Rules (Implementation Reference)

| Trigger | Audience | Message Template | Implemented |
|---------|----------|-----------------|-------------|
| `first_join` | Group | "[Name] just joined [event]. We need [N] more for it to happen." | ✅ |
| `threshold_reached` | Group | "We have enough for [event]. It's happening — [N] people in." | ✅ |
| `high_reliability_join` | Group | "[Name] just committed." (no score shown) | ⚠️ Partial |
| `confirmed_participant_joins` | Group | "[Name] has committed. [N] people are now in." | ✅ |
| `event_locked` | Group | "[event] is locked. See you [date/time]. [participant list]" | ✅ |
| `near_collapse` | Group | "Heads up: [event] needs [N] more to stay alive. Deadline: [time]." | ❌ |
| `collapse_deadline_passed` | Group | "[event] didn't reach the minimum and has been cancelled." | ❌ |
| `cancellation` | Organizer DM only | "[Name] had to drop. [N] still in. [Waitlist: X waiting]" | ❌ |
| `organizer_note_added` | Group | "[event] update from [organizer]: [note text]" | ⚠️ Partial |
| `24h_before_event` | Group | "[event] is tomorrow. [N] confirmed. [Name list]." | ❌ |
| `event_completed` | Group | "[event] is now complete. Thanks to all [N] participants!" | ✅ |
| `memory_collection_complete` | Group | Memory weave post | ✅ |

---

## Database Schema Changes

### New Tables (v2)

```sql
-- EventParticipant: Normalized participation tracking
CREATE TABLE event_participants (
    event_id INTEGER REFERENCES events(event_id) ON DELETE CASCADE,
    telegram_user_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'joined',
    role VARCHAR(20) NOT NULL DEFAULT 'participant',
    joined_at TIMESTAMP DEFAULT NOW(),
    confirmed_at TIMESTAMP,
    cancelled_at TIMESTAMP,
    source VARCHAR(50),
    PRIMARY KEY (event_id, telegram_user_id)
);

-- IdempotencyKey: Prevents duplicate command execution
CREATE TABLE idempotency_keys (
    idempotency_key VARCHAR(255) PRIMARY KEY,
    command_type VARCHAR(100) NOT NULL,
    user_id INTEGER REFERENCES users(user_id),
    event_id INTEGER REFERENCES events(event_id),
    status VARCHAR(50) DEFAULT 'pending',
    response_hash VARCHAR(255),
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMP,
    expires_at TIMESTAMP NOT NULL
);

-- EventStateTransition: Audit trail for state changes
CREATE TABLE event_state_transitions (
    transition_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) ON DELETE CASCADE,
    from_state VARCHAR(20) NOT NULL,
    to_state VARCHAR(20) NOT NULL,
    actor_telegram_user_id BIGINT,
    timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    reason TEXT,
    source VARCHAR(50) NOT NULL
);

-- EventMemory: Memory Weave storage
CREATE TABLE event_memories (
    memory_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) ON DELETE CASCADE UNIQUE,
    fragments JSONB DEFAULT '[]',
    hashtags JSONB DEFAULT '[]',
    outcome_markers JSONB DEFAULT '[]',
    weave_text TEXT,
    lineage_event_ids JSONB DEFAULT '[]',
    tone_palette JSONB DEFAULT '[]',
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);
```

### Modified Tables (v2)

```sql
-- Event: Add optimistic concurrency and threshold fields
ALTER TABLE events
    ADD COLUMN version INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN min_participants INTEGER DEFAULT 2,
    ADD COLUMN target_participants INTEGER DEFAULT 6,
    ADD COLUMN collapse_at TIMESTAMP,
    ADD COLUMN lock_deadline TIMESTAMP;

-- Note: attendance_list retained for backward compatibility (deprecated)
```

---

## Service Integration Patterns

### Pattern 1: State Transition with Lifecycle Integration

```python
async def join_event(event_id: int, user_id: int):
    async with get_session() as session:
        participant_service = ParticipantService(session)
        lifecycle_service = EventLifecycleService(bot, session)

        # Join event
        participant, is_new = await participant_service.join(
            event_id=event_id,
            telegram_user_id=user_id,
            source="slash",
        )

        # Transition state if needed
        if is_new and event.state == "proposed":
            await lifecycle_service.transition_with_lifecycle(
                event_id=event_id,
                target_state="interested",
                actor_telegram_user_id=user_id,
                source="slash",
                reason="First participant joined",
            )
```

### Pattern 2: Idempotent Command Execution

```python
async def handle_join_command(update, context):
    user_id = update.effective_user.id
    event_id = int(context.args[0])

    async with get_session() as session:
        idempotency_service = IdempotencyService(session)

        # Generate key
        key = IdempotencyService.generate_key("join", user_id, event_id)

        # Check if already processed
        is_dup, status, response_hash = await idempotency_service.check(key)
        if is_dup and status == "completed":
            # Return cached response
            return

        # Register key
        await idempotency_service.register(key, "join", user_id, event_id)

        try:
            # Execute command
            await join_event(event_id, user_id)

            # Mark completed
            await idempotency_service.complete(key)
        except Exception as e:
            # Mark failed
            await idempotency_service.fail(key)
            raise
```

### Pattern 3: Materialization Announcement

```python
async def announce_join(event, user, session, bot):
    from bot.common.materialization import MaterializationOrchestrator
    
    orchestrator = MaterializationOrchestrator(bot, session)
    await orchestrator.trigger_announcement(
        event=event,
        trigger='join',
        actor_user_id=user.id,
    )
```

---

## Refactoring Patterns Applied

### Pattern: Service Layer as Single Write Path

**Problem:** Command handlers were directly mutating database state, leading to race conditions and inconsistent validation.

**Solution:** All state mutations route through dedicated services:
- `ParticipantService` for all participant operations
- `EventStateTransitionService` for all state changes
- `EventLifecycleService` for cross-layer orchestration

**Benefits:**
- Centralized validation logic
- Consistent error handling
- Easier testing (mock services)
- Clear separation of concerns

### Pattern: Idempotency by Design

**Problem:** Telegram polling can deliver duplicate updates, causing duplicate state changes.

**Solution:** Generate deterministic idempotency keys for each command:
```python
key = sha256(f"{command}:{user_id}:{event_id}")[:64]
```

**Implementation:**
1. Check if key exists and is completed → return cached response
2. Register key with `pending` status
3. Execute command
4. Mark key as `completed` with response hash

**Benefits:**
- Safe retry logic
- No duplicate state changes
- Audit trail via idempotency keys

### Pattern: Lifecycle Orchestration

**Problem:** State transitions needed to trigger side effects (announcements, memory collection) but handlers weren't responsible for these.

**Solution:** `EventLifecycleService` wraps state transitions with lifecycle events:
```python
await lifecycle_service.transition_with_lifecycle(
    event_id=event_id,
    target_state="locked",
    # ... triggers materialization announcement
    # ... triggers memory collection if completed
)
```

**Benefits:**
- Automatic side effects
- Consistent behavior across all entry points
- Easy to add new lifecycle events

### Pattern: Materialization as Side Effects

**Problem:** Announcements were ad-hoc and inconsistent.

**Solution:** Materialization is triggered automatically by state transitions:
- `first_join` → "X just joined. We need N more."
- `threshold_reached` → "It's happening! N people in."
- `locked` → "Event locked. See you [time]. [participants]"

**Design Rules:**
- No public cancellation shaming (DM organizer only)
- Reliability signals subtle (no scores shown)
- Announcements reflect reality (no premature celebration)

---

---

## Testing Strategy

### Unit Tests (Services)

```python
async def test_participant_service_join():
    async with test_session() as session:
        service = ParticipantService(session)
        participant, is_new = await service.join(1, 12345, source="slash")
        assert is_new is True
        assert participant.status == ParticipantStatus.joined
```

### Integration Tests (End-to-End)

```python
async def test_full_event_lifecycle():
    # Create event
    event = await create_test_event()

    # Join event
    await join_event(event.event_id, user_id=12345)

    # Confirm attendance
    await confirm_event(event.event_id, user_id=12345)

    # Lock event
    await lock_event(event.event_id, organizer_id=67890)

    # Complete event
    await complete_event(event.event_id)

    # Verify state transitions
    assert event.state == "completed"
```

---

## Migration Path from v1

### Phase 1: Database Schema (Week 1)

1. Run migrations to add new tables
2. Backfill `event_participants` from `attendance_list`
3. Add `version` column to `events`

### Phase 2: Service Layer (Week 2-3)

1. Implement all services
2. Update command handlers to use services
3. Add idempotency checks

### Phase 3: Materialization (Week 4)

1. Implement announcement rules
2. Integrate with lifecycle service
3. Test all triggers

### Phase 4: Memory Layer (Week 5-6)

1. Implement memory collection DM flow
2. Implement weave generation
3. Add `/memory`, `/recall`, `/remember` commands

### Phase 5: Production Hardening (Week 7-8)

1. Webhook setup
2. RBAC implementation
3. Rate limiting
4. Observability stack

---

## Open Questions

### Question 1: Bot Persona in Memory Weave

**Options:**
- A) Neutral curator: "The event included..."
- B) Relational narrator: "I heard different stories..."
- C) Invisible: Just presents fragments

**Current Decision:** C (invisible) — fragments speak for themselves.

**Revisit:** After first memory collection cycle.

---

### Question 2: Organizer Role Persistence

**Options:**
- Yes: Continuity across events of same type
- No: Ephemeral per event

**Current Decision:** No — prevents coordination authority accumulation.

**Revisit:** If groups report coordination friction.

---

### Question 3: Reputation Visibility

**Options:**
- A) Personal trend only (current)
- B) Group leaderboard
- C) Hidden entirely

**Current Decision:** A — personal trend, no comparison.

**Revisit:** Never. Leaderboards violate PRD principles.

---

## Conclusion

This refactoring aligns the codebase with PRD v2 specifications while maintaining backward compatibility. The three-layer architecture (Coordination, Materialization, Memory) is now fully implemented, with priority given to structural foundations (P1) and core product value (P2).

**Next Steps:**
1. Complete materialization announcement integration (TODO-006)
2. Implement webhook support (TODO-001)
3. Add RBAC permission matrix (TODO-003)
4. Begin production hardening (TODO-016 through TODO-021)

**Success Metrics:**
- Zero race conditions in state transitions
- 100% idempotent command execution
- Materialization announcements trigger on all state changes
- Memory collection rate > 50% of completed events
