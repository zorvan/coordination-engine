# COORDINATION ENGINE

## PRODUCT V1

### Core Purpose

Transform informal “When are you free?” chaos into structured, transparent, socially reasonable group convergence.

Target group size: 2–20 people
Focus: small network coordination
No payments, no deposits, no penalties.

This is not a booking system.
It is a structured alignment system.

## CORE PRINCIPLE

Coordination must be:
- Legible
- Soft (not binary)
- Fair to majority
- Resistant to minority dominance
- Transparent in outcome reasoning

All ranking decisions follow a 3-Layer Decision Logic.

This is the heart of the product.

## SYSTEM OVERVIEW

Users create gatherings.
Members submit availability and optional soft constraints.
The system ranks time options using a transparent multi-step logic.
Organizer locks final selection.

No automation overrides humans.
System recommends. Organizer decides.

## DATA MODEL SUMMARY
### User
- id
- name
- avatar
- circles[]
- activity-scoped reliability score

Reputation is:
- Contextual (per activity)
- Visible only within shared gathering context
- Lightweight (attendance ratio only)

No global ranking.

### Gathering

- id
- title
- type (sport | travel | city | home)
- organizerId
- members[]
- invited[]
- availabilityMatrix
- constraints[]
- locationOptions[]
- deadline
- status (draft | voting | locked | cancelled)
- finalSelection

### Availability Input

Each user marks per slot:
- No
- Prefer Not
- Yes
- Strong Yes

Discrete inputs only.
No probability sliders.
No fuzzy membership functions.

## THE 3-LAYER DECISION LOGIC

This replaces simple weighted sums.

It runs automatically when ranking slots.

### Layer 1 — Viability Filter

Before ranking:
A time slot must meet a minimum participation threshold.

Default:
≥ 60–70% of members mark Yes or Strong Yes.

Slots below threshold:
- Not removed
- But visually faded
- Labeled “Below viability threshold”

Purpose:
Prevent weak turnout outcomes.

Narrative:
“This option does not meet minimum group availability.”

This protects group energy.

### Layer 2 — Regret Minimization (Primary Ranking)

For viable slots, compute dissatisfaction:

No = 2 regret points
Prefer Not = 1 regret point
Yes = 0
Strong Yes = 0

Total regret = sum of all regret points.

Rank slots ascending by total regret.

Primary decision driver:
Choose the slot with the lowest total friction.

Narrative:
“This option creates the least overall friction.”

This prevents:

- One enthusiastic minority dominating
- Majority mild dissatisfaction being ignored

It biases toward social stability.

### Layer 3 — Enthusiasm Tie-Breaker

If two slots have equal regret:

Rank by enthusiasm score:

Strong Yes = 2
Yes = 1

Highest enthusiasm wins.

Narrative:

“Tie broken by strongest collective enthusiasm.”

This preserves energy without sacrificing fairness.

## USER EXPERIENCE FLOW

### 1. Dashboard

Users see:
- Upcoming gatherings
- Invitations
- Past gatherings
- Create new gathering CTA

Each gathering shows:
- Member count
- Deadline
- Status indicator
- Viability indicator (if voting phase)

### 2. Create Gathering Flow

Step 1 – Basics
Title, type, description, deadline

Step 2 – Invite Members
Select friends or share invite link

Step 3 – Add Time Options
Add candidate date/time slots

Step 4 – Voting Opens
Members submit availability

### 3. Availability Matrix Screen

Grid format:

- Rows: Members
- Columns: Time slots

Color-coded inputs:
- No → red
- Prefer Not → amber
- Yes → light green
- Strong Yes → dark green

Below the grid:

#### Slot Ranking Panel
Each slot shows:
- Viability status
- Regret score
- Enthusiasm score
- Ranked position

Expandable:
“How this ranking works”

Transparency is mandatory.

### 4. Constraint Panel (Soft Social Logic)

Members may optionally add:

- “If X attends, I attend”
- “If X attends, I prefer not”
- Confidence slider (0–100)

Constraints affect:
Regret score slightly (weighted adjustment).

Constraints are soft.
No hard enforcement in V1.

Loops show warning.
No auto-resolution.

### 5. Decision Screen (Organizer View)

Organizer sees:

For each top slot:

✔ Viability %
⚖ Total friction score
🔥 Strong yes count
⚠ Constraint alerts

Clear structured explanation.

Organizer can:
- Lock Slot
- Extend Deadline
- Cancel

Once locked:
Status = locked
Members notified

No reversals.

## PROFILE SYSTEM

Profiles have 3 visibility layers:

### Public
- Name
- Avatar

### Circle Layer
- Participation rate %
- Response speed

### Activity Context Layer (inside gathering only)
- Reliability score for this activity
- Experience tag (Beginner / Casual / Skilled / Pro)

Reputation is descriptive, not punitive.

## NOTIFICATIONS

Triggers:
- Invitation received
- Deadline approaching
- Ranking updated significantly
- Slot locked
- Constraint affecting you added

In-app dropdown.
Real-time sync.

## EDGE CASE HANDLING

Must handle:
- 2-person gatherings
- Member leaving mid-vote
- All slots below viability
- Mutual exclusion loops
- Deadline reached without viable slot

If no viable slot:
Organizer prompted to:
- Lower threshold
- Add new options
- Cancel

System never auto-cancels.

## ENGINEERING STRUCTURE

Scoring module:

```
/lib/scoring/
   filterViable.ts
   calculateRegret.ts
   calculateEnthusiasm.ts
   rankSlots.ts
```

rankSlots():
1. Apply viability filter
2. Sort by regret
3. Tie-break by enthusiasm

Pure functions only.
Deterministic.
No hidden weight normalization.


## WHAT THIS DESIGN ACHIEVES

It avoids:

- Fuzzy logic opacity
- Complex optimization
- AI overreach
- Minority domination
- Majority frustration

It delivers:
- Structured fairness
- Soft coordination
- Socially explainable outcomes
- Transparent ranking logic

Stability at small-group scale

## WHAT IT DOES NOT TRY TO DO

It does not:
- Guarantee perfect fairness
- Enforce attendance
- Penalize flaking
- Optimize globally
- Allocate resources

It only structures convergence.

## PRODUCT IDENTITY

This is not a scheduling app.
It is a coordination infrastructure layer.
Its intelligence is social clarity, not algorithmic sophistication.
