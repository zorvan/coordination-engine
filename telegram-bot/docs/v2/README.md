# Coordination Engine v2

## From Coordination Tool to Shared Experience Engine

This directory contains the implementation of Coordination Engine v2, a fundamental transformation of the coordination bot based on the product vision in `coordination-engine-PRD.md`.

---

## 🎯 Vision

> This system exists to help groups bring things into existence together — and to leave behind shared memories strong enough to shape future behavior.

v2 transforms the bot from a **coordination tool** into a **shared-experience engine** that uses coordination as a constraint layer. The real output is **meaning** that accumulates over time.

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [`coordination-engine-PRD.md`](./coordination-engine-PRD.md) | Full product requirements document |
| [`IMPLEMENTATION_SUMMARY.md`](./IMPLEMENTATION_SUMMARY.md) | Technical implementation details |
| [`QUICKSTART.md`](./QUICKSTART.md) | Get started with v2 features |

---

## 🏗️ Architecture

### Three-Layer Design

```
┌─────────────────────────────────────────────────────────┐
│  Layer 3: MEMORY (Persistence)                          │
│  Makes events mean something                            │
│  • Memory Weaves                                        │
│  • Event Lineage                                        │
│  • Group Hashtags                                       │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 2: MATERIALIZATION (Experience)                  │
│  Makes events feel real                                 │
│  • Visible Momentum                                     │
│  • Recognition Loops                                    │
│  • Threshold Celebrations                               │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│  Layer 1: COORDINATION (Constraint)                     │
│  Ensures events are real                                │
│  • State Machine                                        │
│  • Threshold Enforcement                                │
│  • Normalized Participation                             │
└─────────────────────────────────────────────────────────┘
```

---

## ✨ New Features

### Layer 1: Structural Foundations

- ✅ **Normalized participant tracking** — Replaces JSON `attendance_list` with `event_participants` table
- ✅ **EventStateTransitionService** — Single write path for all state changes
- ✅ **Optimistic concurrency control** — Prevents race conditions with `version` field
- ✅ **Idempotency registry** — Prevents duplicate command execution
- ✅ **Structured logging** — JSON logs with correlation IDs
- ✅ **Threshold enforcement** — `min_participants`, `target_participants`, `collapse_at`

### Layer 2: Event Materialization

- ✅ **Materialization announcements** — Bot posts updates at key transitions
- ✅ **Recognition-based nudges** — No public shaming, only positive framing
- ✅ **Mutual dependence visibility** — "X people are counting on you"
- ✅ **Private cancellation handling** — No "[X] cancelled" in group chat
- ✅ **Threshold celebrations** — "We have enough — it's happening!"

### Layer 3: Memory Layer

- ✅ **Memory collection DM flow** — Post-event memory gathering
- ✅ **Memory Weave generation** — Multi-narrative aggregation (not a summary)
- ✅ **Event lineage** — Reference prior similar events
- ✅ **Group hashtags** — Natural language tags for cultural continuity
- ✅ **New commands**: `/memory`, `/recall`, `/remember`

---

## 🚀 Quick Start

### 1. Run Migration

```bash
cd telegram-bot
python scripts/migrate_v2.py
```

### 2. Update Environment

```bash
# .env
ENABLE_MATERIALIZATION=true
ENABLE_MEMORY_LAYER=true
JSON_LOGS=false
```

### 3. Test Features

```bash
python main.py
```

Then in Telegram:
- Create event: `/organize_event`
- Join: `/join [event_id]`
- View memories: `/recall`

See [`QUICKSTART.md`](./QUICKSTART.md) for full guide.

---

## 📦 New Services

### EventStateTransitionService
```python
from bot.services import EventStateTransitionService

service = EventStateTransitionService(session)
event, transitioned = await service.transition(
    event_id=123,
    target_state="locked",
    actor_telegram_user_id=user_id,
    source="slash",
)
```

### ParticipantService
```python
from bot.services import ParticipantService

service = ParticipantService(session)
participant, is_new = await service.join(
    event_id=123,
    telegram_user_id=user_id,
    source="slash",
)
```

