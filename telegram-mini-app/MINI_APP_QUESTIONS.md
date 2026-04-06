# Questions to Answer Before Building the Telegram Mini App

**Document Type:** Pre-Build Decision Framework
**Applies To:** Telegram Mini App (Android / iOS) for the Coordination Engine
**Date:** 2026-04-04

---

## How to Use This Document

These questions are not a checklist. They are a sequence. Each category must be resolved before the next can be designed. Answering them out of order produces a Mini App that is either philosophically misaligned with the bot it extends, or technically incapable of evolving with it.

Answer them in writing. The act of writing forces precision. Vague verbal answers will produce vague architecture.

---

## Category 1 — Identity and Relationship to the Bot

These questions define what the Mini App *is* in relation to the existing system. Everything else depends on them.

**1.1 — Is the Mini App a richer surface for the same system, or a second product?**

The bot already has a functioning DM menu system (`bot/handlers/menus.py`, `bot/common/menus.py`) with paginated event lists, context-aware action buttons, and inline navigation. The Mini App could be a visual upgrade to that same experience — or it could be a genuinely different product that happens to share a backend.

If it is a richer surface: every design decision should ask "what does the chat interface make awkward that the Mini App should make fluid?" If it is a second product: it needs its own product vision and its own KPI, and the risk of philosophical drift doubles.

**1.2 — What is the Mini App's primary trigger? How does a user arrive at it?**

Telegram Mini Apps open from a button in a bot message, from a chat attachment, or from a direct link. The entry point shapes everything about the experience. Does the Mini App open when a user receives an event invitation? When they type `/events`? When they tap a button in the DM menu? The entry point is the first UX decision and it is architectural, not cosmetic.

**1.3 — Does the Mini App replace the bot's DM interaction, extend it, or run alongside it?**

Currently the bot handles: meaning-formation in group chat, constraint input via DM, memory collection via DM, menu navigation via inline keyboards. If the Mini App handles some of these, the bot must stop handling them for those users — or the system has two competing interaction surfaces for the same flow, which produces confusion and maintenance overhead.

Which flows stay in chat? Which move to the Mini App? This must be a table, not a general answer.

**1.4 — How do you handle users who never open the Mini App?**

The bot works today without a Mini App. If you build the Mini App and some group members use it while others don't, do both users see a consistent shared reality of the event? Or does the Mini App create a split experience where some users see rich UI and others receive text messages that reference states they cannot access?

This is not a UX question. It is a product philosophy question. The coordination system only works if all participants share the same event reality.

---

## Category 2 — Philosophy Alignment

The bot was rebuilt around six mediation levers: timing, framing, visibility, language, sequence, memory surfacing. The Mini App must be evaluated against each one — because a rich UI can violate all of them simultaneously without the designer noticing.

**2.1 — How does the Mini App hold meaning-formation mode?**

The bot's `meaning_formation.py` resists collapsing ambiguity into structure. Its opening prompt is "What are you trying to bring together?" not a form. A Mini App's natural gravity is toward forms — pickers, dropdowns, step wizards. How does the Mini App's event creation flow preserve the open-ended, intent-first posture of the bot's meaning-formation mode? What does it look like to hold ambiguity in a mobile UI?

If your answer is "it will show a text field first," that is fine — but it must be a deliberate design decision, not a default.

**2.2 — Where does the Fragment Mosaic live in the Mini App?**

The Fragment Mosaic is the system's most philosophically precise artifact: participant words, arranged without synthesis, no interpretation added. In the bot, this is a text message. In the Mini App, it could be rendered as cards, a scroll, a visual collage — all of which introduce visual hierarchy that the bot intentionally avoids. What is the correct visual form for something that must preserve plurality and resist visual authority?

This is not a design question to answer after engineering starts. It is a design constraint that must be set before any memory UI is built.

**2.3 — Does the Mini App make any information visible that the bot deliberately hides?**

