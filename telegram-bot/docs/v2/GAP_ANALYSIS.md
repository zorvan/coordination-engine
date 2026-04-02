# Gap Analysis — PRD v2 vs Implementation

**Date:** 2026-04-02  
**Document Purpose:** Compare PRD v2 and USER_FLOWS.md specifications against current implementation to identify gaps and simplifications that can be upgraded.

---

## Executive Summary

**Overall Implementation Status:** ~85% of PRD v2 specifications implemented.

**Fully Implemented:**
- ✅ Three-layer architecture (Coordination, Materialization, Memory)
- ✅ Service-oriented design with single write paths
- ✅ RBAC and threshold enforcement
- ✅ Mutual dependence visibility
- ✅ Callback replay protection
- ✅ Rate limiting
- ✅ Webhook support with worker queue
- ✅ Weekly digest

**Implemented Simply (Can Be Upgraded):**
- ⚠️ Memory weave (template-based, not LLM-enhanced)
- ⚠️ Reputation system (data collection only, not operational)
- ⚠️ Materialization announcements (basic, missing reliability signals)
- ⚠️ Event lineage (manual, not automatic)
- ⚠️ Memory collection (command-based, not automatic DM)

**Not Implemented (Gaps):**
- ❌ Log pruning (90-day data minimization)
- ❌ Automatic memory collection DM flow
- ❌ Reputation operational effects
- ❌ Nudges with recognition framing
- ❌ Organizer role rotation
- ❌ Waitlist support

---

## Detailed Analysis by Layer

### Layer 1: Coordination

| Feature | PRD Spec | Implementation | Gap | Upgrade Priority |
|---------|----------|----------------|-----|------------------|
| Event state machine | `proposed → interested → confirmed → locked → completed` | ✅ Fully implemented | None | - |
| `EventStateTransitionService` | Single write path with logging | ✅ Fully implemented | None | - |
| `EventParticipant` table | Normalized schema | ✅ Fully implemented | None | - |
| Optimistic concurrency | `version` field on events | ✅ Fully implemented | None | - |
| `min_participants` enforcement | Block lock below threshold | ✅ Fully implemented | None | - |
| `collapse_at` auto-cancel | Auto-cancel underthreshold events | ❌ Not implemented | **HIGH** | P2 |
| `lock_deadline` | Cutoff for attendance changes | ⚠️ Field exists, not enforced | **MEDIUM** | P3 |
| Waitlist support | Automatic waitlist on cancellation | ❌ Not implemented | **MEDIUM** | P3 |

**Upgrade Recommendations:**

1. **Implement `collapse_at` auto-cancel** (P2)
   - Add scheduled job to check expired events
   - Auto-cancel and notify organizer
   - File: `bot/common/scheduler.py` (NEW)

2. **Enforce `lock_deadline`** (P3)
   - Block lock after deadline passed
   - Show deadline in event details
   - File: `bot/commands/lock.py`

3. **Add waitlist support** (P3)
   - New table: `event_waitlist`
   - Auto-promote on cancellation
   - File: `bot/services/waitlist_service.py` (NEW)

---

### Layer 2: Materialization

| Feature | PRD Spec | Implementation | Gap | Upgrade Priority |
|---------|----------|----------------|-----|------------------|
| First join announcement | "[Name] just joined. We need N more." | ✅ Implemented | None | - |
| Threshold reached | "We have enough. It's happening!" | ✅ Implemented | None | - |
| Event locked | "[Event] locked. See you [time]. [participants]" | ✅ Implemented | None | - |
| Event completed | "[Event] is complete! Thanks to all N." | ✅ Implemented | None | - |
| Cancellation (private) | DM to organizer only | ❌ Not implemented | **HIGH** | P2 |
| Near collapse | "Heads up: needs N more. Deadline: [time]" | ⚠️ Partial (status only) | **MEDIUM** | P3 |
| High-reliability join | Subtle signal amplification | ❌ Not implemented | **MEDIUM** | Requires reputation |
| 24h before event | "[Event] is tomorrow. N confirmed." | ❌ Not implemented | **LOW** | P4 |
| Organizer note prompts | Bot prompts 24h before event | ❌ Not implemented | **LOW** | P4 |

**Upgrade Recommendations:**

1. **Implement cancellation DM to organizer** (P2)
   - Trigger on participant cancel
   - Include waitlist status if available
   - File: `bot/services/event_materialization_service.py`

2. **Add near-collapse group announcements** (P3)
   - Post when confirmed_count == min_participants - 1
   - Include deadline
   - File: `bot/services/event_materialization_service.py`

3. **Implement 24h reminder** (P4)
   - Scheduled job for upcoming events
   - Post to group chat
   - File: `bot/common/scheduler.py` (NEW)

---

### Layer 3: Memory

