# AI Coordination Engine - Bot

``
bot/
├── config/              # Configuration management
│   ├── __init__.py
│   ├── settings.py      # Environment variables
│   └── logging.py       # Logging setup
│
├── db/                  # Database layer
│   ├── __init__.py
│   ├── models.py        # SQLAlchemy models (8 tables)
│   ├── connection.py    # Async connection
│   └── schema.sql       # Database schema
│
├── ai/                  # AI coordination engine
│   ├── __init__.py
│   ├── core.py          # Hybrid orchestrator
│   ├── rules.py         # Rule-based logic
│   └── llm.py           # LLM integration
│
├── bot/                 # Telegram bot layer
│   ├── __init__.py
│   ├── main.py          # Entry point
│   ├── commands/        # Command handlers
│   ├── handlers/        # Message handlers
│   └── utils/           # Utilities
│
├── tests/               # Test suite
│   ├── __init__.py
│   └── conftest.py
│
├── docker/              # Docker configs
│   ├── bot.Dockerfile
│   └── docker-compose.yml
│
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
└── README.md
```
