# Questions to Answer Before Building the Mobile App

**Document Type:** Pre-Development Decision Framework
**Date:** 2026-04-04
**Applies To:** Android / iOS Mobile Application — Coordination Engine v3

---

## How to Use This Document

These questions are not a checklist. They are a dependency graph. The earlier questions shape the answer space of the later ones. Some questions have a right answer — one that follows from the product philosophy. Others are genuinely open. Both types are marked.

Read them in order. Answer them before a single line of mobile code is written.

---

## Part I — The Foundational Question

### 1. What is the mobile app *for*, specifically?

This is not the same question as "what features does it have." The bot lives inside Telegram — the group communication context. The mobile app will live somewhere else. Before deciding what it builds, decide what it *is*.

Three honest positions:

**Position A — The companion app.**
The group still lives in Telegram. The bot is still the group's coordination engine. The mobile app is a richer personal interface for the same system — better event viewing, smoother joining, personal history, memory browsing — without replacing the Telegram group dynamic.

**Position B — The standalone platform.**
The mobile app *is* the product. Telegram is legacy infrastructure you're migrating off. Groups form, events happen, and memory accumulates entirely inside the app.

**Position C — The split surface.**
Group coordination stays in Telegram (group chat is Telegram's home). Personal flows migrate to the app — memory contributions, attendance mirror, constraints, personal history — because they're inherently private and individual.

**Why this question determines everything:**
Position A requires read/write sync with the Telegram bot backend. Position B requires building a chat or group substrate from scratch. Position C requires a clean seam between group-surface and personal-surface in the existing codebase — and that seam currently doesn't exist.

The bot's database (`users`, `groups`, `events`, `event_participants`, `event_memories`) is the source of truth. Any mobile app touches the same data. The question is: what does it *own*, and what does it *observe*?

> **This question has a right answer given the philosophy.** The group field — the social gravity of people forming together — lives in Telegram. That is not incidental. The bot is designed to make the group visible *to itself*, in the place where the group communicates. Moving that surface to an app creates a different dynamic: individual screens instead of shared group chat. Position C is the most philosophically coherent choice. But you must decide, not assume.

---

## Part II — Identity and Authentication

### 2. How does a user's mobile identity connect to their Telegram identity?

The entire backend is keyed on `telegram_user_id` (BigInteger). That is the identity primitive for every user record, every event participant entry, every memory fragment, every constraint. There is no email, no password, no OAuth token.

You need to decide:

**Option A — Telegram login on mobile.**
Use Telegram's Login Widget or the `tgauth` protocol. The mobile app authenticates via Telegram and receives a `telegram_user_id`. Backend remains unchanged. User's history, events, and memory are immediately available.

**Option B — New identity system.**
The mobile app creates its own identity (email/phone). You build a mapping layer: `mobile_user_id → telegram_user_id`. This requires migration logic, dual-write, and resolving conflicts for users who exist in Telegram but haven't registered on mobile.

**Option C — Phone number bridge.**
Both Telegram and the mobile app use phone number as the identity anchor. You resolve identity server-side by matching phone numbers.

The correct question underneath this one: do you want mobile users and Telegram users to be the same people, or different populations? If the same — which is almost certainly true — Option A is the lowest-friction path and preserves the existing data model entirely.

### 3. What happens to a user who is in a Telegram group but has never opened the mobile app?

The bot already knows them. They have a `users` record. They may have participated in events, contributed memory fragments, set constraints. When they install the app, what do they see?

- Do they see their full history immediately?
- Do they need to "claim" their Telegram identity?
- Is there an onboarding flow or do they land directly in their group's context?

This is a UX question with a data architecture answer underneath it.

---

## Part III — The Group Surface Problem

### 4. Where does the group chat live in the mobile app?

The bot's core dynamic is: the group sees things together, in Telegram. When someone joins, the group sees it. When the threshold is reached, the group sees it. The materialization announcements exist precisely because shared visibility creates shared experience.

In a mobile app, the default interaction model is individual. You open the app. You see your events. You join. You confirm. The *group* doesn't see you doing it in real time the way they do in Telegram.

You must decide whether to:

**A — Accept the reduced social surface.** The app is for individual actions. The group coordination still flows through Telegram. The app is faster for personal use; the group moment still happens in the chat.

**B — Build a group feed inside the app.** A real-time feed per group showing formation events — who joined, threshold status, memory fragments posted. This is the materialization layer translated to mobile. This is a significant build.

**C — Send materialization events to both surfaces.** The bot posts to Telegram as before *and* sends a push notification to app users. The group moment happens in Telegram; app users get a mirror of it.

> **This question has a right answer given the philosophy.** Option C is correct for now. Option B is the long-term aspiration. Option A slowly kills the social layer by siloing actions into individual screens.

### 5. Does the group need to know that some members are acting from the app and some from Telegram?

The `source` field on `EventParticipant` currently tracks: `slash`, `callback`, `mention`, `dm`. Adding `mobile_app` is trivial. The question is: does it matter to users? Does it matter to the product?

---

## Part IV — Real-Time and Notifications

### 6. What is your push notification strategy, and does it respect the product's philosophy on pressure?

Push notifications are the most direct mechanism for creating urgency. They are also the fastest way to betray the product's philosophy. Every decision about when to notify is a decision about whether you're creating awareness or pressure.

Map every notification type to the materialization rules in WHY_VERSION_3.md before implementing:

- Someone joined your event → awareness (permitted)
- Threshold reached → awareness (permitted)
- Event is locked → awareness (permitted)
- "X more people needed before deadline" → potentially pressure (constrain the language carefully)
- Memory contribution request → receiving posture (this is the "absent friend" DM — it must feel like one, not like a system ping)
- Cancellation → **organizer only, private** (same rule as in the bot)

The questions to answer:
- Which triggers send push notifications?
- Does the user have per-event notification control, per-group control, or global control?
- Can notifications be turned off entirely without losing access to the app?
- Does a notification going unanswered create any follow-up pressure?

### 7. How does the mobile app stay in sync with the bot in real time?

The bot modifies state. Users on Telegram modify state. The mobile app needs to reflect current state without being the source of truth.

Options:
- **WebSocket connection** to a new API layer that wraps the existing bot backend
- **Polling** (simple but expensive and not real-time)
- **Server-sent events (SSE)** from a new mobile API endpoint
- **Firebase / APNs push + fetch on open** (notification triggers a state refresh, not a payload)

The bot is currently running on Python/PTB with PostgreSQL. It does not have a REST or GraphQL API. You will need to build one. The question is: does that API live inside the bot's codebase, or is it a separate service that reads the same database?

---

## Part V — Architecture and Evolution Speed

### 8. Does the mobile app call the bot backend directly, or does it go through a new API layer?

This is the most consequential technical question for evolution speed.

**Option A — Direct database access via a new API layer inside the bot codebase.**
Add a FastAPI (or similar) layer to the existing Python project. The bot and the API share models, services, and database connections. One codebase. Evolution is fast: when you add a feature to the bot, the API is one step away.

Risks: the bot codebase is PTB-specific and was not designed with an API in mind. Mixing async bot handling and HTTP serving in one process needs care.

**Option B — Separate API microservice that reads the same PostgreSQL database.**
A clean FastAPI service with its own process, sharing only the database. The bot and the API are separate deployments.

Risks: you have two codebases to maintain. Schema changes must be coordinated. Business logic lives in two places unless you extract it into a shared library.

**Option C — Event-driven: bot publishes domain events; mobile API consumes them.**
The bot publishes to a message queue (Redis, RabbitMQ, etc.) on every state change. The mobile API subscribes and maintains its own read model. CQRS-style.

Risks: significant infrastructure addition. Overkill for the current scale. But very clean for evolution.

**The right answer depends on your team size and deployment model.** For a small team, Option A is fastest. For a team that wants clean separation, Option B. For a team thinking about long-term scale, Option C eventually becomes necessary.

> **The critical constraint:** Whatever you choose, the single source of truth must remain the PostgreSQL database. The mobile app must never become a separate source of truth for event state. Divergence between the bot's view and the app's view is the failure mode to prevent above all others.

### 9. What is the mobile app's tech stack, and how does that affect shared logic?

The existing backend is Python (SQLAlchemy, asyncpg, PTB). The mobile app will be Swift/Kotlin native, or React Native, or Flutter.

The question is not which framework to use. The question is: where does business logic live?

In the bot, business logic is distributed across services (`EventLifecycleService`, `EventMemoryService`, `EventMaterializationService`). If the mobile app needs to make decisions — validation, state preconditions, materialization triggers — it either:

**A — Defers everything to the backend API.** The app is a thin client. All logic lives server-side. Evolution is fast because logic changes don't require app updates.

**B — Duplicates some logic on device.** Validation, UI-level state machines, etc. Faster perceived performance. But now you have two places where logic must stay in sync.

For a product that evolves as fast as this one — where the philosophy can change and business rules follow — Option A is the only defensible choice. Thick-client logic on mobile becomes a synchronization problem that compounds with every release.

### 10. How do you handle the bot evolving while the app exists?

The bot can ship a new feature — a new command, a new memory flow, a new materialization trigger — in a single Python deploy. The mobile app requires an App Store / Play Store release cycle, review periods, and user update lag.

You need answers to:

- What is the minimum API contract the app requires? What can the backend change without requiring an app update?
- How do you version the API? What is the deprecation policy?
- If a new bot feature has no mobile equivalent yet, how does the app degrade gracefully? (Does it show a "use Telegram for this" prompt? Does it hide the feature? Does it show a web view?)
- Do you build a feature flag system that gates mobile features independently of bot features?

### 11. How do you keep the mobile app from becoming a second product that diverges from the bot?

This is a governance question, not a technical one.

The bot's design decisions are made against a clearly documented philosophy (WHY_VERSION_3.md, PRD v3). Every feature proposal is evaluated against six questions. The mobile app will face pressure to add features that "make sense on mobile" — features that would never survive the six-question filter if applied to the bot.

Before building, decide:

- Does the mobile app have its own PRD, or does it extend the existing one?
- Are the same six evaluative questions applied to mobile feature proposals?
- Who has veto power when a mobile feature proposal conflicts with the bot's philosophy?
- Is the mobile app's product surface explicitly a subset of the bot's, or can the app introduce flows that don't exist in the bot?

---

## Part VI — The Memory Layer on Mobile

### 12. How does memory contribution feel different on mobile than in a Telegram DM?

In the bot, the "absent friend" DM is a Telegram message. The user responds in Telegram. It feels like messaging someone.

On mobile, memory contribution will be a push notification that opens the app, which shows a text input. That is a different interaction. It has a frame, a UI, a submit button. It risks feeling like a form.

The question: how do you design the memory contribution flow on mobile so it retains the receiving posture rather than the data-collection posture?

Concrete decisions to make:
- Does the notification open a minimal, full-screen text input with no chrome? Or does it open the app to a "Memory" tab with structure?
- Is there a character count? (There shouldn't be, but someone will suggest adding one.)
- Is there a submit button, or does the user just type and close? (The latter is richer but harder to implement cleanly.)
- If the user dismisses the notification, what happens? Does the app send a follow-up? (It shouldn't. The absent friend doesn't follow up twice.)

### 13. Where does the Fragment Mosaic live in the mobile app's information architecture?

On Telegram, the mosaic is posted to the group chat. Everyone sees it in the same place they see everything else. It appears, people read it, it becomes part of the group's shared text history.

On mobile, it needs a home. Options:
- Inside the event detail screen (makes sense, but it's buried)
- In a dedicated "Memories" tab (surfaced, but separated from coordination)
- As a notification that opens a full-screen mosaic view (highest impact, but most intrusive)
- In the group feed (if you build one per Question 4)

The decision should be made based on one test: does this placement make memory feel like a coordination driver (Question 7 from WHY_VERSION_3.md) or like an appendix to the event?

### 14. How does the lineage prompt work in mobile event creation?

In the bot, the lineage prompt surfaces in the group chat as a message with inline keyboard buttons before the creation flow continues. The group can see it.

On mobile, event creation happens on an individual screen. The lineage prompt would appear as part of an onboarding flow — probably a card or modal showing prior memory fragments, with "Link to this" and "Start fresh" options.

The question is whether this individual-screen lineage prompt captures the same dynamic as the group-visible one. When only you see the prior memory, does it still function as a coordination driver? Or does it need the group to see it too?

---

## Part VII — The Personal Flows

### 15. Which flows are genuinely better on mobile than on Telegram, and which are just "also possible" on mobile?

Be honest about this. The mobile app should prioritize flows where the mobile surface creates genuine additional value — not flows that work fine in Telegram but are being duplicated for completeness.

Candidates for "genuinely better on mobile":
- **Personal Attendance Mirror** — a rich, personal, visual history of your own participation. On Telegram this is a wall of text. On mobile it can be a timeline, a heatmap, a clear personal artifact.
- **Memory contribution** — typing a memory fragment on a phone keyboard, possibly with a photo, feels natural. Richer than a Telegram DM.
- **Constraint management** — setting conditional participation ("I join if @alice joins") is awkward in a Telegram DM flow. A mobile UI with an autocomplete for group members, toggle switches, and a clear summary is better.
- **Event browsing and discovery** — the `/events` command produces a list. A mobile screen with cards, visual state indicators, and one-tap joining is better.
- **Notifications** — mobile push is better than Telegram notifications for time-sensitive awareness (threshold reached, event locked, etc.)

Candidates for "works fine in Telegram, mobile adds little":
- **@bot mention flows** — natural language in a group chat. Mobile has no equivalent.
- **Group materialization** — the group moment happens in Telegram by design.
- **Weekly digest** — Telegram message is fine for this.

This inventory shapes what you build first and how much of the feature surface you need at v1.

### 16. What is the minimum viable mobile app that creates genuine value without creating a maintenance burden?

Given the constraint that the bot will continue to evolve rapidly, what is the smallest mobile app that:
1. Creates clear user value that Telegram cannot provide
2. Requires minimal API surface (fewer breaking change risks)
3. Does not introduce a competing product surface that diverges from the bot

A reasonable candidate for v1:
- Event list with one-tap join/confirm
- Event detail with participant visibility and mutual presence language
- Memory contribution (the "absent friend" flow, mobile-native)
- Personal Attendance Mirror (visual, private, personal)
- Push notifications for materialization events

Everything else — constraint management, time suggestion, event creation, the full memory layer — can come in v2 after the API contract is stable.

---

## Part VIII — What You Must Not Do

These are not questions. They are constraints derived directly from the product's design decisions. They apply to the mobile app with the same force they apply to the bot.

**Do not introduce scoring on mobile that doesn't exist in the bot.**
The reputation system was removed. If the mobile app adds a "reliability score," "participation rate," or any numeric behavioral summary beyond the attendance mirror, it re-introduces the system that was removed from the bot. This applies even if the framing is "gamification" or "engagement."

**Do not make push notifications the primary commitment mechanism.**
Push notification frequency is the fastest way to turn the mobile app into the pressure system the bot was redesigned to avoid. Notifications should inform, not engineer urgency. If you find yourself debating how often to remind users about upcoming events, the answer is: once, and only for events they have already joined.

**Do not allow the mobile app to read data the user hasn't consented to.**
The bot never surfaces one user's event history to another user. The mobile app must enforce the same constraint. No group admin view of individual member histories. No analytics screen that shows group-level behavioral patterns. The Personal Attendance Mirror is private to the user. It stays private on mobile too.

**Do not let the mobile event creation flow skip the meaning-formation step.**
The bot opens event creation with "What are you trying to bring together?" — not "Select event type." The mobile creation flow must begin the same way. A multi-step wizard that opens directly on a type picker is not v3.

**Do not let the app become a dashboard.**
Dashboards are for systems that measure. This system mediates. The home screen of the mobile app should show what is forming — current events, recent memories, live threshold states — not metrics, completion rates, or engagement summaries.

---

## The Six Questions, Applied to Mobile

Before any mobile feature is added to the backlog, apply these questions (from WHY_VERSION_3.md):

1. Does this require modeling user behavior to work? If yes, do not build it.
2. Does this create asymmetric visibility — where the system knows something about a user that the user does not know? If yes, do not build it.
3. Does this introduce pressure into what should be awareness? If yes, redesign before building.
4. Does this treat memory as an artifact or as a driver? If artifact, reconsider the placement.
5. Does this belong to Paradigm A (relational emergence) or Paradigm B (computational governance)? If B, do not build it.
6. Would the user be surprised to learn this exists? If yes, it should not exist.

These are not filters that make building harder. They are the definition of what this product is, on any surface.
