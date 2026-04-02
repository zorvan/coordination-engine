# Coordination Engine Bot

Telegram group coordination bot with hybrid AI + deterministic command flows.

**Version 2.0** — Three-layer architecture with normalized participant management, automated lifecycle events, and comprehensive service integration.

> **Phase 2 Complete** ✅ — Service-oriented architecture, RBAC, threshold enforcement, and mutual dependence visibility implemented. See [IMPLEMENTATION.md](docs/v2/IMPLEMENTATION.md) for details.

This README reflects the **current v2 implementation** with normalized database schema and service-oriented architecture.

## What This Bot Does

The bot helps groups coordinate events with:

- **Three-layer architecture**: Coordination (state management), Materialization (announcements), Memory (post-event narratives)
- **Normalized participant management**: EventParticipant table replaces JSON attendance_list
- **Automated lifecycle events**: Materialization announcements and memory collection triggers
- **Service-oriented design**: Single write paths for all operations with proper validation
- **Idempotency framework**: Prevents duplicate command execution (feature-flagged)
- **Optimistic concurrency control**: Version-based conflict detection for state transitions
- Structured slash-command workflows for speed and reliability
- Mention/reply-based AI orchestration for natural language interaction
- Organizer-controlled event edits with reconfirmation handling
- Attendee private inputs (availability, notes, early feedback) via DM
- Persistent PostgreSQL storage for events, constraints, logs, and reputation-related signals

## Quick Start

**Get running in 15 minutes:** See [docs/v2/QUICKSTART.md](docs/v2/QUICKSTART.md)

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your Telegram token and database URL

# Run database migrations
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/schema.sql

# Start the bot
python main.py
```

## Architecture Overview

### Three-Layer Architecture

```
┌─────────────────────────────────────────┐
│  Layer 3: Memory (Post-Event Narratives)│
│  - Memory collection via DM             │
│  - Memory Weave generation              │
│  - Event lineage                        │
└─────────────────────────────────────────┘
              ▲
┌─────────────────────────────────────────┐
│  Layer 2: Materialization (Announcements)│
│  - Group chat announcements             │
│  - Threshold celebrations               │
│  - Visible momentum                     │
└─────────────────────────────────────────┘
              ▲
┌─────────────────────────────────────────┐
│  Layer 1: Coordination (State Management)│
│  - Event state machine                  │
│  - Participant management               │
│  - Constraint handling                  │
└─────────────────────────────────────────┘
```

**Layer Details:**

1. **Coordination Layer** (`EventStateTransitionService`, `ParticipantService`)
   - Manages event state transitions with validation
   - Enforces business rules and preconditions
   - Provides optimistic concurrency control
   - Single write path for all participant operations

2. **Materialization Layer** (`EventMaterializationService`, `MaterializationOrchestrator`)
   - Automated group announcements at state transitions
   - Milestone notifications ("We hit threshold!", "Event locked", etc.)
   - Progress updates and status broadcasts
   - Private cancellation notices (no public shaming)

3. **Memory Layer** (`EventMemoryService`)
   - Collects post-event narratives via DM
   - Generates Memory Weaves (multi-narrative aggregation)
   - Maintains event lineage and hashtags
   - Preserves plurality of voices (not a summary)

### Service Integration

**Core Services (Single Write Paths):**

| Service | Purpose |
|---------|---------|
| `ParticipantService` | All join/confirm/cancel operations |
| `EventStateTransitionService` | State machine with validation + concurrency |
| `EventLifecycleService` | Orchestrates transitions across all three layers |
| `EventMaterializationService` | Group announcements and DM notifications |
| `EventMemoryService` | Memory collection and weave generation |
| `IdempotencyService` | Prevents duplicate command execution |

All services use async SQLAlchemy with proper transaction management.

## Documentation

| Document | Description |
|----------|-------------|
| [QUICKSTART.md](docs/v2/QUICKSTART.md) | Get running in 15 minutes |
| [USER_FLOWS.md](docs/v2/USER_FLOWS.md) | Complete user flow specifications |
| [PRD v2](docs/v2/coordination-engine-PRD-v2.md) | Product requirements document |
| [IMPLEMENTATION.md](docs/v2/IMPLEMENTATION.md) | Architecture decisions and TODOs |
| [REFACTORING_SUMMARY.md](docs/v2/REFACTORING_SUMMARY.md) | Phase 1 & 2 refactoring summary |

## Core Interaction Modes

### 1) Classic slash commands (deterministic)

When a message starts with `/`, command handlers are used directly.  
This is the fast and predictable mode.

### 2) Mention/reply AI mode (group chat)

When users mention the bot (or reply to a bot message), the bot can infer intent and execute actions such as:

- `organize_event` or `organize_event_flexible`
- `status`, `event_details`, `suggest_time`
- `join`, `confirm` (interested), `cancel`, `lock`
- `constraint_add`, `request_confirmations`
- `opinion` response for advisory text

For sensitive inferred actions with mentioned participants (`constraint_add`, `organize_event*`), the bot requests inline approvals from mentioned users before execution.

### 3) Hybrid private mode (DM with bot)

The bot sends deep links for private interactions:

- private availability input
- private feedback submission
- private attendee notes to organizer context

## Event Model and Lifecycle

**Event States:**

```
proposed → interested → confirmed → locked → completed
                                   ↘ cancelled (from any pre-locked state)
