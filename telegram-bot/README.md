# Coordination Engine Bot

Telegram group coordination bot with hybrid AI + deterministic command flows.

**Version 2.0** - Three-layer architecture with normalized participant management, automated lifecycle events, and comprehensive service integration.

This README reflects the **current v2 implementation** with normalized database schema and service-oriented architecture.

## What This Bot Does

The bot helps groups coordinate events with:

- **Three-layer architecture**: Coordination (state management), Materialization (announcements), Memory (post-event narratives)
- **Normalized participant management**: EventParticipant table replaces JSON attendance_list
- **Automated lifecycle events**: Materialization announcements and memory collection triggers
- **Service-oriented design**: Single write paths for all operations with proper validation
- Structured slash-command workflows for speed and reliability
- Mention/reply-based AI orchestration for natural language interaction
- Organizer-controlled event edits with reconfirmation handling
- Attendee private inputs (availability, notes, early feedback) via DM
- Persistent PostgreSQL storage for events, constraints, logs, and reputation-related signals

## Architecture Overview

### Three-Layer Architecture

1. **Coordination Layer** (`EventStateTransitionService`)
   - Manages event state transitions with validation
   - Enforces business rules and preconditions
   - Provides optimistic concurrency control

2. **Materialization Layer** (`EventMaterializationService`)
   - Handles automated group announcements
   - Milestone notifications ("We hit threshold!", "Event locked", etc.)
   - Progress updates and status broadcasts

3. **Memory Layer** (`EventMemoryService`)
   - Collects post-event narratives and feedback
   - Generates event summaries and insights
   - Maintains historical event context

### Service Integration

- **EventLifecycleService**: Orchestrates transitions across all layers
- **ParticipantService**: Single write path for all participant operations
- **IdempotencyService**: Prevents duplicate operations
- All services use async SQLAlchemy with proper transaction management

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

Event states:

- `proposed` -> event created
- `interested` -> at least one participant has joined
- `confirmed` -> at least one participant has confirmed attendance
- `locked` -> finalized, attendance closed, commitments finalized
- `completed`, `cancelled` -> terminal states

**Automatic State Transitions:**
- `proposed` → `interested`: When first participant joins
- `interested` → `confirmed`: When first participant confirms
- `confirmed` → `locked`: Manual organizer action (with threshold validation)
- `locked` → `completed`: Manual or automatic completion

**Participant Statuses:**
- `joined`: Interested in attending
- `confirmed`: Committed to attend
- `cancelled`: Withdrawn from event
- `no_show`: Confirmed but didn't attend

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

- `users`: User profiles and Telegram metadata
- `groups`: Group information and membership
- `events`: Event details with normalized schema
- `event_participants`: **NEW** - Normalized participant records
- `constraints`: Availability and constraint rules
- `reputation`: User reputation scores
- `logs`: Audit trail for all actions
- `feedback`: Post-event feedback
- `early_feedback`: Pre-event signals
- `ailog`: AI interaction history

### Event Fields (v2)

- `description`, `event_type`
- `organizer_telegram_user_id`, `admin_telegram_user_id`
- `scheduled_time`, `duration_minutes`, `threshold_attendance`
- `state`, `version` (optimistic concurrency)
- `planning_prefs`: JSON configuration
- **REMOVED**: `attendance_list` (migrated to event_participants)

### EventParticipant Table

- `event_id`, `telegram_user_id`
- `status` (joined/confirmed/cancelled/no_show)
- `role` (organizer/participant)
- `source` (slash/callback/mention/auto)
- `joined_at`, `confirmed_at`, `cancelled_at`
- Proper foreign keys and indexes

## Commands

### Core Commands
- `/start`, `/help` - Bot introduction
- `/my_groups` - User's group memberships
- `/profile` - Personal reputation stats
- `/reputation` - Group reputation rankings

### Event Management
- `/organize_event` - Create structured event
- `/organize_event_flexible` - Create flexible event
- `/modify_event <id> <changes>` - Edit event (organizer only)
- `/lock <id>` - Finalize event
- `/status` - Events overview
- `/events` - List all events
- `/event_details <id>` - Detailed event view

### Participation
- `/join <id>` - Join event
- `/confirm <id>` - Confirm attendance
- `/cancel <id>` - Cancel participation
- `/back <id>` - Unconfirm attendance

### Coordination
- `/constraints <id> <action>` - Manage constraints
- `/suggest_time <id>` - AI time suggestion
- `/request_confirmations <id>` - Send confirmation requests

### Feedback
- `/feedback <id> [text]` - Post-event feedback
- `/early_feedback <id> <@user> <text>` - Pre-event feedback
- `/event_note <id> <note>` - Private notes

## Migration from v1

### Key Changes
- **attendance_list** JSON → **event_participants** table
- Service-oriented architecture with single write paths
- Automated lifecycle events and announcements
- Improved concurrency control and validation
- Comprehensive audit logging

### Backward Compatibility
- Legacy attendance_list parsing maintained for read operations
- Gradual migration of display logic to new schema
- All v1 commands supported with improved internals

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
- **Single Write Paths**: All participant operations route through ParticipantService
- **Service Integration**: EventLifecycleService coordinates state changes across layers
- **Validation First**: All transitions validated before execution
- **Audit Everything**: Comprehensive logging for debugging and analytics
- **Async by Default**: All database operations use async SQLAlchemy

