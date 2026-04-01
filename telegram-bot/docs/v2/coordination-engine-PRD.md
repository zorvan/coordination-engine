# Product Requirements Document
## Coordination Engine — Telegram Bot
### From Coordination Tool to Shared Experience Engine

---

| Field | Value |
|---|---|
| Status | Draft — Engineering Review |
| Product Area | Group Coordination / Social Infrastructure |
| Platform | Telegram Bot (Python / PTB) + PostgreSQL |
| Audience | Engineering Team |
| Core Goal | Richer shared group experiences, not just event attendance |

---

## Table of Contents

1. [Vision & Product Philosophy](#1-vision--product-philosophy)
2. [System Architecture — Three Layers](#2-system-architecture--three-layers)
3. [Feature Specifications](#3-feature-specifications)
4. [Engineering Work — Prioritized Backlog](#4-engineering-work--prioritized-backlog)
5. [Non-Functional Requirements](#5-non-functional-requirements)
6. [Open Design Decisions](#6-open-design-decisions)
7. [What This System Is (And Is Not)](#7-what-this-system-is-and-is-not)

---

## 1. Vision & Product Philosophy

### 1.1 The North Star

> This system exists to help groups bring things into existence together — and to leave behind shared memories strong enough to shape future behavior.

The coordination engine is not a scheduler, reputation tracker, or governance tool. It is a **shared-experience engine that uses coordination as a constraint layer**. Attendance is necessary, but the real output is meaning that accumulates over time.

### 1.2 Product KPI

**Primary KPI:**

> Richness and frequency of shared experiences that members reference later, replicate, and use as cultural building blocks.

**Secondary signals:**
- Events that acquire their own language / hashtags within the group
- Events referenced in future event proposals
- Events that lead to new collaborations, products, or institutions
- Voluntary re-participation rate (same activity type, same members)

### 1.3 Design Philosophy — Three Principles

#### Principle 1: Recognition over Enforcement

People honor commitments when they feel seen and counted on — not when they are penalized. The system must design for **felt commitment**, not forced compliance.

**Mechanism:** Visible mutual dependence, acknowledgment loops, and threshold awareness replace penalties as the commitment driver.

#### Principle 2: Gravity over Control

An event should feel real enough that cancellation feels like abandoning something meaningful — not like breaking a rule. Social gravity scales better than enforcement.

**Mechanism:** Event materialization layer — narrative, visible momentum, participant signals, and event identity build weight over time.

#### Principle 3: Memory over Surveillance

The system should store what mattered, not everything that happened. Minimal necessary data. Human-shaped memory artifacts, not behavioral databases.

**Mechanism:** Post-event Memory Weaves: hashtags, key phrases, outcome markers. No detailed logs retained. Detailed behavioral data is pruned after use.

---

## 2. System Architecture — Three Layers

The product is organized into three purposeful layers. Most coordination systems only implement Layer 1. This product deliberately designs all three.

| Layer | Name | Role |
|---|---|---|
| Layer 1 | Coordination (Constraint) | Ensures events are real: time, scarcity, thresholds, commitment states |
| Layer 2 | Materialization (Experience) | Makes events feel real: narrative, visible momentum, participant signals |
| Layer 3 | Memory (Persistence) | Makes events mean something: references, language, identity, continuity |

---

### 2.1 Layer 1 — Coordination

Current state: largely implemented. Needs hardening and enrichment.

#### Event State Machine

The state machine is correct in its current form and must be preserved as the backbone:

```
proposed → interested → confirmed → locked → completed
                                           ↘ cancelled (exit from any pre-locked state)
```

**Required additions:**
- Each state transition must record: actor, timestamp, reason, and source (`slash` / `callback` / `AI mention`)
- A dedicated `EventStateTransitionService` must be the single write path — no direct state mutation from command handlers
- Transition preconditions must be enforced: `lock` requires minimum confirmed attendance above `threshold_attendance`

#### Threshold-Based Fragility (currently implicit — must become explicit)

> Every event must declare its viability parameters. Implicit thresholds create invisible failure modes.

**Required additions to event model:**

| Field | Purpose |
|---|---|
| `min_participants` | Absolute floor below which event cannot proceed |
| `target_participants` | Desired count for optimal experience |
| `collapse_at` | Timestamp after which underthreshold events auto-cancel |
| `lock_deadline` | Cutoff for attendance changes (partially covers existing `commit_by`) |

#### Attendance Model Refactor

> **CRITICAL:** `attendance_list` JSON column must be replaced with a normalized `event_participants` table. This is blocking for production.

**New table: `event_participants`**

| Column | Type | Notes |
|---|---|---|
| `event_id` | FK → events | Composite PK with `telegram_user_id` |
| `telegram_user_id` | BigInt | Composite PK |
| `status` | Enum | `joined \| confirmed \| cancelled \| no_show` |
| `role` | Enum | `organizer \| participant \| observer` |
| `joined_at` | Timestamp | When user first joined |
| `confirmed_at` | Timestamp | When user confirmed |
| `cancelled_at` | Timestamp | When user cancelled, if applicable |
| `source` | Varchar | `slash \| callback \| mention \| dm` |

---

### 2.2 Layer 2 — Event Materialization

> This layer is almost entirely missing from the current codebase. It is the highest-leverage investment for achieving the product's real KPI.

#### 2.2.1 Events as Living Objects

Events must evolve with context. The current model treats events as static records. Each event should accumulate materialization signals that make it feel increasingly real:

- Event description should support incremental updates (append-style, not replace)
- Milestone announcements — "Court booked", "X confirmed", "We hit threshold" — auto-posted by bot to group chat
- Visible participant list in group context (names, not IDs) shown at key state transitions
- Threshold progress display: "We need 2 more. 4 of 6 confirmed."

#### 2.2.2 Recognition Loops — Commitment as a Social Act

When a user confirms, the system must create a moment of mutual awareness, not just record a state change.

- On confirm: bot posts "[Name] has committed. [N] people are now in." to group
- On threshold reached: bot posts a materialization message celebrating the formation
- On new join by a reliable participant: subtle signal amplification (e.g., "Y — who's been to every [activity] session — just joined")
- On cancellation: system privately informs organizer; no public shaming; silently opens waitlist slot

> **Design rule:** Commitment should feel like a social act witnessed by the group, not a private form submission.

#### 2.2.3 Campaign-Style Event Promotion

Organizers should be able to enrich events over time to build gravity. The bot facilitates this without replacing human voice.

- Event note system (`/event_note`): organizer can add context updates that bot posts to group
- Bot can prompt organizer 24h before event: "Add a final word to build momentum?"
- Reliable members can be optionally tagged in an event summary as signal amplifiers (opt-in, never forced)

> **Design guardrail:** Materialization must reflect genuine reality. Over-promotion of weak events destroys trust faster than under-promotion.

#### 2.2.4 Reputation as Background Signal, Not Score

The existing reputation system is data-collection ready but not yet operational. Reputation must move from **descriptive** to **causal** without becoming a visible score that people optimize for.

**How reputation becomes operational (invisibly):**
- Priority on scarce/oversubscribed events goes to higher-reliability participants — no announcement made
- Lower-reliability participants face earlier reconfirmation windows (system nudge, not punishment label)
- Threshold calculation for event viability considers participant reliability mix, not just raw count
- `/reputation` command shows personal trend, not a leaderboard or score comparison

> The user should feel: *"This group values me showing up."* Not: *"My score went up."*

#### 2.2.5 Organizer as Temporary Role

The current model treats organizer as a fixed identity attached to the event. Over time this accumulates coordination authority in specific members.

- Organizer = role for this event, not a permanent identity marker
- System should occasionally surface "Who wants to organize the next one?" rather than auto-defaulting to prior organizer
- Admin actions (modify event, force cancel) should be available to any confirmed participant in emergencies, logged transparently

---

### 2.3 Layer 3 — Event Memory

> The Memory Layer is what transforms this from a coordination tool into a micro-culture generator. It is the primary differentiation of this product.

#### 2.3.1 The Bot as Absent Friend

After an event completes, the bot's primary persona is that of an "absent friend" people want to tell their story to. This unlocks honest, informal, low-stakes contribution.

**The bot should:**
- DM each participant within a few hours post-event: "Hey — how was it? Anything worth remembering?"
- Accept fragments: short text, a photo, a word, a feeling — anything
- Not ask structured questions — open-ended prompts only
- Never frame contribution as feedback, rating, or evaluation

> **UX principle:** Contributing a memory fragment should feel like telling something to someone, not filling a form or being assessed.

#### 2.3.2 Event Memory Weave

The bot aggregates contributions into a **multi-narrative weave** — not a summary. This is a new object type in the system.

**Structure of an Event Memory Weave:**

| Component | Description |
|---|---|
| Event anchor | Title, date, type, participant count |
| Memory fragments | 1–5 short contributions from participants (anonymous by default) |
| Tone palette | Coexisting tones identified (competitive, warm, chaotic, playful) — never collapsed |
| Outcome markers | Optional: "led to collaboration X", "prompted another event" |
| Group hashtags | 1–3 natural language tags participants use when referencing this event later |

**What the weave is NOT:**
- Not a summary (does not merge voices)
- Not a log (does not record actions or behavioral data)
- Not a rating (no scoring, no rankings)
- Not an authority (no "official takeaway")

> **Design rule:** Preserve plurality. The weave should feel like co-existing voices, not a resolved narrative. Contradictions are features, not bugs.

#### 2.3.3 Memory Storage Model

**New table: `event_memories`**

| Column | Type | Notes |
|---|---|---|
| `event_id` | FK → events | One memory per event |
| `fragments` | JSON array | Each: `{text, contributor_hash, tone_tag, submitted_at}` |
| `hashtags` | JSON array | 1–3 natural language tags |
| `outcome_markers` | JSON array | Optional: follow-on events, collaborations |
| `weave_text` | Text | Bot-generated weave (posted to group) |
| `lineage_event_ids` | JSON array | References to prior similar events |
| `created_at` | Timestamp | |

> **Data minimization policy:** Detailed behavioral logs (action-level) should be pruned after 90 days. Only `event_memories` and reputation aggregates persist long-term. Raw attendance data retained only for active events.

#### 2.3.4 Event Lineage

Events should reference each other. This builds the cultural layer that transforms a group from "people who coordinate" to "a group with shared history."

- When creating a new event of the same type, system suggests: "Last time you did this: [memory anchor]. Reference it?"
- Weaves can link to prior weaves as lineage
- Hashtags from past events surface as suggestions in new events
- Group digest (weekly, optional): recent memories + upcoming events

---

## 3. Feature Specifications

### 3.1 Existing Features — Current State Assessment

| Feature / Command | Status | Gap / Action Required |
|---|---|---|
| `/organize_event`, `/events` | Working | Add `min_participants`, `collapse_at` fields to creation flow |
| `/join`, `/confirm`, `/cancel` | Working | Migrate `attendance_list` to `event_participants` table; add recognition message on confirm |
| `/lock` | Working | Add precondition: block lock if below `min_participants`; add threshold check |
| `/reputation` | Stub only | Implement operational effects (priority, reconfirmation windows); display personal trend |
| Event state machine | Correct logic | Centralize into `EventStateTransitionService`; add transition logging |
| `/constraints` (DM flow) | Working | Preserve — this is a strategic differentiator for private preferences |
| AI hybrid (mention + commands) | Working | Ensure AI actions route through same domain services as slash commands |
| Reputation data model | Partially built | Wire reputation into priority logic and reconfirmation window width |
| `EarlyFeedback` | Built | Ensure `is_private` enforced; anti-bias checks before impacting reputation |
| `nudges.py` | Stub | Rewrite to use recognition framing; remove "low reliability" public messages |
| Post-event feedback | Working | Extend to trigger Memory Weave flow (see Layer 3) |

---

### 3.2 New Features — Required for v1 Completion

#### Feature: Event Materialization Announcements

The bot posts natural-language updates to the group chat at key state transitions.

| Trigger | Bot Message (example) |
|---|---|
| First join | "[Name] just joined the [event]. We need [N] more for it to happen." |
| Threshold reached | "We have enough for [event]. It's happening. [N] people in." |
| High-reliability join | "[Name] just committed." *(Signal only — no explicit reliability score shown)* |
| Event locked | "[Event] is locked. See you [date/time]. [participant list]" |
| Cancellation | **DM to organizer only:** "[Name] had to drop. [N] still in. [Waitlist status]" |
| Near collapse | "Heads up: [event] needs [N] more to stay alive. Deadline: [time]." |

> **Design constraint:** No public shaming of cancellations. No "[X] cancelled" posts in group. Cancellation handling is private between system and organizer.

---

#### Feature: Memory Collection Flow (Post-Event)

Triggered automatically after event state transitions to `completed`.

1. Bot waits 1–3 hours post-event completion (configurable).
2. Bot DMs each confirmed participant: "Hey — how was [event]? Anything that stuck with you? A word, a moment, a photo is enough."
3. Participant replies in DM (any format accepted — text, emoji, image).
4. After 24-hour collection window, bot synthesizes contributions into Event Memory Weave.
5. Bot posts weave to group chat with framing: "Here's how people remember [event]..."
6. Memory stored in `event_memories` table; detailed logs pruned.

**Required new bot commands:**

| Command | Purpose |
|---|---|
| `/remember [event_id]` | Participant adds a memory fragment outside the DM window |
| `/memory [event_id]` | View the memory weave for a past event |
| `/recall` | List recent memory weaves for the group |

---

#### Feature: Visibility of Mutual Dependence

When a user views event details, show who else is in — not as peer pressure, but as relational context.

- Event detail view shows: confirmed names, interested names, how many needed to reach threshold
- User-specific acknowledgment: "You are one of [N] people [Name] is counting on"
- Visible threshold fragility: "If one more person drops, this event collapses"

---

#### Feature: Reliability-Informed Confirmation Windows

Users with lower reliability patterns receive earlier confirmation deadlines for high-stakes events — invisible to others, framed as personalized UX.

- System calculates per-user confirmation window = `base_deadline - reliability_adjustment`
- Low reliability: window may open earlier (more lead time to reconfirm)
- No user is told they have a "reliability penalty" — framed as "we want to make sure you can make it"
- No leaderboard. No public score. Reputation affects access and timing only.

---

## 4. Engineering Work — Prioritized Backlog

### 4.1 Priority 1 — Structural Foundations (Must-Have)

> These items must be completed before any new feature work. They resolve blocking technical risks in the current architecture.

| Work Item | Effort | Why It Blocks |
|---|---|---|
| Migrate `attendance_list` JSON → `event_participants` table | Large | All participation logic depends on this |
| Create `EventStateTransitionService` (single write path) | Medium | Race conditions, duplicate transitions, inconsistent state |
| Add optimistic concurrency control (`version` field on events) | Medium | Concurrent join/cancel/lock operations corrupt state |
| Webhook + worker queue (replace `run_polling`) | Large | Polling is unscalable; duplicate message delivery risk |
| Idempotency key registry for commands | Medium | Duplicate Telegram updates cause duplicate state changes |
| Structured JSON logging with correlation IDs | Medium | Debugging and incident response impossible without it |

---

### 4.2 Priority 2 — Layer 2 Features (Core Product Value)

| Work Item | Effort | Expected Impact |
|---|---|---|
| Event materialization announcements (bot group posts at state transitions) | Medium | Transforms events from silent records to visible social objects |
| Add `min_participants`, `collapse_at` fields and threshold enforcement | Small | Enables threshold fragility logic — the core coordination philosophy |
| Rewrite `nudges.py`: recognition framing, no public cancellation shaming | Small | Current nudges violate product philosophy; will erode trust |
| Wire reputation into priority ordering and reconfirmation window logic | Medium | Reputation becomes causal (operational), not decorative |
| Visibility of mutual dependence in event detail view | Small | Creates recognition loop — "who is counting on me" |
| Organizer role rotation / temporary rights model | Medium | Prevents coordination authority accumulation in single members |

---

### 4.3 Priority 3 — Layer 3 Features (Differentiation)

| Work Item | Effort | Strategic Value |
|---|---|---|
| Memory collection DM flow (post-event) | Medium | Captures the real product output: shared meaning |
| `event_memories` table + Memory Weave generation (LLM) | Medium | Core new data object; primary KPI driver |
| Event lineage: reference prior events in new proposals | Medium | Builds cultural continuity between events |
| `/memory`, `/recall`, `/remember` commands | Small | User access to memory layer |
| Weekly group digest (recent memories + upcoming events) | Small | Keeps memory layer active; drives re-engagement |
| Data minimization: log pruning after 90d, memory retention policy | Medium | Privacy by design; reduces surveillance footprint |

---

### 4.4 Priority 4 — Production Hardening

These items are required for production readiness. They are lower-priority than the above only because the product is still in active design. They must be completed before any public launch.

- RBAC: role matrix (attendee, organizer, group admin, system admin) with permission checks in service layer
- Per-user and per-group rate limiting for commands and AI mention triggers
- LLM output schema validation + safe parser + deterministic fallback
- Callback replay protection (expiry, ownership check, idempotency)
- CI pipeline: lint, unit, integration, security scan, migration validation
- Observability: Prometheus metrics, distributed tracing, SLO dashboards
- Secret management: no plaintext credentials; separate dev/staging/prod configs
- Database: connection pool tuning, index review, backup/restore drills

---

## 5. Non-Functional Requirements

### 5.1 Privacy & Data Ethics

> This is not a surveillance platform. Every technical decision about data collection, storage, and retention must be evaluated against this principle.

- Private constraints (DM flows) must never surface in group context — even in aggregate without explicit opt-in
- Reputation data is personal — never shown as comparative leaderboard
- Memory fragments are contributor-anonymous in group weave by default
- No behavioral tracking beyond what is necessary for coordination functionality
- Log retention: 90 days for action-level logs; long-term only for memory artifacts and aggregated reputation
- GDPR-compatible export/delete workflow must be implemented before public launch

### 5.2 Bot Persona Constraints

- Bot is a background orchestrator, not center stage. First encounter is with the group, not the bot.
- Bot voice: relational, not administrative. It is the "absent friend" in memory flows; the "quiet facilitator" in coordination flows.
- No gamification language (points, engagement badges, leaderboards). Reliability streaks/badges are acceptable only if personal and non-comparative.
- No "you have been penalized" or "your score decreased" messaging — ever.

### 5.3 Telegram Platform Constraints

- Identity is weak on Telegram (multiple accounts possible). Reputation system must be account-level but not treated as authoritative identity proof.
- UI constraints: no complex state visualization in chat. Event weaves and memory output must be readable as plain Telegram messages.
- Group privacy: bot should not store full chat history. Only structured event data and opted-in memory fragments.

---

## 6. Open Design Decisions

The following questions require a product decision before implementation. Engineering should not resolve these unilaterally.

| Question | Options | Implication |
|---|---|---|
| Bot persona in Memory Weave: neutral, relational, or invisible curator? | A) "The event included..." B) "I heard different stories..." C) Just presents fragments | Defines emotional tone and intimacy level of memory layer |
| How visible should others' memory fragments be in the weave? | A) Fully visible B) Partially visible C) Mostly private | Shapes identity formation and trust vs. performance dynamic |
| Should the weave feel like "this represents us" or "this reflects parts of us"? | Represents (unified) vs. Reflects (plural) | Determines whether system drifts toward narrative centralization |
| Should organizer role have any persistence across events of the same type? | Yes (continuity) vs. No (ephemeral per event) | Controls coordination authority accumulation |
| How is memory contribution opt-in structured? | DM flow (current design) vs. Group prompt vs. Both | Affects participation rate and authenticity of fragments |

---

## 7. What This System Is (And Is Not)

### This system IS

- A coordination environment that helps groups bring events into existence
- A materialization layer that makes events feel real and worth showing up for
- A memory layer that preserves meaning without surveillance
- A recognition-first commitment system where trust emerges from felt mutual dependence
- A micro-culture generator for tight-knit groups

### This system is NOT

- A surveillance platform or behavioral database
- An enforcement engine with penalties and punishments
- A gamification system with leaderboards or comparative scoring
- A scheduling assistant or calendar integration *(yet)*
- A governance or decision-making tool

---

> **Core Design Principle**
>
> *Don't force people to honor commitments.*
> *Make commitments feel meaningful enough to honor.*