| Feature | PRD Spec | Implementation | Gap | Upgrade Priority |
|---------|----------|----------------|-----|------------------|
| Memory collection DM | Auto DM 1-3h post-event | ❌ Not implemented | **HIGH** | P2 |
| Open-ended prompts | "How was it? Anything worth remembering?" | ⚠️ Manual `/feedback` | **MEDIUM** | P2 |
| Memory weave (LLM) | LLM generates plural-voice weave | ⚠️ Template-based | **MEDIUM** | P3 |
| Tone palette | Coexisting tones identified | ⚠️ Basic implementation | **LOW** | P4 |
| Event lineage | Auto-suggest at event creation | ❌ Not implemented | **MEDIUM** | P3 |
| Hashtag suggestions | From prior similar events | ❌ Not implemented | **LOW** | P4 |
| `/my_history` (DM only) | Personal event timeline | ❌ Not implemented | **LOW** | P4 |
| Log pruning (90d) | Delete detailed logs after 90 days | ❌ Not implemented | **HIGH** (GDPR) | P2 |

**Upgrade Recommendations:**

1. **Implement automatic memory collection DM** (P2)
   - Trigger on event completion
   - Wait 1-3 hours, then DM all confirmed participants
   - 24-hour collection window
   - File: `bot/services/event_memory_service.py`

2. **Upgrade memory weave to LLM-based** (P3)
   - Use LLM to generate plural-voice weave
   - Preserve contradictions, no unified narrative
   - File: `bot/services/event_memory_service.py`

3. **Implement event lineage** (P3)
   - Check for prior events of same type at creation
   - Show lineage prompt with memory anchor
   - File: `bot/commands/event_creation.py`

4. **Implement log pruning** (P2 - GDPR)
   - Scheduled job to delete logs older than 90 days
   - Keep `event_memories` and reputation aggregates
   - File: `bot/common/scheduler.py` (NEW)

---

### Cross-Cutting Features

| Feature | PRD Spec | Implementation | Gap | Upgrade Priority |
|---------|----------|----------------|-----|------------------|
| Reputation operational | Affects priority, reconfirmation windows | ❌ Data collection only | **HIGH** | P2 |
| `/reputation` command | Personal trend, not leaderboard | ⚠️ Stub implementation | **MEDIUM** | P3 |
| Nudges (recognition framing) | "We value you showing up" | ❌ Not implemented | **MEDIUM** | P3 |
| Organizer role rotation | Temporary role, not permanent | ❌ Not implemented | **LOW** | P4 |
| Admin actions by confirmed participants | Emergency modify/cancel | ⚠️ Partial (RBAC exists) | **LOW** | P4 |
| Anti-bias checks for early feedback | Prevent reputation manipulation | ❌ Not implemented | **MEDIUM** | P3 |

**Upgrade Recommendations:**

1. **Wire reputation into operational logic** (P2)
   - Priority on oversubscribed events
   - Earlier reconfirmation windows for low-reliability users
   - File: `bot/services/participant_service.py`

2. **Implement `/reputation` command** (P3)
   - Show personal trend over time
   - No leaderboard, no score comparison
   - File: `bot/commands/reputation.py`

3. **Rewrite nudges with recognition framing** (P3)
   - Remove "low reliability" language
   - Frame as "we want to make sure you can make it"
   - File: `bot/common/nudges.py`

---

## USER_FLOWS.md Analysis

### Flows Fully Implemented

| Flow | Status | Notes |
|------|--------|-------|
| Event Creation (`/organize_event`) | ✅ Complete | All stages implemented |
| Event Participation (join/confirm/cancel) | ✅ Complete | State-aware menus |
| Constraint Management | ✅ Complete | DM flow working |
| Mention-Driven AI | ✅ Complete | Natural language inference |
| Time Suggestion | ✅ Complete | AI-assisted |
| Weekly Digest | ✅ Complete | Manual trigger `/digest` |

### Flows Partially Implemented

| Flow | Status | Missing Components | Upgrade Priority |
|------|--------|-------------------|------------------|
| Memory Collection | ⚠️ Partial | Auto DM flow, LLM weave | P2 |
| Event Lineage | ⚠️ Partial | Auto-prompt at creation | P3 |
| Feedback | ⚠️ Partial | Open-ended prompts (not ratings) | P3 |
| Materialization | ⚠️ Partial | Cancellation DM, 24h reminder | P2 |

### Flows Not Implemented

| Flow | Status | Description | Priority |
|------|--------|-------------|----------|
| `/my_history` | ❌ Not implemented | Personal event timeline (DM only) | P4 |
| Automatic event completion | ❌ Not implemented | Auto-complete after event time passes | P3 |
| Waitlist flow | ❌ Not implemented | Waitlist on full events | P3 |

---

## Simplifications That Can Be Upgraded

### 1. Memory Weave (Template → LLM)

**Current:** Template-based weave generation
```python
weave_parts = [f"📿 <b>How people remember: {event_anchor}</b>"]
for fragment in fragments:
    weave_parts.append(f"• \"{fragment['text']}\"")
```

**Upgrade Path:** LLM-enhanced weave
```python
prompt = f"""
Generate a memory weave from these fragments.
DO NOT summarize or unify. Preserve plural voices.
Hold contradictions without resolution.

Fragments:
{fragments_json}

Return weave text only.
"""
weave_text = await llm.generate(prompt)
```