The bot hides: individual cancellation from the group, any form of comparative ranking, the system's reasoning about participants. A Mini App dashboard tempts designers toward completeness — showing everything in one place. You must explicitly decide which information the Mini App will not show, and that list must be as deliberate as what it does show.

**2.4 — How does the Mini App handle the "near minimum" moment?**

The bot's materialization layer was carefully rewritten to inform without engineering guilt. The near-minimum message says: "Heads up — this event needs N more to happen." In the Mini App, this same state might be shown as a progress bar, a warning badge, a color change, a countdown. Each of those visual choices carries emotional weight. Which of them stay on the right side of the awareness/pressure line?

You must define the visual grammar for fragility before the first screen is designed.

---

## Category 3 — Data Architecture and API Design

This is where Mini Apps typically create long-term problems. The bot communicates directly with the database through SQLAlchemy async sessions. The Mini App needs an API. That API is a new contract — and every time the bot evolves, the API must evolve too.

**3.1 — Do you build a new REST/GraphQL API, or expose the bot's internal services directly?**

The bot's service layer (`ParticipantService`, `EventLifecycleService`, `EventMemoryService`, `EventMaterializationService`) is the correct abstraction point. The Mini App should call these services through an API — not re-implement coordination logic in the frontend. But the services are currently called by Python bot handlers, not by HTTP endpoints. Who builds and maintains the API layer? What is its technology? What is its versioning strategy?

If you do not answer this before engineering starts, the Mini App will either bypass the service layer (duplicating business logic) or the API will be built ad-hoc alongside the Mini App and become a maintenance problem the moment the bot's services change.

**3.2 — How do bot state transitions remain the single source of truth?**

The `EventStateTransitionService` is the single write path for event state changes. If the Mini App can trigger state transitions directly via API, you need to ensure that:

- The Mini App's transitions go through the same service (not directly to the database)
- The same optimistic concurrency control (`version` field) applies
- The same idempotency keys prevent duplicate transitions
- The same materialization announcements fire in the group chat when the Mini App triggers a state change

Concretely: if a user taps "Confirm" in the Mini App, the group chat must still receive the materialization announcement. The bot's materialization layer is triggered by the service, not by the command handler — so this is achievable. But it must be verified as a requirement before API design begins.

**3.3 — What is the authentication model?**

Telegram Mini Apps receive `initData` from the Telegram client on launch, which includes the user's Telegram ID and a hash that can be validated against the bot token. This is the correct authentication mechanism — the Mini App inherits the user's Telegram identity without passwords or separate accounts. But:

- Is `initData` validated server-side on every API call, or only on session establishment?
- Does the API issue its own session tokens after validating `initData`?
- What happens when `initData` expires (Telegram signs it with a time component)?
- How does the API enforce that a user can only access events from groups they belong to — using the same `check_group_membership` logic from `bot/common/rbac.py`?

**3.4 — How does the Mini App receive real-time updates?**

The bot delivers materialization announcements to the group the moment a state transition occurs. The Mini App displays event state. If a user has the Mini App open and another participant confirms in the group chat, the Mini App's state view will be stale until the user refreshes. Options:

- Polling (simple, stale, works for low-frequency events)
- WebSocket or Server-Sent Events (real-time, more complex)
- Telegram's own push via the bot message

Which approach fits the event frequency and the team's infrastructure capacity? There is no wrong answer, but there is no neutral answer — each choice has implications for how "live" the Mini App feels and how much it resembles a real-time coordination surface.

**3.5 — How do you prevent the Mini App API from becoming a second codebase to maintain?**

Every time a new field is added to the `events` table, every time a new command is added to the bot, every time the memory service evolves — the API may need to change. This is the core maintenance risk of a Mini App: it creates a surface that must be kept in sync with the bot's evolving internals. The answer is not "we'll be careful." The answer is an explicit strategy: a typed API contract, a shared schema, contract testing, or a monorepo structure that makes the relationship explicit and visible.