```

| State | Description |
|-------|-------------|
| `proposed` | Event created, waiting for participants |
| `interested` | At least one participant has joined |
| `confirmed` | At least one participant has confirmed attendance |
| `locked` | Finalized, attendance closed, commitments finalized |
| `completed` | Event finished (terminal state) |
| `cancelled` | Event cancelled (terminal state) |

**Automatic State Transitions:**
- `proposed` → `interested`: When first participant joins
- `interested` → `confirmed`: When first participant confirms
- `confirmed` → `locked`: Manual organizer action (with threshold validation)
- `locked` → `completed`: Manual or automatic completion

**Participant Statuses:**

| Status | Description |
|--------|-------------|
| `joined` | Interested in attending |
| `confirmed` | Committed to attend |
| `cancelled` | Withdrawn from event |
| `no_show` | Confirmed but didn't attend |

**Materialization Announcements:**

The bot automatically posts to group chat at key state transitions:

| Trigger | Message |
|---------|---------|
| First join | "🌱 [Name] just joined. We need [N] more for it to happen." |
| Threshold reached | "✨ We have enough. It's happening! [N] people in." |
| Event locked | "🔒 [Event] is locked. See you [time]. [participants]" |
| Event completed | "✅ [Event] is complete! Thanks to all [N] participants." |

*Note: Cancellations are sent privately to organizer only (no public shaming).*

## Key Capabilities

### Event Creation

- `/organize_event`:
  - Group-only flow with structured wizard
  - Description → type → calendar date → time → threshold → duration → invitees → confirmation
- `/organize_event_flexible`:
  - Same flow but without fixed initial time
  - Attendees add availability constraints, then `/suggest_time` proposes optimal time
- Inline calendar for date selection
- Invitee selection supports handles, `@all`, or individual mentions
- Automatic participant record creation for organizer

### Participant Management

- `/join <event_id>`: Join event (creates participant record)
- `/confirm <event_id>`: Confirm attendance commitment
- `/cancel <event_id>`: Cancel participation
- `/back <event_id>`: Unconfirm (revert from confirmed to joined)
- All operations use ParticipantService with proper validation and logging

### Event Coordination

- `/lock <event_id>`: Finalize event (requires organizer, validates thresholds)
  - Automatically finalizes all joined participants to confirmed status
  - Triggers materialization announcement
- `/request_confirmations <event_id>`: Send DM prompts to pending participants
- `/suggest_time <event_id>`: AI-assisted optimal time selection based on constraints

### Event Modification

- `/modify_event <event_id> <changes>`: Organizer-only modifications
- LLM infers patch (time, duration, threshold, description, type, etc.)
- Invalidates confirmations if time/location changes
- Triggers reconfirmation DMs to affected participants

### Constraints and Availability

- `/constraints <event_id> view|add|remove|availability`
- Supports structured and natural language formats
- Private constraints in DM (attendee-only)
- Availability supports multiple time slots
- Integration with time suggestion algorithms

### Feedback and Memory

- `/feedback <event_id>`: Post-event feedback collection
- `/early_feedback <event_id>`: Pre-event feedback and notes
- `/event_note <event_id>`: Private attendee notes to organizer
- Automatic memory collection triggers on event completion

### Monitoring and Status

- `/status`: Current events overview
- `/event_details <event_id>`: Detailed event view with participant status
- `/events`: List all events
- `/profile`: User reputation and activity stats
- `/reputation`: Group reputation rankings

## Data Model (PostgreSQL v2)

### Core Tables

| Table | Description |
|-------|-------------|
| `users` | User profiles and Telegram metadata |
| `groups` | Group information and membership |
| `events` | Event details with normalized schema |
| `event_participants` | **NEW** - Normalized participant records |
| `constraints` | Availability and constraint rules |
| `reputation` | User reputation scores |
| `logs` | Audit trail for all actions |
| `feedback` | Post-event feedback |
| `early_feedback` | Pre-event signals |
| `ailog` | AI interaction history |
| `event_state_transitions` | **NEW** - Audit trail for state changes |
| `idempotency_keys` | **NEW** - Prevents duplicate command execution |
| `event_memories` | **NEW** - Memory Weave storage |

### Event Fields (v2)

| Field | Description |
|-------|-------------|
| `description`, `event_type` | Event details |
| `organizer_telegram_user_id`, `admin_telegram_user_id` | Ownership |
| `scheduled_time`, `duration_minutes`, `threshold_attendance` | Timing |
| `min_participants`, `target_participants` | **NEW** - Viability thresholds |
| `collapse_at`, `lock_deadline` | **NEW** - Auto-cancel and lock deadlines |
| `state`, `version` | State machine + optimistic concurrency |
| `planning_prefs` | JSON configuration |

**Deprecated:** `attendance_list` (migrated to `event_participants` table)

### EventParticipant Table

| Column | Description |
|--------|-------------|
| `event_id`, `telegram_user_id` | Composite primary key |
| `status` | Enum: `joined`, `confirmed`, `cancelled`, `no_show` |
| `role` | Enum: `organizer`, `participant`, `observer` |
| `source` | `slash`, `callback`, `mention`, `dm` |
| `joined_at`, `confirmed_at`, `cancelled_at` | Timestamps |

## Commands

### Core Commands
| Command | Description |
|---------|-------------|
| `/start`, `/help` | Bot introduction |
| `/my_groups` | Your group memberships |
| `/profile` | Personal reputation stats |
| `/reputation` | Group reputation rankings |

### Event Management
| Command | Description |
|---------|-------------|
| `/organize_event` | Create structured event |
| `/organize_event_flexible` | Create flexible event (no fixed time) |
| `/modify_event <id> <changes>` | Edit event (organizer only) |
| `/lock <id>` | Finalize event |
| `/status` | Events overview |
| `/events` | List all events |
| `/event_details <id>` | Detailed event view |

### Participation
| Command | Description |
|---------|-------------|
| `/join <id>` | Join event |
| `/confirm <id>` | Confirm attendance |
| `/cancel <id>` | Cancel participation |
| `/back <id>` | Unconfirm attendance |

### Coordination
| Command | Description |
|---------|-------------|
| `/constraints <id> <action>` | Manage constraints |
| `/suggest_time <id>` | AI time suggestion |
| `/request_confirmations <id>` | Send confirmation requests |

### Feedback & Memory
| Command | Description |
|---------|-------------|
| `/feedback <id> [text]` | Post-event feedback |
| `/early_feedback <id> <@user> <text>` | Pre-event feedback |
| `/event_note <id> <note>` | Private attendee notes |
| `/memory <id>` | View event memory weave |
| `/recall` | List recent group memories |
| `/remember <id> <text>` | Add memory fragment |

## Migration from v1

### Key Changes

| Change | Impact |
|--------|--------|
| `attendance_list` JSON → `event_participants` table | Normalized participation tracking |
| Service-oriented architecture | Single write paths for all operations |
| Automated lifecycle events | Materialization announcements, memory collection |
| Optimistic concurrency control | Version-based conflict detection |
| Idempotency framework | Duplicate command prevention |
| Comprehensive audit logging | State transition tracking |

### Backward Compatibility

- ✅ Legacy `attendance_list` parsing maintained for read operations
- ✅ Gradual migration of display logic to new schema
- ✅ All v1 commands supported with improved internals
- ✅ Migration helper: `ParticipantService.migrate_from_legacy()`

## Development

### Testing

```bash
# Run all tests
pytest

