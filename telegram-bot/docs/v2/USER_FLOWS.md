# User Flow Logics

**Document Version:** 2.0  
**Last Updated:** 2026-04-02  
**Project:** Coordination Engine Telegram Bot

---

## Table of Contents

1. [Overview](#overview)
2. [Event Creation Flow](#1-event-creation-flow)
3. [Event Participation Flow](#2-event-participation-flow)
4. [Event Materialization Announcements Flow](#3-event-materialization-announcements-flow) *(new)*
5. [Mention-Driven AI Orchestration Flow](#4-mention-driven-ai-orchestration-flow)
6. [Constraint Management Flow](#5-constraint-management-flow)
7. [Feedback Flow](#6-feedback-flow)
8. [Event Modification Flow](#7-event-modification-flow)
9. [Time Suggestion Flow](#8-time-suggestion-flow)
10. [Group Membership Sync Flow](#9-group-membership-sync-flow)
11. [Early Feedback Flow](#10-early-feedback-flow)
12. [Memory Layer Flow](#11-memory-layer-flow)
13. [Event Lineage & Note Flow](#12-event-lineage--note-flow) *(new)*
14. [State Transition Diagram](#state-transition-diagram)
15. [Key Services](#key-services)
16. [Database Models](#database-models)
17. [Command Reference](#command-reference)
18. [Resolved Design Decisions](#resolved-design-decisions) *(new)*

---

## Overview

This document describes all user flow logics for the Coordination Engine Telegram Bot. The bot uses a **hybrid coordination engine** with a rules-based core and LLM fallback, supporting both explicit commands and natural language group interactions.

### Architecture Principles

- **Hybrid AI Engine:** Rules-first decision making with LLM fallback for conflicts/low confidence
- **Idempotent Commands:** Prevents duplicate command execution via idempotency keys
- **Optimistic Concurrency:** Version-based conflict detection for state transitions
- **Normalized Participation:** Replaces JSON columns with structured participant tracking
- **Memory Layer:** Stores shared narratives and event lineage
- **Non-Surveillance Platform:** User histories are private; no querying other users' event timelines
- **Plural Voices:** Memory weave preserves multiple perspectives without merging into single narrative
- **Materialization Layer:** Bot actively posts to group at key state transitions to make events feel real

### Design Philosophy Notes

| Principle | Implementation |
|-----------|----------------|
| Feedback is not evaluation | Post-event feedback uses open-ended narrative prompts, not star ratings |
| Bot is weaver, not narrator | Memory weave outputs co-existing fragments, not unified summaries |
| No surveillance | `/recall` shows group memories, not individual user histories |
| Constraints are private | DM-only input, never surfaced publicly to avoid social pressure |
| Commitment is social | Bot announces joins and confirmations to group to create mutual awareness |
| Gravity over enforcement | Events gain social weight through visible momentum, not through penalties |

### Core Modules

| Module | Path | Purpose |
|--------|------|---------|
| Event Creation | `bot/commands/event_creation.py` | Event draft creation with inline keyboards |
| Event Flow | `bot/handlers/event_flow.py` | State machine for participant actions |
| Materialization | `bot/common/materialization.py` | Group announcement posts at state transitions |
| Mentions | `bot/handlers/mentions.py` | AI-driven natural language orchestration |
| Constraints | `bot/commands/constraints.py` | Conditional participation management |
| Feedback | `bot/handlers/feedback.py` | Post-event narrative feedback and reputation updates |
| Memory | `bot/commands/memory.py` | Memory collection, weave generation, lineage |
| Event Note | `bot/commands/event_note.py` | Organizer context updates during event lifecycle |
| AI Core | `ai/core.py` | 3-layer decision logic for scheduling |
| LLM Client | `ai/llm.py` | OpenAI-compatible API wrapper |

---

## 1. Event Creation Flow

**Commands:** `/organize_event`, `/organize_event_flexible`, `/private_organize_event`  
**Source:** `bot/commands/event_creation.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │────▶│  Select     │────▶│  Enter      │
│ Initiates   │     │  Event Type │     │ Description │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Final     │◀────│   Select    │◀────│  Select     │
│ Confirmation│     │  Invitees   │     │   Time      │
└─────────────┘     └─────────────┘     └─────────────┘
      │
      ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│    Event    │◀────│   Review    │◀────│   Select    │
│   Created   │     │  Summary    │     │  Preferences│
└─────────────┘     └─────────────┘     └─────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Check: Prior event of same type exists?            │
│  → If yes: offer lineage prompt (see Flow 12)       │
└─────────────────────────────────────────────────────┘
```

### Flow Stages

| Stage | State Key | Description |
|-------|-----------|-------------|
| Type Selection | `type` | Choose: social, sports, work |
| Description | `description` | Enter event description (max 500 chars) |
| Date Selection | `date_preset` | Today, Tomorrow, Weekend, Next Week, Custom |
| Time Selection | `time_window` | Early-morning, Morning, Afternoon, Evening, Night |
| Duration | `duration` | 30m, 60m, 90m, 120m, 180m |
| Location | `location_type` | Home, Outdoor, Cafe, Office, Gym |
| Budget | `budget_level` | Free, Low, Medium, High |
| Transport | `transport_mode` | Walk, Public Transit, Drive, Any |
| Threshold | `threshold` | Minimum participants required |
| Invitees | `invitees` | @handles or @all group members |
| Final | `final` | Confirm, Modify, or Cancel |

### Threshold Fields Relationship

The PRD specifies three distinct threshold-related fields:

| Field | Description | Source |
|-------|-------------|--------|
| `threshold_attendance` | User-specified minimum for event viability | Collected at Threshold stage |
| `min_participants` | Absolute floor for viability (default: 2) | Derived: `threshold_attendance` or system default |
| `target_participants` | Desired count for optimal experience (default: 6) | Derived: `threshold_attendance * 1.5` or system default |
| `collapse_at` | Auto-cancel deadline for under-threshold events | Calculated: `scheduled_time - 2 hours` |

**Implementation Note:** The UI currently collects a single `threshold_attendance` value. The system derives `min_participants`, `target_participants`, and `collapse_at` with sensible defaults. This may be revisited to expose separate inputs for advanced users.

### Event Modes

| Mode | Description | Lock Behavior |
|------|-------------|---------------|
| `public` (default) | Group-visible event | Manual lock by organizer |
| `flexible` | AI-suggested time | Auto-lock when threshold met |
| `private` | DM-only event | Auto-lock on confirmation |

### LLM-Powered Modifications

During the `final` stage, users can modify the event draft via:
- Inline keyboard revisions
- Free-text natural language commands

**Example:**
```
"Change time to March 8, 2026 at 18:00"
"Increase threshold to 10"
"Add @alice and @bob to invitees"
```

### Key Functions

- `build_date_preset_markup()` - Date selection keyboard
- `build_time_window_markup()` - Time window keyboard
- `build_final_confirmation_markup()` - Final action keyboard
- `_apply_final_stage_patch()` - LLM-based draft modification
- `check_event_lineage(group_id, event_type)` - Check for prior events of same type

---

## 2. Event Participation Flow

**Commands:** `/join`, `/confirm`, callback buttons  
**Source:** `bot/handlers/event_flow.py`, `bot/commands/join.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /join or   │────▶│   Check     │────▶│   Add       │
│ Join Button │     │ Conflicts   │     │ Participant │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Event     │◀────│   Update    │◀────│   Show      │
│   State     │     │  State if   │     │ Confirm     │
│ Transition  │     │  Needed     │     │   Menu      │
└─────────────┘     └─────────────┘     └─────────────┘
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Trigger Materialization Announcement (see Flow 3)  │
└─────────────────────────────────────────────────────┘
```

### Participant Status States

| Status | Description | Can Confirm | Can Cancel |
|--------|-------------|-------------|------------|
| `joined` | Expressed interest | Yes | Yes |
| `confirmed` | Committed to attend | No | Yes (before lock) |
| `cancelled` | Withdrew attendance | No | No |
| `no_show` | Did not attend | No | No |

### Callback Actions

| Callback Pattern | Action | Description |
|------------------|--------|-------------|
| `event_join_{id}` | Join | Mark attendance intent |
| `event_confirm_{id}` | Confirm | Commit to attendance |
| `event_back_{id}` | Back | Revert to interested |
| `event_cancel_{id}` | Cancel | Leave event |
| `event_lock_{id}` | Lock | Organizer locks event |
| `event_details_{id}` | Details | View event info |
| `event_status_{id}` | Status | View participation status |
| `event_constraints_{id}` | Constraints | Set availability |
| `event_logs_{id}` | Logs | View audit trail |
| `event_feedback_{id}` | Feedback | Submit narrative feedback |
| `event_modify_{id}` | Modify | Edit event (organizer only) |

### State Transitions

| Trigger | From State | To State | Condition |
|---------|------------|----------|-----------|
| First join | `proposed` | `interested` | joined_count > 0 |
| First confirm | `interested` | `confirmed` | confirmed_count > 0 |
| Organizer lock | `confirmed` | `locked` | Organizer/admin only |
| All cancel | `confirmed`/`interested` | `proposed` | confirmed_count == 0 |
| Event ends | `locked` | `completed` | Scheduled time passed |
| Under threshold | `locked` | `cancelled` | Auto-cancel at collapse_at |
| Organizer cancel | `proposed`/`interested`/`confirmed` | `cancelled` | Organizer action |

### Conflict Detection

Before joining/confirming, the system checks for:
- Time conflicts with other events
- Duration overlap (default 120 minutes)

**Function:** `find_user_event_conflict()` in `bot/common/scheduling.py`

### Visibility of Mutual Dependence

When a user views event details (`/event_details` or `event_details_{id}` callback):
- Shows confirmed participant names and interested participant names
- Shows threshold progress: "4 of 6 confirmed. We need 2 more."
- Shows user-specific acknowledgment: "You are one of [N] people [Name] is counting on."
- If near collapse: "If one more person drops, this event collapses."

> **Design rule:** This is relational context, not peer pressure. The goal is mutual awareness, not guilt.

---

## 3. Event Materialization Announcements Flow

**Source:** `bot/common/materialization.py`  
**Trigger:** Automatic — fired by `EventLifecycleService` after every state transition and key participation action

> This is a system-initiated flow. No user command triggers it. It runs as a side-effect of state changes, making events feel progressively more real through visible social presence in the group chat.

### Flow Diagram

```
┌─────────────────────┐
│  State Change or    │
│  Participation      │
│  Action Occurs      │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐
│  MaterializationSvc │
│  receives event     │
│  + trigger type     │
└─────────────────────┘
          │
          ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Lookup trigger     │────▶│  Build announcement  │
│  in announcement    │     │  message with        │
│  rule table         │     │  event context       │
└─────────────────────┘     └─────────────────────┘
          │                           │
          │ No rule found             │ Rule found
          ▼                           ▼
┌─────────────────────┐     ┌─────────────────────┐
│  Silent (no post)   │     │  Post to group chat  │
└─────────────────────┘     └─────────────────────┘
                                       │
                          ┌────────────┴────────────┐
                          │ Cancellation trigger     │
                          ▼                         ▼
               ┌─────────────────┐      ┌───────────────────┐
               │  DM to organizer│      │  Open waitlist     │
               │  only (private) │      │  slot silently     │
               └─────────────────┘      └───────────────────┘
```

### Announcement Rule Table

Every trigger maps to a message template. The system fills in event context at runtime.

| Trigger | Audience | Message Template |
|---------|----------|-----------------|
| First join | Group | "[Name] just joined [event]. We need [N] more for it to happen." |
| Threshold reached | Group | "We have enough for [event]. It's happening — [N] people in." |
| High-reliability join | Group | "[Name] just committed." *(no score shown — signal only)* |
| Confirmed participant joins | Group | "[Name] has committed. [confirmed_count] people are now in." |
| Event locked | Group | "[event] is locked. See you [date/time]. [participant name list]" |
| Near collapse (≤ 1 away from min) | Group | "Heads up: [event] needs [N] more to stay alive. Deadline: [time]." |
| Collapse deadline passed | Group | "[event] didn't reach the minimum and has been cancelled." |
| Cancellation | **Organizer DM only** | "[Name] had to drop. [N] still in. [Waitlist: X waiting]" |
| Organizer note added | Group | "[event] update from [organizer]: [note text]" |
| 24h before event | Group | "[event] is tomorrow. [confirmed_count] confirmed. [Name list]." |

### Design Constraints

- **No public cancellation shaming.** Cancellation announcements go to the organizer only, via DM. The group never sees "[X] cancelled."
- **Reliability signal amplification is subtle.** When a high-reliability participant joins, the message does not mention their reliability score, track record, or ranking. It simply notes their commitment as a fact.
- **Materialization must reflect reality.** The system does not post celebratory messages for events that are still fragile. "It's happening" is only posted once `threshold_attendance` is met.
- **Silence is valid.** Not every action produces an announcement. Minor re-joins or re-confirmations after a back-and-forth should not spam the group.

### Key Functions

- `MaterializationService.announce(event_id, trigger, actor_id)` - Main entry point
- `build_announcement(trigger, event, actor)` - Constructs message from template
- `should_announce(trigger, event)` - Guards against spam / duplicate announcements
- `notify_organizer_private(event_id, message)` - DM-only path for cancellations

---

## 4. Mention-Driven AI Orchestration Flow

**Source:** `bot/handlers/mentions.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User       │────▶│  LLM        │────▶│  Action     │
│  Mentions   │     │  Inference  │     │  Classification│
│  @bot       │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                    ┌─────────────────────────┼─────────────────────────┐
                    │                         │                         │
                    ▼                         ▼                         ▼
            ┌─────────────┐           ┌─────────────┐           ┌─────────────┐
            │  Direct     │           │  Needs      │           │  Opinion    │
            │  Execution  │           │  Approval   │           │  (Fallback) │
            └─────────────┘           └─────────────┘           └─────────────┘
                    │                         │
                    ▼                         ▼
            ┌─────────────┐           ┌─────────────┐
            │  Execute    │           │  Send       │
            │  Action     │           │  Approval   │
            │             │           │  Request    │
            └─────────────┘           └─────────────┘
                                              │
                                              ▼
                                      ┌─────────────┐
                                      │  All        │
                                      │  Approve?   │
                                      └─────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │ Yes               │ No                │
                          ▼                   ▼                   │
                  ┌─────────────┐     ┌─────────────┐             │
                  │  Execute    │     │  Cancel     │◀────────────┘
                  │  Action     │     │  Request    │
                  └─────────────┘     └─────────────┘
```

### Inferred Actions

| Action Type | Description | Requires Event ID | Requires Approval | Role Restriction |
|-------------|-------------|-------------------|-------------------|------------------|
| `organize_event` | Create public event | No | No | None |
| `organize_event_flexible` | Create flexible event | No | No | None |
| `join` | Join event | Yes | No | None |
| `confirm` | Confirm attendance | Yes | No | None |
| `cancel` | Cancel attendance | Yes | No | None |
| `lock` | Lock event | Yes | No | **Organizer/Admin only** |
| `suggest_time` | Suggest optimal time | Yes | No | None |
| `status` | Show event status | Yes | No | None |
| `event_details` | Show event details | Yes | No | None |
| `constraint_add` | Add constraint | Yes | Yes (if mentions others) | None |
| `request_confirmations` | Prompt confirmations | Yes | No | None |
| `opinion` | General response | No | No | None |

**Note:** The `lock` action via mention requires an organizer/admin role check before execution, consistent with slash command behavior. This prevents privilege escalation via natural language.

### Approval Workflow

**Triggered when:** `constraint_add` or `organize_event` mentions other participants

1. Generate pending action ID (UUID)
2. Store in `context.bot_data["pending_mention_actions"]`
3. Send approval request with inline keyboard
4. Track approvals from mentioned users
5. Execute when all approve, cancel if any reject

### Context Collection

The bot maintains rolling chat history for context:
- Last 40 messages per group
- Stored in `context.bot_data["chat_history"][chat_id]`
- Used by LLM for action inference

### LLM Inference

**Function:** `llm.infer_group_mention_action(text, history)`

**Prompt includes:**
- User message text
- Recent chat history (last 20 messages)
- Allowed action types
- Constraint type validation

---

## 5. Constraint Management Flow

**Command:** `/constraints`  
**Source:** `bot/commands/constraints.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /constraints│────▶│   Parse     │────▶│  Structured │
│  <event_id> │     │   Action    │     │  Format?    │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │ Yes               │ No                │
                          ▼                   ▼                   │
                  ┌─────────────┐     ┌─────────────┐             │
                  │  Validate   │     │  LLM        │             │
                  │  & Save     │     │  Inference  │             │
                  └─────────────┘     └─────────────┘             │
                                                │                 │
                                                ▼                 │
                                        ┌─────────────┐           │
                                        │  Show       │           │
                                        │  Preview    │           │
                                        └─────────────┘           │
                                                │                 │
                                                ▼                 │
                                        ┌─────────────┐           │
                                        │  User       │           │
                                        │  Confirms?  │◀──────────┘
                                        └─────────────┘
                                                │
                          ┌─────────────────────┼─────────────────────┐
                          │ Yes                 │ No                  │
                          ▼                     ▼                     │
                  ┌─────────────┐       ┌─────────────┐               │
                  │  Save to DB │       │  Cancel     │               │
                  │  + Early    │       │  Request    │◀──────────────┘
                  │  Feedback   │       └─────────────┘
                  └─────────────┘
```

> **Privacy rule:** All constraints are submitted and stored via DM. They are never surfaced in the group chat in any form. The system uses them internally for scheduling and compatibility checks only.

### Constraint Types

| Type | Description | Example |
|------|-------------|---------|
| `if_joins` | Join if target joins | "I join if @alice joins" |
| `if_attends` | Join if target attends | "I join if @bob attends" |
| `unless_joins` | Join unless target joins | "I join unless @charlie joins" |
| `available:{timestamp}` | Availability slot | "available:2026-03-20T18:00" |

### Usage Patterns

#### View Constraints
```bash
/constraints 123 view
```

#### Add Constraint (Structured)
```bash
/constraints 123 add @alice if_joins
/constraints 123 add 456 if_joins  # Numeric user ID
```

#### Add Constraint (Natural Language)
```bash
/constraints 123 add I only join if @alice joins
/constraints 123 add I can't come if @bob is there
```

#### Add Availability Slots
```bash
/constraints 123 availability 2026-03-20 18:00,2026-03-21 10:30
```

#### Remove Constraint
```bash
/constraints 123 remove 1  # constraint_id
```

### LLM Inference

**Function:** `llm.infer_constraint_from_text(text)`

**Returns:**
```json
{
  "constraint_type": "if_joins",
  "target_username": "alice",
  "confidence": 0.8,
  "sanitized_summary": "User joins if Alice joins"
}
```

### Early Feedback Integration

When a constraint is added, an early feedback signal is recorded:

| Constraint Type | Signal Score | Signal Type |
|-----------------|--------------|-------------|
| `if_attends` | 4.2 | trust |
| `if_joins` | 3.8 | trust |
| `unless_joins` | 2.8 | trust |

**Purpose:** Pre-event behavioral signals for reputation analytics

---

## 6. Feedback Flow

**Command:** `/feedback`  
**Source:** `bot/handlers/feedback.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /feedback  │────▶│   Check     │────▶│   Event     │
│  <event_id> │     │   Event     │     │  Completed? │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │ Yes               │ No                │
                          ▼                   ▼                   │
                  ┌─────────────┐     ┌─────────────┐             │
                  │  Has User   │     │  Error:     │             │
                  │  Feedback?  │     │  Not Done   │             │
                  └─────────────┘     └─────────────┘             │
                          │                                       │
          ┌───────────────┼───────────────┐                       │
          │ Yes           │ No            │                       │
          ▼               ▼               │                       │
  ┌─────────────┐ ┌─────────────┐         │                       │
  │  Error:     │ │  Prompt     │         │                       │
  │  Duplicate  │ │  Narrative  │         │                       │
  │             │ │  Response   │         │                       │
  └─────────────┘ └─────────────┘         │                       │
                          │               │                       │
                          ▼               ▼                       │
                  ┌─────────────┐ ┌─────────────┐                 │
                  │  User Types │ │  User Types │                 │
                  │  in DM      │ │  in command │                 │
                  └─────────────┘ └─────────────┘                 │
                          │               │                       │
                          └───────┬───────┘                       │
                                  ▼                               │
                          ┌─────────────┐                         │
                          │  LLM Parses │                         │
                          │  Sentiment  │                         │
                          │  (Internal) │                         │
                          └─────────────┘                         │
                                  │                               │
                                  ▼                               ▼
                          ┌─────────────┐
                          │  Store      │
                          │  Feedback   │
                          └─────────────┘
                                  │
                                  ▼
                          ┌─────────────┐
                          │  Update     │
                          │  Reputation │
                          └─────────────┘
                                  │
                                  ▼
                          ┌─────────────────────────────────────┐
                          │  Trigger Memory Collection DM Flow  │
                          │  (if not already triggered)         │
                          │  → see Flow 11                      │
                          └─────────────────────────────────────┘
```

### Feedback Input Mode: Open-Ended Narrative (Primary)

**Design Principle:** Feedback is not evaluation. The entry point tone defines whether users contribute authentic memory fragments or optimized ratings.

**Bot prompt (sent via DM after event completion):**
```
How was [Event Type]?

Anything that stuck with you? A moment that stood out?
Something that surprised you? Just reply with whatever comes to mind.

(Or use: /feedback 123 <your thoughts>)
```

**Key Points:**
- No star rating keyboard shown by default
- LLM infers numeric signal internally from free text for reputation computation
- Framing invites authentic narrative, not judgment
- Stars are an implementation detail, not a user-facing prompt

#### Alternative: Direct Command (AI-Parsed)
```bash
/feedback 123 Great event! Very well organized, loved the venue.
/feedback 123 Terrible experience, organizer was rude and late.
/feedback 123 The hike was tough but worth it. Met great people.
```

**Note:** If a numeric signal is explicitly needed, the LLM infers it from the text. The star structure exists internally for reputation computation but is not the primary entry point.

### LLM Parsing

**Function:** `llm.infer_feedback_from_text(event_type, text)`

**Returns:**
```json
{
  "score": 4.5,           // Inferred internally, not shown to user
  "weight": 0.8,          // Confidence in inference
  "sanitized_comment": "Great event! Very well organized, loved the venue.",
  "expertise_adjustments": {"social": 0.1}
}
```

### Reputation Updates

#### Global Reputation
```
new_reputation = current * (1 - 0.2 * weight) + score * (0.2 * weight)
```

#### Activity-Specific Expertise
```
new_expertise[activity] = current * (1 - 0.3 * weight) + score * (0.3 * weight)
```

#### Blended Score (with Early Feedback)
```
early_influence = min(0.35, early_weight_total / 6.0)
blended_score = score * (1 - early_influence) + early_avg * early_influence
blended_weight = min(1.0, weight + min(0.25, early_weight_total / 12.0))
```

### Feedback Validation

| Check | Error Message |
|-------|---------------|
| Event not found | "❌ Event not found." |
| Event not completed | "❌ Event is not completed yet." |
| Duplicate feedback | "ℹ️ You have already provided feedback." |
| Empty text | "❌ Please share something — even a single word works." |

---

## 7. Event Modification Flow

**Source:** `bot/handlers/mentions.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  User       │────▶│  Select     │────▶│  Choose     │
│  Requests   │     │  Modify     │     │  Method     │
│  Modify     │     │  Button     │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │ Write Own         │ AI Suggested      │
                          ▼                   ▼                   │
                  ┌─────────────┐     ┌─────────────┐             │
                  │  Prompt for │     │  LLM        │             │
                  │  Free Text  │     │  Analyzes   │             │
                  └─────────────┘     │  Event      │             │
                          │           └─────────────┘             │
                          │                   │                   │
                          ▼                   ▼                   │
                  ┌─────────────────────────────────────────┐     │
                  │         Submit to Admin Approval        │     │
                  └─────────────────────────────────────────┘     │
                                              │                   │
                                              ▼                   │
                                      ┌─────────────┐             │
                                      │  Admin      │             │
                                      │  Receives   │             │
                                      │  DM         │             │
                                      └─────────────┘             │
                                              │                   │
                          ┌───────────────────┼───────────────────┤
                          │ Approve           │ Reject            │
                          ▼                   ▼                   │
                  ┌─────────────┐     ┌─────────────┐             │
                  │  Apply LLM  │     │  Notify     │             │
                  │  Patch      │     │  Requester  │             │
                  └─────────────┘     └─────────────┘             │
                          │                                       │
                          ▼                                       │
                  ┌─────────────┐                                 │
                  │  Notify     │                                 │
                  │  All        │                                 │
                  │  Attendees  │                                 │
                  └─────────────┘                                 │
```

### Modification Methods

#### Write Your Own
User provides free-text modification request:
```
"Change time to March 8, 2026 at 18:00"
"Increase threshold to 10"
"Move location to gym"
```

#### AI Suggested
LLM analyzes event and suggests improvements:
```json
{
  "suggestion": "Consider moving the event to evening hours based on attendee availability patterns."
}
```

### Modifiable Fields

| Field | Type | Validation |
|-------|------|------------|
| `description` | String | Max 500 chars |
| `event_type` | Enum | social, sports, work |
| `scheduled_time` | DateTime | ISO format |
| `duration_minutes` | Integer | 30-720 |
| `threshold_attendance` | Integer | Min 1 |
| `location_type` | Enum | Preset values |
| `budget_level` | Enum | Preset values |
| `transport_mode` | Enum | Preset values |
| `invitees` | List | Add/remove @handles |
| `scheduling_mode` | Enum | fixed, flexible |

### Approval Workflow

1. Requester submits modification
2. Store in `context.bot_data["pending_modify_requests"]`
3. Send DM to event admin with approve/reject buttons
4. Admin decision:
   - **Approve:** Apply LLM patch, notify attendees
   - **Reject:** Notify requester

### Callback Patterns

| Pattern | Action |
|---------|--------|
| `event_modify_{id}` | Initiate modification |
| `modinput_{id}_write` | Choose write mode |
| `modinput_{id}_ai` | Choose AI mode |
| `modinput_{id}_cancel` | Cancel request |
| `modreq_{id}_approve` | Admin approves |
| `modreq_{id}_reject` | Admin rejects |

---

## 8. Time Suggestion Flow

**Command:** `/suggest_time`  
**Source:** `bot/commands/suggest_time.py`, `ai/core.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /suggest_  │────▶│  Collect    │────▶│  Compute    │
│  time <id>  │     │ Constraints │     │ Availability│
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Send      │◀────│   LLM       │◀────│  Calculate  │
│ Suggestion  │     │  Fallback   │     │ Confidence  │
└─────────────┘     └─────────────┘     └─────────────┘
                          ▲
                          │
                    Confidence < 0.7
```

### 3-Layer Decision Logic

#### Layer 1: Availability Check (Rules-Based)
```python
availability = rules_engine.check_availability(event, constraints)
```
- Aggregates availability slots from constraints
- Computes per-user availability scores (0-1)

#### Layer 2: Reliability Computation (Rules-Based)
```python
reliability = rules_engine.compute_reliability(event)
```
- Based on historical attendance
- Activity-specific reputation scores

#### Layer 3: Confidence Calculation
```python
confidence = (avg_availability * 0.5 + avg_reliability / 5 * 0.5)
```

### Decision Branching

| Confidence | Resolution Method |
|------------|-------------------|
| ≥ 0.7 | Rules-based conflict resolution |
| < 0.7 | LLM fallback with private notes |

### LLM Fallback

**Function:** `llm.resolve_conflicts(event, availability, reliability, notes)`

**Prompt includes:**
- Event details (type, threshold, participants)
- Availability scores
- Reliability scores
- Private attendee notes (from early feedback)

**Returns:**
```json
{
  "conflict_detected": true,
  "suggested_time": "2026-03-20T18:00",
  "reasoning": "Best overlap for 80% of attendees",
  "compromises": ["Alternative: 2026-03-21T10:00"]
}
```

### Output Format

```
🤖 AI Time Suggestion for Event 123

Suggested Time: 2026-03-20 18:00
Confidence: 85%

Reasoning:
- 5/6 attendees available
- High reliability scores
- Matches historical preferences

Alternatives:
- 2026-03-21 10:00 (70% availability)
- 2026-03-21 14:00 (60% availability)
```

---

## 9. Group Membership Sync Flow

**Source:** `bot/handlers/membership.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Group      │────▶│  Extract    │────▶│  Check DB   │
│  Message    │     │  Users      │     │  for Group  │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │ Exists            │ New               │
                          ▼                   ▼                   │
                  ┌─────────────┐     ┌─────────────┐             │
                  │  Update     │     │  Create     │             │
                  │  Member     │     │  Group      │             │
                  │  List       │     │  Record     │             │
                  └─────────────┘     └─────────────┘             │
                          │                   │                   │
                          ▼                   ▼                   │
                  ┌─────────────────────────────────────────┐     │
                  │         Sync Users to DB                │     │
                  │  - Create if not exists                 │     │
                  │  - Update display name/username         │     │
                  └─────────────────────────────────────────┘     │
                                              │                   │
                                              ▼                   │
                                      ┌─────────────┐             │
                                      │  Commit     │             │
                                      │  Changes    │             │
                                      └─────────────┘             │
```

### Triggers

| Trigger | Action |
|---------|--------|
| Any group message | Sync sender to DB |
| New member joins | Sync new members to DB |
| Group info changes | Update group record |

### Data Synced

#### Group Record
- `telegram_group_id` (unique identifier)
- `group_name` (updated on change)
- `member_list` (JSON array of Telegram user IDs)
- `group_type` (default: "casual")

#### User Record
- `telegram_user_id` (unique identifier)
- `username` (Telegram handle)
- `display_name` (Full name)
- `reputation` (default: 1.0)
- `expertise_per_activity` (JSON)

### Error Handling

- Sync failures are logged but don't block message processing
- Bot continues functioning without membership data
- Retry on next group activity

---

## 10. Early Feedback Flow

**Source:** `bot/common/early_feedback.py`

### Flow Diagram

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Behavioral │────▶│  Parse      │────▶│  Store      │
│  Signal     │     │  Signal     │     │  Early      │
│  Detected   │     │  Type       │     │  Feedback   │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                                              ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Aggregate  │◀────│  Event      │◀────│  Post-Event │
│  into Final │     │  Completed  │     │  Feedback   │
│  Feedback   │     │             │     │  Submitted  │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Signal Sources

| Source Type | Description | Example |
|-------------|-------------|---------|
| `constraint` | Conditional participation | "I join if @alice joins" |
| `discussion` | Group chat behavior | Helpful suggestions |
| `private_peer` | Private feedback | DM to bot about attendee |
| `system` | Automated signals | No-show detection |

### Signal Types

| Signal Type | Range | Description |
|-------------|-------|-------------|
| `overall` | 0-5 | General impression |
| `reliability` | 0-5 | Punctuality, attendance |
| `cooperation` | 0-5 | Helpfulness, flexibility |
| `civility` | 0-5 | Respectful behavior (higher is better) |
| `commitment` | 0-5 | Follow-through on promises |
| `trust` | 0-5 | Interpersonal trust |

**Note:** The signal type was renamed from `toxicity` to `civility` to maintain consistent direction (higher score = better behavior) across all signal types. This prevents confusion during debugging and analytics.

### Aggregation Formula

```python
early_avg = weighted_average(early_feedback_signals)
early_weight_total = sum(signal_weights)

early_influence = min(0.35, early_weight_total / 6.0)
blended_score = score * (1 - early_influence) + early_avg * early_influence
blended_weight = min(1.0, weight + min(0.25, early_weight_total / 12.0))
```

### Use Cases

1. **Reputation Bootstrapping:** New users get reputation from early signals
2. **Conflict Detection:** Low trust scores trigger LLM review
3. **AI Context:** Private notes enrich LLM reasoning for time suggestions

---

## 11. Memory Layer Flow

**Commands:** `/memory`, `/recall`, `/remember`, `/my_history`  
**Source:** `bot/commands/memory.py`

### Primary Flow: Bot-Initiated DM Collection (Post-Event)

This is the **primary** memory collection mechanism. It fires automatically when an event transitions to `completed`. The `/remember` command is a fallback for users who want to contribute outside this window.

```
Event → completed
    │
    └── [1–3 hours later] Bot DMs each confirmed participant
            │
            └── "Hey — how was [event]? Anything that stuck with you?
                 A word, a moment, a photo — whatever comes to mind."
                    │
                    ├── User replies via DM (text / emoji / photo)
                    │       └── Fragment stored in event_memories
                    │
                    └── [24-hour collection window closes]
                            │
                            └── LLM generates Memory Weave (plural voices)
                                    │
                                    └── Weave posted to group chat
                                            │
                                            └── Memory stored in event_memories
                                                    └── Detailed logs pruned
```

**Key Points:**
- Automatic, time-delayed DM to all confirmed participants
- Low-friction: users reply naturally, no command syntax needed
- Open-ended prompt — not structured questions, not ratings
- 24-hour collection window before weave generation
- The bot is an "absent friend" in this flow — receiving a story, not collecting data

### Secondary Flow: User-Initiated Contribution (`/remember`)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /remember  │────▶│  Parse      │────▶│  Store      │
│  <event_id> │     │  Fragment   │     │  Memory     │
│  <text>     │     │  + Hashtags │     │  Fragment   │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Usage:** Fallback for users who want to contribute outside the primary DM window, or add more after the weave is published.

### Event Memory Recall (`/memory`)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /memory    │────▶│  Retrieve   │────▶│  Format     │
│  <event_id> │     │  Memories   │     │  Weave      │
└─────────────┘     └─────────────┘     └─────────────┘
```

### Group Memory Browse (`/recall`)

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /recall    │────▶│  Query      │────▶│  Return     │
│  [filter]   │     │  Group      │     │  Group      │
│             │     │  Memories   │     │  Timeline   │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Privacy Note:** `/recall` shows **group-shared memories only**, not individual user histories.

### Personal History (`/my_history`) — Private DM Only

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /my_history│────▶│  Query      │────▶│  Return     │
│  (DM only)  │     │  User's     │     │  Personal   │
│             │     │  Events     │     │  Timeline   │
└─────────────┘     └─────────────┘     └─────────────┘
```

**Privacy Note:** Users can only view their **own** event history, and only via private DM. No user can query another user's participation history.

### Memory Structure

```json
{
  "memory_id": 1,
  "event_id": 123,
  "fragments": [
    {
      "text": "Best hiking trip ever!",
      "contributor_hash": "abc123",
      "tone_tag": "enthusiastic",
      "submitted_at": "2026-03-20T20:00:00"
    }
  ],
  "hashtags": ["hiking", "adventure", "friends"],
  "outcome_markers": ["follow-up event: 456", "photo album link"],
  "weave_text": "Some remember the climb as the hardest part. Others stayed at the summit longer than anyone expected. There was laughter about the wrong trail. For a few, the view changed something.",
  "lineage_event_ids": [100, 101],
  "tone_palette": ["enthusiastic", "grateful", "excited"]
}
```

### Memory Operations

#### Contribute Memory (`/remember`) — Secondary Flow
```bash
/remember 123 Amazing sunset at the peak! #hiking #memories
```

#### Recall Event Memory (`/memory`)
```bash
/memory 123
```

#### Browse Group Memories (`/recall`) — Group-Scoped
```bash
/recall                    # All group memories
/recall #hiking            # Filter by hashtag
/recall social             # Filter by event type
```

#### View Personal History (`/my_history`) — Private DM Only
```bash
/my_history                # In DM: view your own event timeline
/my_history @username      # ❌ NOT ALLOWED — privacy violation
```

### Weave Text Generation — Philosophy-Correct Output

**Design Principle:** The bot is a **weaver of fragments**, not a storyteller or summarizer.

**LLM Prompt Constraint:** Generate `weave_text` that holds multiple voices in co-existence without merging them into a single narrative. The prompt must explicitly instruct the LLM not to produce a unified description, summary, or resolution.

**Wrong (Summarizing Narrator):**
> "The group enjoyed a memorable hiking adventure."

**Correct (Fragment Weave):**
> "Some remember the climb as the hardest part. Others stayed at the summit longer than anyone expected. There was laughter about the wrong trail. For a few, the view changed something."

**Key Characteristics:**
- No conclusion, no resolution
- Plural perspectives held together without hierarchy
- No dominant narrative or authority voice
- Tones co-exist without collapse
- Contradictions are features, not bugs

### Tone Palette

Identified from memory fragments:
- `enthusiastic`, `grateful`, `excited`
- `reflective`, `humorous`, `nostalgic`

### Outcome Markers

Tracks event impact:
- Follow-up events
- Collaborations started
- Photo albums
- Shared documents

---

## 12. Event Lineage & Note Flow

**Commands:** `/event_note`  
**Source:** `bot/commands/event_note.py`, `bot/commands/event_creation.py`  
**Trigger:** Automatically offered at event creation if prior events of same type exist; manually triggered by organizer via `/event_note`

> This flow is how events build on each other over time. It is the mechanism that transforms a group from "people who coordinate" into "a group with shared history."

### 12.1 Lineage Prompt at Event Creation

When a new event is created with the same `event_type` as a prior completed event in the same group, the system offers a lineage connection at the end of the creation flow.

```
┌─────────────────────────┐
│  Event Created          │
│  (type: sports)         │
└─────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────┐
│  Check: prior completed event of same type?     │
│  Function: check_event_lineage(group_id, type)  │
└─────────────────────────────────────────────────┘
          │
          ├── No prior event → skip, creation complete
          │
          └── Prior event found
                    │
                    ▼
          ┌─────────────────────────────────────────┐
          │  Bot shows lineage prompt (inline):     │
          │                                         │
          │  "Last time you did this:               │
          │   [memory anchor from prior event]      │
          │   #hiking #adventure                    │
          │                                         │
          │  Reference it in this event?"           │
          │                                         │
          │  [Yes, link it]  [No, start fresh]      │
          └─────────────────────────────────────────┘
                    │
          ┌─────────┴─────────┐
          │ Yes               │ No
          ▼                   ▼
┌─────────────────┐   ┌─────────────────┐
│  Link events:   │   │  Creation       │
│  add prior      │   │  complete,      │
│  event_id to    │   │  no lineage     │
│  lineage_event_ │   │  set            │
│  ids on new     │   └─────────────────┘
│  event          │
│                 │
│  Surface prior  │
│  hashtags as    │
│  suggestions    │
└─────────────────┘
```

**What the lineage prompt shows:**
- Memory anchor: a short excerpt from the prior event's `weave_text` (1–2 sentences)
- The prior event's hashtags as quick-select options for the new event
- No detailed data, no participant list, no behavioral history

### 12.2 Organizer Event Note Flow (`/event_note`)

Organizers can enrich a live event with context updates at any time before it is locked. The bot posts these to the group, building narrative gravity around the event without replacing the human voice.

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  /event_note│────▶│  Check:     │────▶│  Is user    │
│  <event_id> │     │  Event      │     │  organizer? │
│  <text>     │     │  exists?    │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
                                              │
                          ┌───────────────────┼───────────────────┐
                          │ Yes               │ No                │
                          ▼                   ▼                   │
                  ┌─────────────┐     ┌─────────────┐             │
                  │  Is event   │     │  Error:     │             │
                  │  pre-lock?  │     │  Not        │             │
                  │             │     │  authorized │             │
                  └─────────────┘     └─────────────┘             │
                          │                                       │
          ┌───────────────┼───────────────┐                       │
          │ Yes           │ No (locked/   │                       │
          │               │  completed)   │                       │
          ▼               ▼               │                       │
  ┌─────────────┐ ┌─────────────┐         │                       │
  │  Store note │ │  Error:     │         │                       │
  │  in event   │ │  Too late   │         │                       │
  │  record     │ │  to add     │         │                       │
  └─────────────┘ └─────────────┘         │                       │
          │                               │                       │
          ▼                               │                       ▼
  ┌─────────────┐                         │
  │  Bot posts  │                         │
  │  to group:  │                         │
  │             │                         │
  │  "[event]   │                         │
  │  update:    │                         │
  │  [note]"    │                         │
  └─────────────┘
```

**Usage:**
```bash
/event_note 123 Court is confirmed booked. Bring your own rackets.
/event_note 123 Weather looks good. See you all at the south entrance.
/event_note 123 We're one person short — anyone able to bring a friend?
```

**Design Constraints:**
- Only the organizer can post event notes
- Notes are posted verbatim to the group (no LLM rewriting) — the human voice is preserved
- Notes are stored in the event record and visible in `/event_details`
- The system may prompt the organizer 24h before the event: "Anything to add before tomorrow?"

### 12.3 Lineage in Group Digest (Weekly)

If the group has accumulated memories, the bot posts a weekly digest (opt-in per group):

```
📅 This week in [group name]

Past events:
• [event 1] — "Some remember the climb..." #hiking
• [event 2] — "The debate ran long. Nobody minded." #work

Upcoming:
• [event 3] — Saturday, 10am — 4 confirmed
```

**Purpose:** Keeps the memory layer active between events, re-surfaces cultural references, and drives re-engagement.

**Function:** `MemoryService.build_weekly_digest(group_id)` — scheduled weekly task

---

## State Transition Diagram

```
                                    ┌─────────────────────────────────────────────┐
                                    │                                             │
                                    ▼                                             │
┌──────────┐   first join    ┌──────────────┐   first confirm   ┌──────────────┐  │
│ proposed │ ──────────────▶ │ interested   │ ────────────────▶ │ confirmed    │  │
└──────────┘                 └──────────────┘                   └──────────────┘  │
     │                            │                              │                │
     │ all cancel                 │ all cancel                   │ organizer lock │
     │                            │                              │                │
     │◀───────────────────────────┘                              ▼                │
     │                                              ┌──────────────┐              │
     │                                              │   locked     │──────────────┘
     │                                              └──────────────┘
     │                                                     │
     │                                                     │ event ends
     │                                                     ▼
     │                                              ┌──────────────┐
     │                                              │  completed   │──── triggers memory
     │                                              └──────────────┘     DM flow (Flow 11)
     │                                                     │
     │                                                     │ under threshold at collapse_at
     │                                                     ▼
     │                                              ┌──────────────┐
     │                                              │  cancelled   │
     │                                              └──────────────┘
     │                                                     ▲
     │                                                     │
     └─────────────────────────────────────────────────────┘
              organizer cancel (from any pre-locked state)
```

### State Descriptions

| State | Description | Allowed Actions |
|-------|-------------|-----------------|
| `proposed` | Event created, no participants | Join, Cancel, Modify, Add Note |
| `interested` | Participants joined, none confirmed | Join, Confirm, Cancel, Modify, Add Note |
| `confirmed` | At least one confirmed participant | Join, Confirm, Cancel, Lock, Modify, Add Note |
| `locked` | Event finalized, no changes | View only |
| `completed` | Event finished | Feedback, Memory |
| `cancelled` | Event cancelled | View only |

### Transition Rules

| From | To | Trigger | Actor |
|------|----|---------|-------|
| `proposed` | `interested` | First join | Any user |
| `interested` | `confirmed` | First confirm | Any user |
| `confirmed` | `locked` | Manual lock | Organizer/Admin |
| `locked` | `completed` | Time passed | System |
| `locked` | `cancelled` | Under threshold at `collapse_at` | System |
| `proposed`/`interested`/`confirmed` | `cancelled` | Organizer cancel | Organizer |
| Any pre-lock | `proposed` | All participants cancel | Any user |

---

## Key Services

### ParticipantService

**Location:** `bot/services/participant_service.py`

**Purpose:** Normalized participant tracking (replaces JSON `attendance_list`)

**Methods:**
- `join(event_id, telegram_user_id, source)` - Mark as joined
- `confirm(event_id, telegram_user_id, source)` - Mark as confirmed
- `cancel(event_id, telegram_user_id, source)` - Mark as cancelled
- `get_participant(event_id, telegram_user_id)` - Get participant record
- `get_counts(event_id)` - Get interested/confirmed/total counts
- `get_interested_count(event_id)` - Count joined participants
- `get_confirmed_count(event_id)` - Count confirmed participants
- `finalize_commitments(event_id)` - Lock in commitments

### EventLifecycleService

**Location:** `bot/services/event_lifecycle_service.py`

**Purpose:** State transitions with audit trail

**Methods:**
- `transition_with_lifecycle(event_id, target_state, actor_telegram_user_id, source, reason, expected_version)` - Transition with validation
- `_validate_transition(from_state, to_state)` - Check allowed transitions
- `_record_transition(event_id, from_state, to_state, actor_id, source, reason)` - Audit trail

### MaterializationService

**Location:** `bot/common/materialization.py`

**Purpose:** Posts group announcements at key state transitions and participation actions. Keeps cancellations private.

**Methods:**
- `announce(event_id, trigger, actor_id)` - Main entry point; fires after every state change
- `build_announcement(trigger, event, actor)` - Constructs message from template
- `should_announce(trigger, event)` - Guard against spam / duplicate posts
- `notify_organizer_private(event_id, message)` - DM-only path for cancellations

### MemoryService

**Location:** `bot/services/memory_service.py`

**Purpose:** Memory collection, weave generation, lineage, and digest

**Methods:**
- `trigger_collection_dms(event_id)` - DM all confirmed participants post-event
- `store_fragment(event_id, telegram_user_id, text, tone_tag)` - Store one memory fragment
- `generate_weave(event_id)` - LLM call to produce plural-voice weave text
- `post_weave_to_group(event_id)` - Post weave to group chat
- `get_memory(event_id)` - Retrieve memory record
- `get_group_memories(group_id, filter)` - Browse group memories by hashtag or type
- `link_lineage(event_id, prior_event_id)` - Connect events in lineage chain
- `check_event_lineage(group_id, event_type)` - Find prior events of same type
- `build_weekly_digest(group_id)` - Generate weekly summary for group

### LLMClient

**Location:** `ai/llm.py`

**Purpose:** OpenAI-compatible API wrapper

**Methods:**
- `resolve_conflicts(event, availability, reliability, notes)` - Conflict resolution
- `analyze_constraints(constraints)` - Constraint conflict detection
- `infer_constraint_from_text(text)` - Parse natural language constraint
- `infer_feedback_from_text(event_type, text)` - Parse feedback sentiment
- `infer_event_draft_patch(draft, message_text)` - Modify event draft
- `infer_event_draft_from_context(message_text, history)` - Create event from context
- `infer_early_feedback_from_text(text)` - Parse early feedback
- `infer_group_mention_action(text, history)` - Infer action from mention
- `generate_memory_weave(fragments, tone_palette)` - Generate plural-voice weave text

### AICoordinationEngine

**Location:** `ai/core.py`

**Purpose:** Hybrid AI engine (rules first, LLM fallback)

**Methods:**
- `suggest_event_time(session, event_id)` - 3-layer time suggestion
- `check_constraint_compatibility(session, event_id)` - Constraint conflict check
- `calculate_threshold_probability(session, event_id)` - Attendance probability

---

## Database Models

### Core Tables

| Table | Purpose | Key Fields |
|-------|---------|------------|
| `users` | User identities | `telegram_user_id`, `reputation`, `expertise_per_activity` |
| `groups` | Group contexts | `telegram_group_id`, `member_list` |
| `events` | Event lifecycle | `state`, `scheduled_time`, `threshold_attendance`, `version`, `notes` |
| `event_participants` | Normalized participation | `status`, `role`, `joined_at`, `confirmed_at` |
| `constraints` | Conditional participation | `type`, `target_user_id`, `confidence` |
| `feedback` | Post-event narrative feedback | `score_type`, `value`, `comment` |
| `early_feedback` | Pre-event signals | `signal_type`, `value`, `weight`, `source_type` |
| `event_memories` | Memory weave | `fragments`, `hashtags`, `outcome_markers`, `weave_text`, `lineage_event_ids` |
| `event_state_transitions` | Audit trail | `from_state`, `to_state`, `actor_telegram_user_id`, `reason` |
| `idempotency_keys` | Duplicate prevention | `command_type`, `status`, `response_hash` |

### Enum Types

#### ParticipantStatus
- `joined` - Expressed interest
- `confirmed` - Committed to attend
- `cancelled` - Withdrew attendance
- `no_show` - Did not attend

#### ParticipantRole
- `organizer` - Event creator
- `participant` - Regular attendee
- `observer` - Passive observer

#### MaterializationTrigger
- `first_join` - First participant joins
- `threshold_reached` - Event hits `min_participants`
- `confirmed` - A participant commits
- `high_reliability_join` - Reliable member joins
- `locked` - Event locked by organizer
- `near_collapse` - One participant away from collapse
- `collapsed` - Auto-cancelled below threshold
- `cancellation` - Participant drops (private to organizer)
- `note_added` - Organizer adds a note
- `24h_reminder` - Day-before reminder

---

## Command Reference

### Event Management

| Command | Description | Parameters |
|---------|-------------|------------|
| `/organize_event` | Create public event | Interactive flow |
| `/organize_event_flexible` | Create flexible-time event | Interactive flow |
| `/private_organize_event` | Create private event | Interactive flow |
| `/join <event_id>` | Join event | event_id (int) |
| `/confirm <event_id>` | Confirm attendance | event_id (int) |
| `/back <event_id>` | Revert confirmation | event_id (int) |
| `/cancel <event_id>` | Cancel attendance | event_id (int) |
| `/lock <event_id>` | Lock event (organizer only) | event_id (int) |
| `/modify_event <event_id>` | Modify event | event_id (int) |
| `/event_note <event_id> <text>` | Add organizer context update | event_id (int), text |
| `/status <event_id>` | View event status | event_id (int) |
| `/events` | List recent events | None |
| `/event_details <event_id>` | View event details + mutual dependence | event_id (int) |

### Constraints & Scheduling

| Command | Description | Parameters |
|---------|-------------|------------|
| `/constraints <event_id> view` | View constraints | event_id (int) |
| `/constraints <event_id> add ...` | Add constraint | event_id, target, type |
| `/constraints <event_id> availability ...` | Add availability | event_id, slots |
| `/constraints <event_id> remove <id>` | Remove constraint | event_id, constraint_id |
| `/suggest_time <event_id>` | Get AI time suggestion | event_id (int) |
| `/request_confirmations <event_id>` | Prompt confirmations | event_id (int) |

### Feedback & Reputation

| Command | Description | Parameters |
|---------|-------------|------------|
| `/feedback <event_id> [text]` | Submit narrative feedback | event_id, optional text |
| `/reputation` | View personal reliability trend | None |
| `/profile` | View user profile | None |

**Note on `/reputation`:** Output shows personal trend only — no leaderboard, no comparative scores, no ranking against others.

### Memory Layer

| Command | Description | Parameters | Privacy Scope |
|---------|-------------|-------------|---------------|
| `/memory <event_id>` | Recall event memory weave | event_id (int) | Group-visible |
| `/remember <event_id> <text>` | Contribute memory fragment | event_id, text | Group-visible |
| `/recall [filter]` | Browse group memories | Optional: hashtag, event type | Group-visible |
| `/my_history` | View personal event history | None | **Private DM only** |

**Privacy Notes:**
- `/recall` is **group-scoped** — shows shared memories, not individual histories
- `/my_history` is **private** — users see only their own history, via DM only
- No command allows querying another user's participation history (anti-surveillance)

### Utility

| Command | Description | Parameters |
|---------|-------------|------------|
| `/start` | Welcome message | Optional payload |
| `/help` | Show help | None |
| `/my_groups` | List user groups | None |
| `/check_deadlines` | Check event deadlines | None |

---

## Appendix: Callback Query Patterns

### Event Flow Callbacks

| Pattern | Handler | Action |
|---------|---------|--------|
| `event_join_{id}` | `event_flow.handle_event_flow` | Join event |
| `event_confirm_{id}` | `event_flow.handle_event_flow` | Confirm attendance |
| `event_back_{id}` | `event_flow.handle_event_flow` | Revert confirmation |
| `event_cancel_{id}` | `event_flow.handle_event_flow` | Cancel attendance |
| `event_lock_{id}` | `event_flow.handle_event_flow` | Lock event |
| `event_details_{id}` | `event_details.handle_callback` | View details + mutual dependence |
| `event_logs_{id}` | `event_details.handle_callback` | View logs |
| `event_constraints_{id}` | `event_details.handle_callback` | View constraints |
| `event_close_{id}` | `event_details.handle_callback` | Close event |

### Event Creation Callbacks

| Pattern | Handler | Action |
|---------|---------|--------|
| `event_type_{type}` | `organize_event.handle_callback` | Select type |
| `event_date_preset_{preset}` | `organize_event.handle_callback` | Select date |
| `event_time_window_{window}` | `organize_event.handle_callback` | Select time |
| `event_duration_{mins}` | `organize_event.handle_callback` | Select duration |
| `event_location_{type}` | `organize_event.handle_callback` | Select location |
| `event_budget_{level}` | `organize_event.handle_callback` | Select budget |
| `event_transport_{mode}` | `organize_event.handle_callback` | Select transport |
| `event_final_yes` | `organize_event.handle_callback` | Confirm creation |
| `event_final_edit` | `organize_event.handle_callback` | Modify draft |
| `event_cancel_no` | `organize_event.handle_callback` | Cancel creation |
| `event_lineage_yes_{id}` | `organize_event.handle_callback` | Link to prior event |
| `event_lineage_no` | `organize_event.handle_callback` | Skip lineage |

### Mention Callbacks

| Pattern | Handler | Action |
|---------|---------|--------|
| `mentionact_{id}_approve` | `mentions.handle_mention_callback` | Approve action |
| `mentionact_{id}_reject` | `mentions.handle_mention_callback` | Reject action |
| `modinput_{id}_write` | `mentions.handle_callback` | Write modification |
| `modinput_{id}_ai` | `mentions.handle_callback` | AI modification |
| `modinput_{id}_cancel` | `mentions.handle_callback` | Cancel modification |
| `modreq_{id}_approve` | `modify_event.handle_modify_request_callback` | Admin approve |
| `modreq_{id}_reject` | `modify_event.handle_modify_request_callback` | Admin reject |

### Feedback Callbacks

| Pattern | Handler | Action |
|---------|---------|--------|
| `feedback_{id}_submit` | `feedback.handle_feedback_callback` | Submit narrative feedback |

**Note:** Pattern renamed from `feedback_{id}_{score}` to `feedback_{id}_submit`. Numeric score inference happens internally via LLM parsing of free text, not through callback parameters.

### Constraint Callbacks

| Pattern | Handler | Action |
|---------|---------|--------|
| `constraint_nl_confirm` | `constraints.handle_callback` | Confirm constraint |
| `constraint_nl_cancel` | `constraints.handle_callback` | Cancel constraint |

### Memory Callbacks

| Pattern | Handler | Action |
|---------|---------|--------|
| `lineage_link_{prior_id}` | `memory.handle_lineage_callback` | Link new event to prior |
| `lineage_skip` | `memory.handle_lineage_callback` | Skip lineage prompt |

---

## Resolved Design Decisions

The PRD listed five open design decisions that required a product call before engineering resolved them. The following decisions have been made based on the current implementation direction. They are recorded here to prevent future drift.

| Decision | Resolution | Rationale |
|----------|------------|-----------|
| **Bot persona in Memory Weave** | Option C: Invisible curator — bot presents fragments with no first-person voice | Preserves plurality most strongly; avoids the bot becoming a narrator or authority. The weave speaks for itself. |
| **How visible should others' memory fragments be?** | Option B: Partially visible — fragments are shown in the group weave but contributor identity is anonymised by default (contributor_hash, not name) | Balances shared experience with individual comfort; avoids performance pressure while maintaining group resonance. |
| **Should the weave feel like "this represents us" or "this reflects parts of us"?** | "This reflects parts of us" (plural) | Consistent with the core principle: preserve plurality, avoid narrative centralization. |
| **Memory contribution opt-in structure** | DM flow (primary) + `/remember` command (secondary) | DM flow maximises authentic, low-pressure contribution; command provides a fallback. |
| **Should organizer role persist across events of same type?** | No — organizer is ephemeral per event | Prevents coordination authority from accumulating in specific members over time. The system surfaces "Who wants to organize the next one?" at the lineage prompt. |

---

## Changelog

| Version | Date | Changes |
|---------|------|---------|
| 2.0 | 2026-04-02 | Added Flow 3 (Materialization Announcements), Flow 12 (Event Lineage & Note), `MaterializationService`, `MemoryService`, `/event_note` command, lineage callbacks, `MaterializationTrigger` enum, Resolved Design Decisions section. Updated Flow 1 to include lineage check. Updated Flow 2 to show materialization trigger. Updated Flow 6 to link to memory flow. Updated state diagram to show memory trigger on completion. |
| 1.1 | 2026-04-02 | Review corrections: narrative-first feedback, `/recall` group-scoped, `/my_history` added, weave text plural voices, toxicity→civility, state transition fix, organizer cancel path, feedback callback renamed |
| 1.0 | 2026-04-02 | Initial document |

---

## Related Documents

- [PRD v2: Coordination Engine](../docs/PRD_v2.md)
- [Database Schema](../db/schema.sql)
- [API Reference](../docs/API_REFERENCE.md)
- [Deployment Guide](../docs/DEPLOYMENT.md)
