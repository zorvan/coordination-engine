# Telegram AI Coordination Bot

A Python-based Telegram bot for group event coordination with AI-powered scheduling.

## Features

- Group event organization and coordination
- AI suggestions for optimal event times  
- Reputation tracking and soft nudges
- Conditional constraints (e.g., "I join only if Jim joins")
- Automated reminders and notifications
- PostgreSQL for data persistence

## Tech Stack

- **Python 3.11+**
- **PostgreSQL** (via Docker or local)
- **python-telegram-bot v20+**
- **SQLAlchemy** (async ORM)
- **Async OpenAI SDK** (for LLM integration)
- **llama.cpp** (local Qwen3 model)

## Quick Start

### 1. Start PostgreSQL

```bash
docker run -d \
  --name coord_bot_db \
  -e POSTGRES_USER=coord_user \
  -e POSTGRES_PASSWORD=coord_pass \
  -e POSTGRES_DB=coord_db \
  -p 5432:5432 \
  --health-cmd="pg_isready -U coord_user -d coord_db" \
  postgres:15
```

### 2. Setup Database

```bash
createdb -h localhost -U coord_user coord_db
psql -h localhost -U coord_user -d coord_db -f db/schema.sql
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your Telegram bot token
```

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

### 5. Run Bot

```bash
python main.py
```

## Project Structure

```
bot/
├── config/              # Configuration management
├── db/                  # Database layer (models, connection)
├── ai/                  # AI coordination engine
├── bot/                 # Telegram bot layer
│   ├── commands/        # Command handlers
│   ├── handlers/        # Message handlers
│   └── utils/           # Utilities
├── tests/               # Test suite
├── scripts/             # Setup scripts
├── docker/              # Docker configs
└── main.py              # Entry point
```

## Development

### Run Tests

```bash
pytest tests/ -v
```

### Linting

```bash
flake8 .
mypy .
```

### Docker Deployment

```bash
docker build -f docker/bot.Dockerfile -t coord-bot .
docker run -e TELEGRAM_TOKEN=... coord-bot
```

## License

Apache-2.0