# Run service tests specifically
pytest tests/test_services.py

# Run with coverage
pytest --cov=bot --cov-report=html
```

### Architecture Principles

| Principle | Implementation |
|-----------|----------------|
| **Single Write Paths** | All participant operations → `ParticipantService` |
| **Service Integration** | `EventLifecycleService` coordinates state changes |
| **Validation First** | All transitions validated before execution |
| **Audit Everything** | Comprehensive logging for debugging |
| **Async by Default** | All database operations use async SQLAlchemy |
| **Idempotency** | Duplicate command prevention (feature-flagged) |

### Code Quality Standards

- ✅ Type hints on all public APIs
- ✅ Comprehensive docstrings
- ✅ Async/await throughout
- ✅ Service layer testing with mocks
- ✅ Integration tests for end-to-end flows

### Project Structure

```text
.
├── ai/                          # AI coordination engine
│   ├── core.py                  # Hybrid decision logic
│   ├── llm.py                   # LLM client
│   └── rules.py                 # Rule-based engine
├── bot/
│   ├── commands/                # Slash command handlers
│   │   ├── join.py             # ✅ Refactored (v2 pattern)
│   │   ├── lock.py             # ✅ RBAC + threshold enforcement
│   │   ├── confirm.py          # ✅ Uncommit flow
│   │   ├── event_details.py    # ✅ State-aware menus + mutual dependence
│   │   └── ...
│   ├── handlers/                # Update/message/callback handlers
│   │   └── event_flow.py       # ✅ State-aware navigation
│   ├── services/                # Service layer (single write paths)
│   │   ├── participant_service.py
│   │   ├── event_state_transition_service.py
│   │   ├── event_lifecycle_service.py
│   │   ├── event_materialization_service.py
│   │   ├── event_memory_service.py
│   │   └── idempotency_service.py
│   ├── common/                  # Shared helpers
│   │   ├── rbac.py             # ✅ NEW: Role-based access control
│   │   ├── materialization.py  # Materialization orchestrator
│   │   ├── event_presenters.py # ✅ Mutual dependence visibility
│   │   └── ...
│   └── utils/
├── config/                      # Settings + logging
├── db/                          # Models, connection, schema
├── docs/
│   └── v2/                      # v2 documentation
│       ├── QUICKSTART.md
│       ├── USER_FLOWS.md
│       ├── coordination-engine-PRD-v2.md
│       ├── IMPLEMENTATION.md   # Architecture decisions
│       └── REFACTORING_SUMMARY.md
├── tests/
├── main.py                      # App bootstrap
└── IMPLEMENTATION.md            # Legacy (moved to docs/v2)
```

## Setup

### Requirements

- Python 3.11+
- PostgreSQL 15+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Configure environment

Create `.env` with:

```env
# Required
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz
DB_URL=postgresql+asyncpg://coord_user:coord_pass@localhost:5432/coord_db

