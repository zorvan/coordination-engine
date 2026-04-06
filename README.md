# Zwischen

`Zwischen` is a coordination system for small groups. The repository currently centers on a production-oriented Telegram bot that helps groups form events, track participation, surface coordination state, and carry memory from one gathering into the next.

The broader project also includes planning tracks for richer client surfaces:

- `telegram-bot/`: the implemented core product
- `telegram-mini-app/`: pre-build product and architecture questions for a Telegram Mini App
- `web-mobile-app/`: pre-build product and architecture questions for a standalone mobile/web app

## Repository Status

Today, the Telegram bot is the runnable part of the repo. The Mini App and mobile app directories are intentionally still in definition mode; they currently contain decision documents rather than application code.

That means this repository is best understood as:

- an active backend and bot implementation
- a growing product/design knowledge base
- a staging ground for future client surfaces

## What The Telegram Bot Does

The bot is a Telegram-based coordination engine built in Python on top of `python-telegram-bot`, SQLAlchemy, and PostgreSQL.

Core capabilities in the current codebase include:

- event planning and creation flows
- join, confirm, cancel, lock, and modify event actions
- private constraint and availability input
- event state transitions and lifecycle handling
- waitlist and organizer-support flows
- memory capture and recall across events
- weekly digest and scheduled background tasks
- mention-driven AI assistance in group chats
- personal participation history and attendance mirror

The product philosophy and detailed behavior live most clearly in:

- [telegram-bot/README.md](/home/zorvan/Work/projects/Zwischen/telegram-bot/README.md)
- [telegram-bot/docs/v3.2/coordination-engine-PRD-v3.2.md](/home/zorvan/Work/projects/Zwischen/telegram-bot/docs/v3.2/coordination-engine-PRD-v3.2.md)

## High-Level Architecture

### `telegram-bot/`

Main implementation area.

- `main.py`: bot entrypoint and handler registration
- `bot/commands/`: slash commands and DM-facing flows
- `bot/handlers/`: callback, mention, membership, and event-flow handlers
- `bot/services/`: event lifecycle, participant, waitlist, memory, and related domain services
- `bot/common/`: shared coordination logic, scheduling, formatting, menus, notifications, and access helpers
- `db/`: SQLAlchemy models, async DB connection code, and schema reference
- `ai/`: LLM client, schemas, and AI-oriented rules
- `tests/`: unit, integration, contract, scenario, and broader regression coverage
- `docs/`: versioned product/design documentation

### `telegram-mini-app/`

Currently contains [telegram-mini-app/MINI_APP_QUESTIONS.md](/home/zorvan/Work/projects/Zwischen/telegram-mini-app/MINI_APP_QUESTIONS.md), a decision framework for building a Telegram Mini App without drifting from the bot's philosophy or architecture.

### `web-mobile-app/`

Currently contains [web-mobile-app/MOBILE_APP_QUESTIONS.md](/home/zorvan/Work/projects/Zwischen/web-mobile-app/MOBILE_APP_QUESTIONS.md), a decision framework for a standalone mobile/app surface layered on the same coordination system.

## Quick Start

The shortest path to running the existing system is to start the Telegram bot.

### 1. Create a virtual environment

```bash
cd telegram-bot
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
```

### 2. Create a `.env`

At minimum:

```env
TELEGRAM_TOKEN=<your-botfather-token>
DB_URL=postgresql+asyncpg://coord_user:coord_pass@localhost:5432/coord_db
AI_ENDPOINT=http://127.0.0.1:8080/v1/
AI_MODEL=qwen/qwen3-coder-next
AI_API_KEY=dummy-key
ENVIRONMENT=development
LOG_LEVEL=INFO
```

Notes:

- `TELEGRAM_TOKEN` is required and validated at startup.
- If `DB_URL` is omitted, the helper scripts default to a local PostgreSQL URL.
- The bot performs startup checks for both LLM and database availability.

### 3. Start the bot

For a fresh local database reset and bootstrap:

```bash
./start.sh
```

To reuse an existing local database container:

```bash
./resume.sh
```

Both scripts live in [telegram-bot/start.sh](/home/zorvan/Work/projects/Zwischen/telegram-bot/start.sh) and [telegram-bot/resume.sh](/home/zorvan/Work/projects/Zwischen/telegram-bot/resume.sh).

## Running Tests And Checks

From `telegram-bot/`:

```bash
pytest
```

There is also a targeted quality script:

```bash
./scripts/check_quality.sh
```

Useful references:

- [telegram-bot/tests/](/home/zorvan/Work/projects/Zwischen/telegram-bot/tests)
- [telegram-bot/scripts/check_quality.sh](/home/zorvan/Work/projects/Zwischen/telegram-bot/scripts/check_quality.sh)

## Infrastructure Notes

- Python support in the bot is documented as `3.13` to `3.14`.
- PostgreSQL is the system of record.
- The runtime dependency switches DB driver by Python version:
  - `asyncpg` for Python `< 3.14`
  - `psycopg` for Python `>= 3.14`
- A Docker-based local stack exists in [telegram-bot/docker-compose.yml](/home/zorvan/Work/projects/Zwischen/telegram-bot/docker-compose.yml), though the shell scripts are the clearest local entrypoint in the current repo.

## Documentation Map

- Product overview: [telegram-bot/README.md](/home/zorvan/Work/projects/Zwischen/telegram-bot/README.md)
- Current PRD: [telegram-bot/docs/v3.2/coordination-engine-PRD-v3.2.md](/home/zorvan/Work/projects/Zwischen/telegram-bot/docs/v3.2/coordination-engine-PRD-v3.2.md)
- User flows: [telegram-bot/docs/v3.2/USER_FLOWS_v3.2.md](/home/zorvan/Work/projects/Zwischen/telegram-bot/docs/v3.2/USER_FLOWS_v3.2.md)
- Implementation notes: [telegram-bot/docs/v2/IMPLEMENTATION.md](/home/zorvan/Work/projects/Zwischen/telegram-bot/docs/v2/IMPLEMENTATION.md)
- Database notes: [telegram-bot/db/README.md](/home/zorvan/Work/projects/Zwischen/telegram-bot/db/README.md)
- Mini App planning: [telegram-mini-app/MINI_APP_QUESTIONS.md](/home/zorvan/Work/projects/Zwischen/telegram-mini-app/MINI_APP_QUESTIONS.md)
- Mobile app planning: [web-mobile-app/MOBILE_APP_QUESTIONS.md](/home/zorvan/Work/projects/Zwischen/web-mobile-app/MOBILE_APP_QUESTIONS.md)

## Current Reality

This repository is not yet a full multi-client platform. It is a solid Telegram-first coordination system with adjacent planning documents for what might come next.

If you are starting work here, the practical default is:

1. begin in `telegram-bot/`
2. treat the bot and PostgreSQL schema as the source of truth
3. use the Mini App and mobile app folders as design inputs, not implementation surfaces
