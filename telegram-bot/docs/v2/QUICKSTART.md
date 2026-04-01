# Quick Start Guide — Coordination Engine Bot v2

**Version:** 2.0  
**Last Updated:** 2026-04-02

Get your coordination bot running in 15 minutes.

---

## Prerequisites

- **Python 3.11+**
- **PostgreSQL 15+**
- **Telegram Bot Token** (from [@BotFather](https://t.me/BotFather))
- **Optional:** LLM endpoint for AI features

---

## Step 1: Clone and Install

```bash
# Clone repository
git clone <repository-url>
cd telegram-bot

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

---

## Step 2: Configure Environment

Create a `.env` file in the project root:

```bash
# Required: Telegram Bot Token
TELEGRAM_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Required: PostgreSQL Database URL (async)
DB_URL=postgresql+asyncpg://coord_user:coord_pass@localhost:5432/coord_db

# Optional: LLM Configuration (for AI features)
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

# Optional: Environment
ENVIRONMENT=development
```

---

## Step 3: Set Up PostgreSQL

### Option A: Using Docker (Recommended)

```bash
# Start PostgreSQL with docker-compose
docker-compose up -d postgres

# Wait for database to be ready
sleep 5

# Verify connection
docker-compose exec postgres psql -U coord_user -d coord_db -c "SELECT 1"
```

### Option B: Manual PostgreSQL Setup

```bash
# Create database and user
sudo -u postgres psql <<EOF
CREATE USER coord_user WITH PASSWORD 'coord_pass';
CREATE DATABASE coord_db OWNER coord_user;
GRANT ALL PRIVILEGES ON DATABASE coord_db TO coord_user;
EOF

# Apply schema
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/schema.sql

# Apply migrations
for f in db/migrations/*.sql; do
  echo "Applying $f"
  PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f "$f"
done
```

---

## Step 4: Initialize Database

If not using Docker, manually initialize the database:

```bash
# Apply schema
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/schema.sql

# Apply migrations (if any)
for f in db/migrations/*.sql; do
  PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f "$f"
done
```

**Note:** The bot automatically creates tables on startup if they don't exist.

---

## Step 5: Run the Bot

```bash
# Development mode
python main.py

# Or use the start script
./start.sh
```

You should see:

```
INFO: Startup LLM check: LLM available at http://127.0.0.1:8080/v1
INFO: Startup DB check: Database accessible at postgresql+asyncpg://...
INFO: Initializing database...
INFO: Database initialization complete
INFO: Bot started. Press Ctrl+C to stop.
```

---

## Step 6: Test the Bot

### Basic Commands

1. **Start the bot:**
   ```
   /start
   ```

2. **View help:**
   ```
   /help
   ```

3. **View your groups:**
   ```
   /my_groups
   ```

### Create Your First Event

1. **Start event creation:**
   ```
   /organize_event
   ```

2. **Follow the wizard:**
   - Select event type (social, sports, work)
   - Enter description
   - Choose date and time
   - Set threshold (minimum participants)
   - Invite participants (@username or @all)

3. **Confirm and create**

### Join an Event

```
/join <event_id>
```

Example:
```
/join 1
```

---

## Architecture Overview

### Three-Layer Design

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

### Service Layer

All operations route through services (single write path):

| Service | Purpose |
|---------|---------|
| `ParticipantService` | Join/confirm/cancel operations |
| `EventStateTransitionService` | State machine with validation |
| `EventLifecycleService` | Orchestrates all three layers |
| `EventMaterializationService` | Group announcements |
| `EventMemoryService` | Memory collection and weave |
| `IdempotencyService` | Prevents duplicate commands |

---

## Key Features

### Event Lifecycle

```
proposed → interested → confirmed → locked → completed
                                   ↘ cancelled (from any pre-locked state)
```

### Participant Statuses

| Status | Description |
|--------|-------------|
| `joined` | Interested in attending |
| `confirmed` | Committed to attend |
| `cancelled` | Withdrew from event |
| `no_show` | Confirmed but didn't attend |

### Commands

#### Core Commands
- `/start`, `/help` - Bot introduction
- `/my_groups` - Your group memberships
- `/profile` - Personal reputation stats
- `/reputation` - Group reputation rankings

#### Event Management
- `/organize_event` - Create structured event
- `/organize_event_flexible` - Create flexible event (no fixed time)
- `/modify_event <id> <changes>` - Edit event (organizer only)
- `/lock <id>` - Finalize event
- `/status` - Events overview
- `/events` - List all events
- `/event_details <id>` - Detailed event view

#### Participation
- `/join <id>` - Join event
- `/confirm <id>` - Confirm attendance
- `/cancel <id>` - Cancel participation
- `/back <id>` - Unconfirm attendance

#### Coordination
- `/constraints <id> <action>` - Manage availability constraints
- `/suggest_time <id>` - AI time suggestion
- `/request_confirmations <id>` - Send confirmation requests

#### Memory Layer (PRD v2)
- `/feedback <id> [text]` - Post-event feedback
- `/memory <id>` - View event memory weave
- `/recall` - List recent group memories
- `/remember <id> <text>` - Add memory fragment

---

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run service tests
pytest tests/test_services.py

# Run with coverage
pytest --cov=bot --cov-report=html
```

### Code Quality

```bash
# Type checking
mypy bot/ ai/ db/

# Linting
flake8 bot/ ai/ db/

# Format checking
black --check bot/ ai/ db/
```

### Database Migrations

Create a new migration:

```bash
# Create migration file
cat > db/migrations/004_add_waitlist.sql <<EOF
-- Add waitlist support
ALTER TABLE events ADD COLUMN waitlist_enabled BOOLEAN DEFAULT FALSE;
ALTER TABLE event_participants ADD COLUMN waitlist_position INTEGER;
EOF

# Apply migration
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/migrations/004_add_waitlist.sql
```

---

## Production Deployment

### Environment Variables for Production

```bash
ENVIRONMENT=production
ENABLE_IDEMPOTENCY=true
ENABLE_REPUTATION_EFFECTS=true
LOG_LEVEL=WARNING
JSON_LOGS=true

# Use webhook instead of polling (recommended for production)
WEBHOOK_URL=https://your-domain.com/webhook
WEBHOOK_SECRET=your-secret-token
```

### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f bot
```

### Webhook Setup (Optional)

For production, use webhooks instead of polling:

```python
# Replace run_polling() with:
await application.run_webhook(
    listen='0.0.0.0',
    port=8443,
    url_path=settings.telegram_token,
    webhook_url=settings.webhook_url,
)
```

---

## Troubleshooting

### Database Connection Errors

**Error:** `could not connect to server`

**Solution:**
1. Check PostgreSQL is running: `docker-compose ps` or `systemctl status postgresql`
2. Verify credentials in `.env`
3. Ensure `DB_URL` uses `postgresql+asyncpg://` prefix

### LLM Unavailable

**Warning:** `Startup LLM check: LLM unavailable`

**Solution:**
1. Check AI endpoint is accessible
2. Verify `AI_ENDPOINT` and `AI_API_KEY` in `.env`
3. AI features will gracefully degrade if unavailable

### Duplicate Command Execution

**Issue:** Commands execute multiple times

**Solution:**
1. Enable idempotency: `ENABLE_IDEMPOTENCY=true`
2. Check for duplicate bot instances
3. Review Telegram polling rate limits

### Migration Failures

**Error:** `relation "event_participants" does not exist`

**Solution:**
```bash
# Re-apply schema
PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f db/schema.sql

# Apply all migrations
for f in db/migrations/*.sql; do
  PGPASSWORD=coord_pass psql -h localhost -U coord_user -d coord_db -f "$f"
done
```

---

## Next Steps

1. **Read the [PRD v2](docs/v2/coordination-engine-PRD-v2.md)** - Understand product philosophy
2. **Review [User Flows](docs/v2/USER_FLOWS.md)** - See all interaction patterns
3. **Check [Implementation.md](IMPLEMENTATION.md)** - Architecture decisions and TODOs
4. **Join the community** - Share your experience and contribute

---

## Support

- **Documentation:** `/docs` folder
- **Issues:** GitHub Issues
- **Discussions:** GitHub Discussions

---

**Happy Coordinating! 🎉**