# Optional: LLM Configuration
AI_ENDPOINT=http://127.0.0.1:8080/v1
AI_MODEL=qwen/qwen3-coder-next
AI_API_KEY=dummy-key

# Optional: Feature Flags (PRD v2)
ENABLE_MATERIALIZATION=true
ENABLE_MEMORY_LAYER=true
ENABLE_REPUTATION_EFFECTS=false
ENABLE_IDEMPOTENCY=false

# Optional: Logging
LOG_LEVEL=INFO
LOG_LEVEL_TELEGRAM=INFO
LOG_LEVEL_HTTPX=WARNING
JSON_LOGS=false
```

**Note:** The `DB_URL` must use an async driver (`postgresql+asyncpg://`).

### 3) Initialize database

**Option A: Using Docker (Recommended)**
```bash
docker-compose up -d postgres
sleep 5
docker-compose exec postgres psql -U coord_user -d coord_db -f /app/db/schema.sql
```

**Option B: Manual PostgreSQL**
```bash
# Create database and user
sudo -u postgres psql -c "CREATE USER coord_user WITH PASSWORD 'coord_pass';"
sudo -u postgres psql -c "CREATE DATABASE coord_db OWNER coord_user;"

# Apply schema
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/schema.sql
```

### 4) Run bot

```bash
python main.py
```

Expected output:
```
INFO: Startup LLM check: LLM available at http://127.0.0.1:8080/v1
INFO: Startup DB check: Database accessible
INFO: Database initialization complete
INFO: Bot started. Press Ctrl+C to stop.
```

## AI and LLM Configuration

LLM client is OpenAI-compatible and expects:

- `GET /models` for availability check
- `POST /chat/completions` for inference calls

**Used for:**
- Mention intent inference
- Event draft inference and modification patching
- Natural-language constraint parsing
- Early-feedback and post-event feedback structuring
- Conflict-resolution fallback when rules confidence is low

## Current Limitations

| Limitation | Status | Workaround |
|------------|--------|------------|
| `/feedback` requires `completed` state | ⚠️ Known | Manual state completion via admin |
| Test suite outdated | ⚠️ In Progress | Being updated for v2 architecture |
| `reputation` command basic | ⚠️ Known | Use `/profile` for detailed stats |
| Webhook support | ❌ TODO | Use polling (default) |
| RBAC coverage | ⚠️ Partial | Lock command done, more coming |
| Rate limiting | ❌ TODO | Manual monitoring |
| Callback replay protection | ❌ TODO | Short session timeouts |