**File:** `bot/services/event_memory_service.py`  
**Priority:** P3  
**Effort:** Medium

---

### 2. Reputation (Data Collection → Operational)

**Current:** Reputation data collected but not used
```python
# Data exists in database
user_reputation = 3.8  # But has no effect
```

**Upgrade Path:** Operational reputation
```python
# Priority on oversubscribed events
if event.is_oversubscribed:
    if user.reliability_score < 3.0:
        return False, "Waitlist only for this event"

# Earlier reconfirmation for low-reliability users
if user.reliability_score < 3.0:
    reconfirmation_window = 7  # days (vs 3 for others)
```

**File:** `bot/services/participant_service.py`  
**Priority:** P2  
**Effort:** Medium

---

### 3. Materialization (Basic → Full)

**Current:** Basic announcements only
```python
# Only these triggers implemented:
- first_join
- threshold_reached
- event_locked
- event_completed
```

**Upgrade Path:** Full materialization
```python
# Add these triggers:
- cancellation_private (DM to organizer)
- near_collapse (group announcement)
- high_reliability_join (subtle amplification)
- 24h_reminder (group announcement)
```

**File:** `bot/services/event_materialization_service.py`  
**Priority:** P2  
**Effort:** Medium

---

### 4. Event Lineage (Manual → Automatic)

**Current:** No lineage prompts
```python
# Events created independently
```

**Upgrade Path:** Automatic lineage
```python
# At event creation:
prior_events = await get_prior_events(group_id, event_type)
if prior_events:
    memory_anchor = await get_memory_anchor(prior_events[0])
    await show_lineage_prompt(memory_anchor)
```

**File:** `bot/commands/event_creation.py`  
**Priority:** P3  
**Effort:** Medium

---

### 5. Memory Collection (Manual → Automatic)

**Current:** Manual `/feedback` command
```python
# User must remember to use /feedback
```

**Upgrade Path:** Automatic DM flow
```python
# On event completion:
await asyncio.sleep(2 * 3600)  # Wait 2 hours
for participant in confirmed_participants:
    await bot.send_message(
        chat_id=participant.telegram_user_id,
        text="Hey — how was it? Anything worth remembering?"
    )
```

**File:** `bot/services/event_memory_service.py`  
**Priority:** P2  
**Effort:** Medium

---

## Implementation Priority Matrix

| Priority | Feature | Effort | Impact | GDPR/Compliance |
|----------|---------|--------|--------|-----------------|
| **P1** | Log pruning (90d) | Medium | High | ✅ Yes |
| **P2** | Automatic memory collection DM | Medium | High | No |
| **P2** | Cancellation DM to organizer | Low | High | No |
| **P2** | Reputation operational effects | Medium | High | No |
| **P2** | `collapse_at` auto-cancel | Medium | Medium | No |
| **P3** | LLM-enhanced memory weave | Medium | Medium | No |
| **P3** | Event lineage auto-prompt | Medium | Medium | No |
| **P3** | `/reputation` command | Low | Medium | No |
| **P3** | Nudges with recognition framing | Low | Medium | No |
| **P3** | Waitlist support | Medium | Medium | No |
| **P4** | 24h event reminder | Low | Low | No |
| **P4** | `/my_history` (DM only) | Medium | Low | No |
| **P4** | Organizer role rotation | High | Low | No |

---

## Recommended Upgrade Roadmap

### Phase 4.1: Compliance & Core (4 weeks)

**Week 1-2: Log Pruning (GDPR)**
- Implement scheduled job for 90-day log deletion
- Add data retention policy documentation
- Test with production data backup

**Week 3-4: Automatic Memory Collection**
- Implement post-event DM flow
- Add 24-hour collection window
- Upgrade to LLM-enhanced weave generation

### Phase 4.2: Reputation & Materialization (4 weeks)

**Week 5-6: Reputation Operational**
- Wire reputation into priority logic
- Implement reconfirmation window logic
- Add `/reputation` command

**Week 7-8: Full Materialization**
- Add cancellation DM to organizer
- Implement near-collapse announcements
- Add 24h event reminders

### Phase 4.3: Enhancement (4 weeks)

**Week 9-10: Event Lineage**
- Auto-prompt at event creation
- Hashtag suggestions from prior events
- Memory anchor display

**Week 11-12: Waitlist & Polish**
- Implement waitlist support
- Auto-promote from waitlist
- Bug fixes and testing

---

## Conclusion

The current implementation is **production-ready** for core coordination features. The remaining gaps are primarily enhancements that add depth to the product vision rather than blocking issues.

**Immediate Priorities:**
1. Log pruning (GDPR compliance)
2. Automatic memory collection (core differentiation)
3. Cancellation DM (PRD design principle)

**Medium-Term Enhancements:**
1. Reputation operational effects
2. LLM-enhanced memory weave
3. Event lineage

**Nice-to-Have:**
1. 24h reminders
2. `/my_history` command
3. Organizer role rotation

All upgrades should maintain the core design principles:
- Recognition over enforcement
- Gravity over control
- Memory over surveillance
