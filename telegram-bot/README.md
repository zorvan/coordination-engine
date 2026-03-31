# Coordination Engine Bot

Telegram group coordination bot with hybrid AI + deterministic command flows.

This README is aligned with the **current code state** and consolidates the older markdown docs (`bot.md`, `Design-Choices.md`, `Development-Plan.md`, `PROJECT-STRUCTURE.md`, `REFACTORING.md`).

## What This Bot Does

The bot helps groups coordinate events with:

- structured slash-command workflows for speed and reliability
- mention/reply-based AI orchestration for natural language interaction
- organizer-controlled event edits with reconfirmation handling
- attendee private inputs (availability, notes, early feedback) via DM
- persistent PostgreSQL storage for events, constraints, logs, and reputation-related signals

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
- `interested` -> at least one join/interest marker exists
- `confirmed` -> at least one participant has explicit confirmation marker
- `locked` -> finalized, attendance closed
- `completed`, `cancelled` -> terminal states

Attendance encoding:

- plain joined/interest: `telegram_user_id`
- confirmed: `telegram_user_id:confirmed`

Transitions in practice:

- `/join` adds attendee, can move `proposed -> interested`
- `/confirm` (alias `/interested`) marks `:confirmed`, sets `state=confirmed`
- `/back` removes personal `:confirmed` marker and reverts user to joined
- `/cancel` removes user attendance
- `/lock` locks event if current state is `confirmed`

## Key Capabilities

### Event creation

- `/organize_event`:
  - group-only flow
  - description -> type -> calendar date -> time -> threshold -> duration -> invitees -> final confirmation
- `/organize_event_flexible`:
  - same flow but without fixed initial time
  - attendees can add availability constraints, then `/suggest_time`
- inline calendar for date selection
- invitees can be handles or `@all`
- event summary shown before final creation
- created event message includes event ID and action buttons

### Event modification loop

- `/modify_event <event_id> <changes>`
- only organizer can modify
- LLM infers patch (time, duration, threshold, description, type, etc.)
- if event changes before lock, previously confirmed attendees are reset and notified in DM to reconfirm

### Constraints and availability

- `/constraints <event_id> view|add|remove|availability`
- `add` supports:
  - structured format: `@user if_joins|if_attends|unless_joins`
  - natural language format inferred by LLM + explicit confirm/cancel buttons
- supports `@username` and numeric Telegram IDs
- username fallback can query Telegram API if not already in DB
- availability supports multiple slots in one command:
  - `/constraints <event_id> availability YYYY-MM-DD HH:MM,YYYY-MM-DD HH:MM`

Private constraints/availability rules:

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