### EventMemoryService
```python
from bot.services import EventMemoryService

service = EventMemoryService(bot, session)
await service.start_memory_collection(event)
```

See [`IMPLEMENTATION_SUMMARY.md`](./IMPLEMENTATION_SUMMARY.md) for full API docs.

---

## 🎭 Design Principles

### Recognition over Enforcement
- ❌ No public shaming of cancellations
- ❌ No "low reliability" labels
- ✅ Frame as mutual dependence: "people are counting on you"

### Gravity over Control
- ✅ Events feel real through visible momentum
- ✅ Threshold celebrations create social weight
- ✅ Participant lists build identity

### Memory over Surveillance
- ✅ Store what mattered, not everything
- ✅ Contributor-anonymous fragments by default
- ✅ Detailed logs pruned after 90 days

---

## 📊 Database Changes

### New Tables
- `event_participants` — Normalized participation tracking
- `idempotency_keys` — Duplicate command prevention
- `event_state_transitions` — State change audit trail
- `event_memories` — Memory Weave storage

### Modified Tables
- `events` — Added: `min_participants`, `target_participants`, `collapse_at`, `lock_deadline`, `version`

---

## 🔧 Configuration

### Feature Flags

| Flag | Default | Description |
|------|---------|-------------|
| `ENABLE_MATERIALIZATION` | `true` | Event materialization announcements |
| `ENABLE_MEMORY_LAYER` | `true` | Memory collection and weaves |
| `ENABLE_REPUTATION_EFFECTS` | `false` | Reputation-based priority (future) |
| `ENABLE_IDEMPOTENCY` | `false` | Idempotency checks (production) |
| `JSON_LOGS` | `false` | Structured JSON logging |

---

## 🧪 Testing

### Run Migration Tests
```bash
python scripts/migrate_v2.py
```

### Test Services
```python
# Test EventStateTransitionService
from bot.services import EventStateTransitionService

async with get_session(db_url) as session:
    service = EventStateTransitionService(session)
    validation = await service.validate_transition(1, "locked")
    print(validation)
```

### Test Commands
```bash
# In Telegram
/organize_event
/join [event_id]
/memory [event_id]
/recall
```

---

## 📝 What's Changed

### New Files
```
bot/services/
  ├── __init__.py
  ├── event_state_transition_service.py
  ├── participant_service.py
  ├── idempotency_service.py
  ├── event_materialization_service.py
  └── event_memory_service.py

bot/commands/
  └── memory.py

scripts/
  └── migrate_v2.py
```

### Modified Files
```
db/models.py — New fields, new tables
config/settings.py — Feature flags
config/logging.py — Structured logging
db/connection.py — Sync engine support
bot/utils/nudges.py — Recognition framing
main.py — Memory commands
```

---

## 🎯 Product KPI

**Primary KPI:**
> Richness and frequency of shared experiences that members reference later, replicate, and use as cultural building blocks.

**Secondary signals:**
- Events that acquire their own language / hashtags within the group
- Events referenced in future event proposals
- Events that lead to new collaborations, products, or institutions
- Voluntary re-participation rate

---

## 🚧 Future Work

### Priority 2 (Remaining)
- [ ] Reputation-informed event priority
- [ ] Reliability-based reconfirmation windows
- [ ] Mutual dependence visibility in event details

### Priority 3 (Remaining)
- [ ] Weekly group digest (memories + upcoming)
- [ ] Automated log pruning (90 days)

### Priority 4 (Production Hardening)
- [ ] Webhook + worker queue (replace polling)
- [ ] RBAC with permission matrix
- [ ] Rate limiting
- [ ] CI/CD pipeline
- [ ] Observability dashboards

---

## 🤝 Contributing

1. Read the PRD thoroughly
2. Understand the three-layer architecture
3. Follow design principles in all new code
4. Add tests for new services
5. Update documentation

---

## 📖 References

- **Main PRD:** `coordination-engine-PRD.md`
- **Implementation:** `IMPLEMENTATION_SUMMARY.md`
- **Quick Start:** `QUICKSTART.md`
- **Original README:** `../README.md`

---

## 📜 License

Same as main project.

---

**Built with ❤️ for groups that create together.**