---

## Category 4 — Feature Parity and the Evolution Problem

**4.1 — Which bot features must the Mini App support at launch, and which can wait?**

A full parity list includes: event creation (with meaning-formation mode), join/confirm/cancel/lock, event detail with mutual presence view, constraint management (DM-only — how does this translate?), memory contribution, Fragment Mosaic display, personal attendance mirror, recall/memory browsing, event lineage at creation. You cannot build all of this at once. The priority decision determines what users encounter first and what shapes their mental model of the Mini App.

**4.2 — How do you keep the Mini App in sync as the bot adds new features?**

The bot is under active development. New commands, new flows, new memory behaviors will be added. Each addition that touches the service layer or database schema is a potential breaking change for the Mini App's API. The answer to this question is a process, not a technical choice: who is responsible for updating the API when the bot evolves? Is there a contract test suite? Is there a shared type definition layer?

Without an explicit answer here, the Mini App will fall behind the bot within months and require a costly catch-up effort.

**4.3 — How do you handle flows that are inherently chat-native?**

Some of the bot's most important flows are designed for the chat medium specifically:

- **Memory collection DM**: the bot DMs participants with an open-ended prompt after an event. This is a conversation, not a form. In the Mini App, does this become a push notification that opens a text input? Or does it remain in the bot DM, and the Mini App only shows the resulting mosaic?
- **Meaning-formation**: the multi-turn intent-clarification conversation that resists collapsing into a form. Can this be reproduced in a Mini App flow without becoming a wizard? Should it be?
- **Group materialization announcements**: these happen in the group chat. The Mini App cannot post to the group chat on the user's behalf. These announcements must remain bot-driven regardless of whether the Mini App is involved.

For each of these, you must decide: does the Mini App replicate the flow, or does it surface the output of a flow that remains in the bot?

**4.4 — What does the Mini App add that the bot cannot do?**

This is the most important question in this category. If the Mini App is only a visual wrapper around existing bot functionality, it will be harder to maintain and no more valuable to users. The Mini App's justification must be a list of things that are genuinely better in a visual, persistent interface than in a chat: visualizing event formation progress, browsing the group's memory archive, seeing the full participant list at a glance, editing event details with a real form rather than a command string. What is that list, specifically? If the list is short, the scope of the Mini App should be narrow. If the list is long, it must be sequenced.

---

## Category 5 — User Experience Specifics

**5.1 — What is the first screen a user sees, and what can they do from it?**

This is not a wireframe question yet. It is a product question: what is the Mini App's entry-state for a user who has events in their group, and for a user who has none? What is the correct empty state? What is the correct primary action? Every Mini App has a home screen that encodes the product's theory of what matters most. What is yours?

**5.2 — How does the Mini App communicate event state to users who are not yet participants?**

A non-participant sees an event that is "forming" — some people have joined, threshold not yet reached. The bot communicates this through materialization messages in the group chat. The Mini App must communicate it through UI. What does "forming" look like visually? What does "close to threshold" look like? What does "locked" look like? These visual states must be defined with the same care as the bot's message templates — because they carry the same philosophical weight.

**5.3 — How does constraint input work in the Mini App?**

In the bot, constraints (`/constraints`) are entered exclusively via DM — private from the group. The Mini App is a personal interface (it opens for one user), so it is inherently private in that sense. But the Mini App may also share state with the group's event. How is the privacy of constraint input preserved in the Mini App's UX? Does the user understand they are entering something that is visible to the system but not to other group members?

**5.4 — What is the Mini App's offline behavior?**

Mobile apps lose connectivity. When a user taps "Confirm" while offline, what happens? Does the Mini App queue the action and retry? Does it fail with an error? Does it show stale state without indicating it is stale? The answer depends on what is technically feasible, but it must be defined — because users will encounter it, and an undefined offline behavior becomes a bug.

