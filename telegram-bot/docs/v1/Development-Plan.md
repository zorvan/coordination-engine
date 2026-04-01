📋 Development Plan
Phase 1: Project Setup
- [ ] Initialize Python project (venv, requirements.txt)
- [ ] Docker Compose for local PostgreSQL
- [ ] Config management (env vars, config.py)
- [ ] Project structure (modules: bot/, db/, ai/, models/, utils/)
Phase 2: Database Layer
- [ ] Full schema (6 tables: users, groups, events, constraints, reputation, logs)
- [ ] SQLAlchemy models with relationships
- [ ] Migration setup (alembic)
- [ ] DB connection pool + async session
Phase 3: Telegram Bot Layer
- [ ] python-telegram-bot v20+ setup
- [ ] Polling handler + command routing (/start, /organize_event, /join, /confirm, /cancel, /constraints, /my_groups, /profile, /reputation)
- [ ] Inline buttons for RSVP flow
- [ ] Error handling
Phase 4: AI Coordination Layer
- [ ] Hybrid AI class:
  - Rule-based: Availability, reputation scoring, threshold calculation
  - LLM fallback: OpenAI-compatible endpoint with explicit warnings
  - Confidence scoring for constraint resolution
- [ ] 3-layer decision logic (availability → reliability → conflict)
Phase 5: Event Management Flow
- [ ] /organize_event command (type, time, threshold, invitees)
- [ ] /join → /confirm → /cancel state transitions
- [ ] AI time suggestions (availability + reputation-weighted)
- [ ] Constraint processing (e.g., "I join if Jim joins")
Phase 6: Reputation & Nudges
- [ ] Reputation scoring (decay over time, activity-specific)
- [ ] Automated nudges (reminders before deadlines, low-reliability alerts)
- [ ] Post-event summaries (attendance vs. intent, reputation update)
Phase 7: Logging & Analytics
- [ ] Full action logging (/logs command)
- [ ] AI recommendation tracking (timestamps, suggestions, outcomes)
- [ ] Optional: simple analytics dashboard (later)
Phase 8: Testing & Deployment
- [ ] Unit tests (DB CRUD, AI logic, command handlers)
- [ ] Integration tests (multi-user, constraint resolution)
- [ ] Dockerfile for production deployment