## New Features (Phase 2)

### RBAC (Role-Based Access Control)

**Permission Checks:**
- `check_event_organizer()` — Organizer-only actions
- `check_event_admin()` — Organizer or admin actions
- `check_can_lock_event()` — Lock event (organizer/admin only)
- `check_can_modify_event()` — Modify event (organizer/admin/confirmed)
- `check_can_submit_private_note()` — Submit notes (NOT organizer)

**Usage:**
```python
from bot.common.rbac import check_can_lock_event

is_authorized, error = await check_can_lock_event(session, event_id, user_id)
if not is_authorized:
    await message.reply_text(f"❌ {error}")
    return
```

### Threshold Enforcement

**Lock Requirements:**
1. User must be organizer or admin
2. Event must be in `confirmed` state
3. `confirmed_count >= min_participants`

**Error Message:**
```
❌ Cannot lock event - below minimum participants.

Required: 3 confirmed
Current: 2 confirmed

Wait for more participants to confirm, or reduce min_participants.
```

### Mutual Dependence Visibility

**PRD v2 Section 2.2.3:** Shows who else is attending and threshold fragility.

**Status Message Features:**
- ✅ Confirmed participant names
- 👀 Interested participant names
- ⚠️ Threshold progress ("We need N more")
- ❗ Fragility warning ("If one more drops, collapses")
- 🤝 User acknowledgment ("You are one of N people others are counting on")

**Example:**
```
📊 Event 123 Status

⚠️ We need 2 more to reach threshold (2/4)
❗ If one more person drops, this event collapses.

🤝 You are one of 5 people others are counting on.
   4 participants depending on you.

Participants:
✅ Confirmed (2): Alice(@alice), Bob(@bob)
👀 Interested (3): Charlie, Diana, You
```

### State-Aware Navigation

**Problem Solved:** "Back" button was confused between navigation and uncommit action.

**Solution:** Separate callbacks:
- `event_unconfirm_` — Revert confirmation
- `event_details_` — Navigate to details (state-aware)
- `event_close_` — Close menu

**Menu Structure:**
| User State | First Row |
|------------|-----------|
| Not joined | ✅ Join |
| Joined | ✅ Confirm + ❌ Cancel |
| Confirmed | ✓ Confirmed + ↩️ Uncommit |

## Production Deployment

### Docker

```bash
docker-compose up -d
docker-compose logs -f bot
```

### Environment Variables for Production

```env
ENVIRONMENT=production
ENABLE_IDEMPOTENCY=true
ENABLE_REPUTATION_EFFECTS=true
LOG_LEVEL=WARNING
JSON_LOGS=true
```

### Webhook (Optional)

For production, use webhooks instead of polling. See [QUICKSTART.md](docs/v2/QUICKSTART.md) for details.

## Troubleshooting

**Database connection errors:**
```
Error: could not connect to server
```
→ Check PostgreSQL is running: `docker-compose ps` or `systemctl status postgresql`  
→ Verify credentials in `.env`  
→ Ensure `DB_URL` uses `postgresql+asyncpg://` prefix

**LLM unavailable:**
```
Warning: Startup LLM check: LLM unavailable
```
→ Check AI endpoint is accessible  
→ Verify `AI_ENDPOINT` and `AI_API_KEY` in `.env`  
→ AI features gracefully degrade if unavailable

See [QUICKSTART.md](docs/v2/QUICKSTART.md) for more troubleshooting tips.

## License

Apache-2.0

## Contributing

1. Read [PRD v2](docs/v2/coordination-engine-PRD-v2.md) for product philosophy
2. Review [USER_FLOWS.md](docs/v2/USER_FLOWS.md) for interaction patterns
3. Check [IMPLEMENTATION.md](docs/v2/IMPLEMENTATION.md) for architecture decisions
4. Review [REFACTORING_SUMMARY.md](docs/v2/REFACTORING_SUMMARY.md) for implementation status
5. Run tests: `pytest`
6. Submit PR with description of changes

## Implementation Status

| Phase | Status | Features |
|-------|--------|----------|
| Phase 1 | ✅ Complete | Services, Materialization, Memory, Idempotency |
| Phase 2 | ✅ Complete | RBAC, Threshold Enforcement, Mutual Dependence |
| Phase 3 | 📋 Planned | Webhook, Callback Protection, Weekly Digest |
| Phase 4 | 📋 Planned | CI/CD, Observability, Secret Management |

See [IMPLEMENTATION.md](docs/v2/IMPLEMENTATION.md) for detailed TODO list.