**5.5 — What is the notification strategy?**

The bot sends: join announcements in group chat, materialization messages, memory collection DMs, weekly digest. If the Mini App is installed, should it also send push notifications for some of these? If it does: which ones, and does that mean the bot stops sending those messages in chat? Duplicate notifications for the same event destroy the experience. If it does not: what is the value of having the Mini App installed if the primary update channel is still the bot's group chat messages?

---

## Category 6 — Technical Platform Constraints

**6.1 — Have you read the Telegram Mini App documentation in full, including its limitations?**

Telegram Mini Apps run as WebViews inside the Telegram client. They have access to `initData` for authentication, `HapticFeedback`, `MainButton`, `BackButton`, and `ThemeParams` for system integration. They cannot: post messages to the group chat (the bot must still do that), access the Telegram contact list without user permission, or run background processes. The Mini App's feature list must be filtered through these constraints before any promise is made.

**6.2 — What is the technology stack for the Mini App frontend?**

The options are: React (recommended for most teams, good ecosystem for Telegram Mini Apps), Vue, or a lightweight vanilla JS approach. The choice should be based on: team familiarity, available Telegram SDK integrations, and the rendering requirements of the Fragment Mosaic and event formation visualizations. The stack decision also determines the build pipeline, deployment process, and how changes are released — which is directly relevant to keeping the Mini App in sync with bot evolution.

**6.3 — Where is the Mini App hosted, and how does deployment work?**

Telegram Mini Apps must be served over HTTPS from a publicly accessible URL. They are registered with the bot via `@BotFather`. The hosting infrastructure must be decided before development starts. If the mini app is served from the same server as the bot's webhook: deployments are coupled. If it is served separately: there are two independent deployment pipelines, which is cleaner but requires coordination when both change together.

**6.4 — How does `initData` validation work in your backend?**

The Telegram Mini App's `initData` is a HMAC-SHA256-signed payload that must be validated on the server using the bot token. This validation must happen on every authenticated API call, or the API is unauthenticated. The validation logic is documented by Telegram and is straightforward — but it must be explicitly implemented, not assumed. Specifically: the bot token used for validation must be the same bot token that the Mini App was registered under.

---

## Category 7 — The Minimum Viable Mini App

Before any design or engineering begins, answer these three questions together. Their combined answer is the scope of the first version.

**7.1 — What is the one flow that is most painful in the bot and most natural in a Mini App?**

Pick one. The first version of the Mini App should solve one problem better than the bot does, and solve it completely. Not adequately — completely.

**7.2 — What is the smallest surface that can prove the Mini App is worth maintaining alongside the bot?**

The Mini App creates ongoing maintenance overhead. The first version must demonstrate — to the team, not just to users — that the value justifies the overhead. What is the smallest version that can do that?

**7.3 — What would make you decide not to build the Mini App at all?**

This question is not pessimistic. It is protective. Knowing the conditions under which the Mini App should not be built forces clarity about why it should be. If the answer is "nothing would stop us," that is a warning sign. If the answer is "if the API maintenance cost exceeds a given threshold" or "if the Mini App cannot preserve the Fragment Mosaic's plurality in visual form," those are real constraints that should shape the first version.

---

## Summary: The Decision Order

These questions must be answered in this order. Each category depends on the one before it.

1. **Identity** — What is the Mini App's relationship to the bot?
2. **Philosophy** — Which design constraints carry forward?
3. **Data architecture** — Where is the API boundary, and who owns it?
4. **Feature scope** — What is built first, and how does the rest follow?
5. **UX specifics** — What do the key states look and feel like?
6. **Platform constraints** — What does Telegram actually allow?
7. **Minimum viable scope** — What proves this is worth building?

Do not start design until Category 1 and 2 are resolved.
Do not start engineering until Category 3 is resolved.
Do not start building features until Category 4 is resolved.