### Code Quality Standards
- Type hints on all public APIs
- Comprehensive docstrings
- Async/await throughout
- Service layer testing with mocks
- Integration tests for end-to-end flows

- in DM, only interested attendees can submit private constraints/availability
- organizer cannot submit attendee-private constraints/availability

### Private attendee notes

- `/event_note <event_id> <note>` in DM only
- only interested attendees can submit notes
- organizer cannot submit attendee notes
- notes are stored as private early-feedback signals and used as planning context

### Confirmation requests and DM fanout

- `/request_confirmations <event_id>`
- posts group summary of pending/confirmed participants
- sends DM confirmation prompts to attendees
- includes back/cancel/lock/status buttons
- organizer receives private-note context summary if available

### AI-assisted time suggestion

- `/suggest_time <event_id>`
- hybrid decision logic:
  - rules for availability/reliability/conflict handling
  - LLM fallback when confidence is low
- if event has no fixed time and suggestion returns parseable datetime, suggested time can be auto-applied
- auto-applied time change can invalidate old confirmations and trigger reconfirmation DM

### Feedback, profile, and reputation pipeline

- `/feedback <event_id> [free text]`
  - inline star flow or natural-language input (LLM parsed)
  - updates `feedback` table and user reputation/profile values
  - blends post-event feedback with stored early-feedback signals
- `/early_feedback <event_id> <@username|telegram_id> <text>`
  - stores normalized pre-event signals (`discussion` in group, `private_peer` in DM)
- `/profile`
  - global reputation
  - top activity reputation
  - feedback and early-feedback stats

## Access and Consistency Rules

- group membership sync runs on all group activity:
  - updates `groups.member_list`
  - upserts users into `users` table
- organizer control:
  - only organizer can modify event
- sensitive participant actions can require explicit approvals in mention-driven mode
- slash commands are kept deterministic; mention inference does not override slash command handling

## Commands

Registered commands:

- `/start`, `/help`
- `/my_groups`
- `/profile`
- `/reputation`
- `/organize_event`
- `/organize_event_flexible`
- `/join`
- `/confirm` (alias `/interested`)
- `/back`
- `/cancel`
- `/lock`
- `/request_confirmations`
- `/early_feedback`
- `/event_note`
- `/modify_event`
- `/constraints`
- `/suggest_time`
- `/status`
- `/events`
- `/event_details`
- `/feedback`

## Data Model (PostgreSQL)

Main tables:

- `users`
- `groups`
- `events`
- `constraints`
- `reputation`
- `logs`
- `feedback`
- `early_feedback`
- `ailog`

Notable event fields:

- `description`
- `organizer_telegram_user_id`
- `scheduled_time`
- `duration_minutes`
- `threshold_attendance`
- `attendance_list`
- `state`
- `locked_at`, `completed_at`

## Project Structure

```text
.
├── ai/                 # Rule engine + LLM client + hybrid coordinator
├── bot/
│   ├── commands/       # Slash command handlers
│   ├── handlers/       # Update/message/callback handlers
│   ├── common/         # Shared helpers (attendance, scheduling, presenters, etc.)
│   └── utils/
├── config/             # Settings + logging setup
├── db/                 # Models, connection, schema, migrations, user helpers
├── docker/             # Container config
├── tests/
└── main.py             # App bootstrap and handler registration
```

## Setup

### Requirements

- Python 3.11+
- PostgreSQL 15+

### 1) Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Configure environment

Create `.env` with:

```env
TELEGRAM_TOKEN=...
DB_URL=postgresql+asyncpg://coord_user:coord_pass@localhost:5432/coord_db
AI_ENDPOINT=http://127.0.0.1:8080/v1
AI_MODEL=qwen/qwen3-coder-next
AI_API_KEY=dummy-key
LOG_LEVEL=INFO
LOG_LEVEL_TELEGRAM=INFO
LOG_LEVEL_HTTPX=WARNING
```

Note: the app uses SQLAlchemy async engine, so `DB_URL` should use an async driver (`postgresql+asyncpg://...`).

### 3) Initialize schema

```bash
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/schema.sql
```

### 4) Apply migrations

```bash
for f in db/migrations/*.sql; do
  echo "Applying $f"
  PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f "$f"
done
```

### 5) Run bot

```bash
python main.py
```

## AI and LLM Configuration

LLM client is OpenAI-compatible and expects:

- `GET /models` for availability check
- `POST /chat/completions` for inference calls

Used for:

- mention intent inference
- event draft inference and modification patching
- natural-language constraint parsing
- early-feedback and post-event feedback structuring/sanitization
- conflict-resolution fallback when rules confidence is low

## Current Limitations / Notes

- `/feedback` requires event state `completed`; state completion automation is limited and may require external workflow/admin handling.
- Existing test suite includes outdated cases and does not fully represent the latest behavior yet.
- `reputation` command currently returns a basic placeholder text; detailed profile data is available in `/profile`.

## License

Apache-2.0
