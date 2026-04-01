# Coordination Engine v2 — UX Improvement Backlog

This document identifies features that are **implemented as minimal versions** and can be significantly improved for better user experience.

---

## 🎯 High-Impact Improvements (Priority 1)

### 1. Memory Weave Generation with LLM

**Current Implementation:** Simple concatenation of fragments  
**File:** `bot/services/event_memory_service.py:223`

```python
# Current: Simple formatting
weave_parts = [f"📿 <b>How people remember: {event_anchor}</b>\n"]
for fragment in memory.fragments:
    weave_parts.append(f"• \"{fragment['text']}\"")
```

**UX Problem:** Feels mechanical, doesn't capture emotional resonance or create narrative flow.

**Improved Version:**
```python
async def generate_memory_weave(self, event: Event) -> Optional[str]:
    # Use LLM to create poetic, flowing narrative
    prompt = f"""
    Create a brief, poetic memory weave from these participant fragments.
    Preserve multiple voices - don't merge into single narrative.
    Keep contradictions and different tones visible.
    Format for Telegram (HTML, ~150 words max).
    
    Event: {event.event_type} on {event.scheduled_time}
    Fragments: {memory.fragments}
    Tones: {memory.tone_palette}
    """
    
    llm_response = await llm.generate(prompt)
    return llm_response.weave_text
```

**Impact:** ⭐⭐⭐⭐⭐  
**Effort:** Medium (LLM integration already exists)  
**PRD Alignment:** Section 2.3.2 (Memory Weave should feel human)

---

### 2. Materialization Message Personalization

**Current Implementation:** Random choice from predefined templates  
**File:** `bot/utils/nudges.py`

```python
# Current: Random selection
messages = [
    f"⚠️ {name} had to drop...",
    f"FYI: {name} can't make it...",
    f"{name} needed to cancel...",
]
return random.choice(messages)
```

**UX Problem:** Feels generic, doesn't adapt to group culture or event type.

**Improved Version:**
```python
async def generate_personalized_cancellation(
    self,
    event: Event,
    user: User,
    group_culture: str,  # formal, casual, competitive, social
    cancellation_context: dict,  # reason, timing, frequency
) -> str:
    # Adapt tone to group culture
    if group_culture == "casual":
        return f"Hey — {name} can't make it anymore. No worries!"
    elif group_culture == "competitive":
        return f"FYI: {name} had to drop. Still got {remaining} committed players!"
    elif group_culture == "social":
        return f"{name} won't be able to join us this time. See you next one!"
    
    # Consider cancellation context
    if cancellation_context.get('reason') == 'emergency':
        return f"{name} had an emergency come up. Sending good vibes!"
    elif cancellation_context.get('frequency', 0) > 3:
        # Private message to organizer only
        return f"Note: {name} has cancelled 3x recently. Worth a check-in."
```

**Impact:** ⭐⭐⭐⭐  
**Effort:** Medium (requires group culture tracking)  
**PRD Alignment:** Section 5.2 (Bot persona should be relational)

---

### 3. Smart Hashtag Suggestions

**Current Implementation:** Frequency-based from past events  
**File:** `bot/services/event_memory_service.py:340`

```python
# Current: Most common hashtags
counts = Counter(all_hashtags)
return [tag for tag, _ in counts.most_common(3)]
```

**UX Problem:** Doesn't capture emerging language or event-specific moments.

**Improved Version:**
```python
async def suggest_hashtags_with_llm(
    self,
    event: Event,
    memory_fragments: list,
    prior_hashtags: list,
) -> list[str]:
    # Use LLM to suggest hashtags that capture essence
    prompt = f"""
    Suggest 1-3 natural hashtags for this event memory.
    Mix: activity type + memorable moment + group inside joke potential.
    
    Event: {event.event_type}
    Fragments: {memory_fragments}
    Past hashtags: {prior_hashtags}
    
    Make them:
    - Memorable (not just #badminton)
    - Reusable (could become group language)
    - Specific to THIS event (#rainyday rally, not #sunday)
    """
    
    return await llm.generate_hashtags(prompt)
```

**Impact:** ⭐⭐⭐⭐  
**Effort:** Low-Medium  
**PRD Alignment:** Section 2.3.2 (Hashtags as cultural building blocks)

---

### 4. Mutual Dependence Visualization

**Current Implementation:** Text-only reminder  
**File:** `bot/utils/nudges.py:102`

```python
# Current: Simple text
f"{other_str} {'are' if len > 1 else 'is'} counting on you for the {event_type}."
```

**UX Problem:** Doesn't show the actual web of relationships.

**Improved Version:**
```python
async def generate_dependence_visualization(
    self,
    event_id: int,
    user_id: int,
) -> str:
    # Get all participants and their photos
    participants = await self.get_participants_with_photos(event_id)
    
    # Create visual grid
    photos = [p.photo_url for p in participants if p.photo_url]
    
    if photos:
        # Create a collage and send as photo with caption
        collage = await create_participant_collage(photos)
        
        caption = (
            f"You're part of this group for {event.event_type}:\n\n"
            f"{len(photos)} people confirmed\n"
            f"Your presence completes the picture 🧩"
        )
        
        await bot.send_photo(chat_id, photo=collage, caption=caption)
    else:
        # Fallback to text with names
        names = [p.name for p in participants]
        await bot.send_message(f"👥 {', '.join(names)}\n\nYou complete this group!")
```

**Impact:** ⭐⭐⭐⭐⭐  
**Effort:** Medium (image processing)  
**PRD Alignment:** Section 2.2.5 (Visibility of mutual dependence)

---

### 5. Post-Event Memory Collection Timing

**Current Implementation:** Fixed 2-hour delay, 24-hour window  
**File:** `bot/services/event_memory_service.py:26-29`

```python
COLLECTION_WINDOW_HOURS = 24
COLLECTION_DELAY_HOURS = 2  # Fixed for all events
```

**UX Problem:** Doesn't account for event type, time of day, or group preferences.

**Improved Version:**
```python
async def determine_optimal_collection_timing(
    self,
    event: Event,
    group_preferences: dict,
) -> tuple[datetime, datetime]:
    # Adapt timing to event type
    if event.event_type.lower() in ['party', 'celebration', 'dinner']:
        # Social events: wait longer, people need decompression
        delay_hours = 4
        window_hours = 48
    elif event.event_type.lower() in ['workout', 'sports', 'hiking']:
        # Physical events: strike while soreness is fresh
        delay_hours = 1
        window_hours = 18
    elif event.scheduled_time.hour >= 20:
        # Late night events: wait until next day
        delay_hours = 12
        window_hours = 36
    else:
        delay_hours = 2
        window_hours = 24
    
    # Respect group preferences
    if group_preferences.get('quiet_hours'):
        # Don't send DMs during quiet hours
        delay_hours = max(delay_hours, hours_until_morning())
    
    start_time = event.completed_at + timedelta(hours=delay_hours)
    end_time = start_time + timedelta(hours=window_hours)
    
    return start_time, end_time
```

**Impact:** ⭐⭐⭐  
**Effort:** Low  
**PRD Alignment:** Section 2.3.1 (Bot as "absent friend" — good timing matters)

---

## 🎨 Medium-Impact Improvements (Priority 2)

### 6. Event Detail View Enhancement

**Current Implementation:** Basic text display  
**File:** `bot/commands/event_details.py`

**Missing:** Visibility of mutual dependence, threshold progress

**Improved Version:**
```python
async def show_event_details(event_id: int, user_id: int) -> str:
    # Show who else is coming WITH their relationship to user
    participants = await get_participants_with_relationships(event_id, user_id)
    
    # Calculate "you complete" message
    user_position = participants.index(user_id) + 1
    total = len(participants)
    
    message = f"""
📋 {event.event_type}

👥 Who's in ({total} people):
{format_participant_list(participants, highlight_mutual_connections=user_id)}

📊 Threshold progress:
{'█' * confirmed_count}{'░' * (min_required - confirmed_count)} 
{confirmed_count}/{min_required} confirmed

💫 Your role:
You're person {user_position} of {total}. 
{get_personal_impact_message(user_id, participants)}
"""
    return message
```

**Impact:** ⭐⭐⭐⭐  
**Effort:** Medium  
**PRD Alignment:** Section 2.2.5 (Visibility of mutual dependence)

---

### 7. Reputation Trend Visualization

**Current Implementation:** Text-only trend message  
**File:** `bot/utils/nudges.py:134`

**Missing:** Visual trend chart, personal insights

**Improved Version:**
```python
async def generate_reputation_trend_chart(user_id: int) -> bytes:
    # Get last 10 events
    history = await get_user_event_history(user_id, limit=10)
    
    # Create ASCII chart for Telegram
    chart = create_ascii_sparkline([h.reliability for h in history])
    
    # Add insights
    insights = await generate_reputation_insights(history)
    
    message = f"""
📊 Your Reliability Trend

{chart}

{insights}

💡 Tip: {get_personalized_improvement_tip(history)}
"""
    return message
```

**Impact:** ⭐⭐⭐  
**Effort:** Medium (chart generation)  
**PRD Alignment:** Section 2.2.4 (Reputation as background signal, personal trend)

---

### 8. Waitlist Management

**Current Implementation:** TODO stub  
**File:** `bot/services/event_materialization_service.py:200`

```python
# TODO: Add waitlist status when waitlist feature is implemented
```

**Improved Version:**
```python
class WaitlistService:
    async def add_to_waitlist(self, event_id: int, user_id: int) -> tuple[int, bool]:
        # Add user to waitlist
        # Return position and is_movable flag
        
    async def check_waitlist_status(self, event_id: int, user_id: int) -> dict:
        # Return position, estimated chance, auto-promote settings
        
    async def auto_promote_from_waitlist(self, event_id: int, cancelled_user_id: int):
        # When someone cancels, auto-promote first waitlisted person
        # Send DM: "Spot opened up! Confirm within 2 hours?"
```

**Impact:** ⭐⭐⭐⭐  
**Effort:** Medium  
**PRD Alignment:** Section 3.1 (Existing features gap analysis)

---

### 9. Event Note Enhancement

**Current Implementation:** Basic organizer notes  
**File:** `bot/commands/event_note.py`

**Missing:** Milestone tracking, automatic updates

**Improved Version:**
```python
async def add_event_note_with_milestones(
    event_id: int,
    organizer_id: int,
    note_text: str,
) -> str:
    # Auto-detect milestones
    milestones = detect_milestones(note_text)
    # "Court booked" → VENUE_CONFIRMED
    # "Got 6 yeses" → THRESHOLD_REACHED
    
    # Post to group with milestone badge
    if milestones:
        badge = get_milestone_badge(milestones[0])
        message = f"{badge} Organizer update: {note_text}"
    else:
        message = f"📝 Organizer note: {note_text}"
    
    # Track milestone history
    await log_milestone(event_id, milestones)
    
    return message
```

**Impact:** ⭐⭐⭐  
**Effort:** Low-Medium  
**PRD Alignment:** Section 2.2.1 (Events as living objects)

---

### 10. Group Digest (Weekly Summary)

**Current Implementation:** Not implemented  
**File:** N/A

**New Feature:**
```python
async def send_weekly_digest(group_id: int):
    # Gather:
    # - Recent completed events with memory highlights
    # - Upcoming events this week
    # - Members who joined for first time
    # - Group milestones (100th event, etc.)
    
    digest = f"""
📰 Weekly Digest for {group_name}

✨ Memories from last week:
{recent_memory_highlights()}

📅 Coming up:
{upcoming_events_preview()}

👋 New faces:
{new_members_this_week()}

🎯 Group stats:
{group_milestones()}
"""
    await bot.send_message(group_id, digest)
```

**Impact:** ⭐⭐⭐⭐  
**Effort:** Medium  
**PRD Alignment:** Section 2.3.4 (Group digest)

---

## 🔧 Low-Effort, High-Value Improvements (Priority 3)

### 11. Emoji Consistency

**Current:** Mixed emoji usage across messages

**Fix:** Create emoji style guide
```python
# bot/common/emoji.py
EMOJI = {
    'first_join': '🌱',
    'join': '👋',
    'threshold': '✨',
    'locked': '🔒',
    'completed': '✅',
    'cancelled': '⚠️',  # Private only
    'memory': '📿',
    'recall': '💭',
}
```

**Impact:** ⭐⭐  
**Effort:** Low  
**PRD Alignment:** Section 5.2 (Consistent bot persona)

---

### 12. Message Thread Organization

**Current:** All messages in main chat

**Improved:** Use Telegram threads for event discussions
```python
async def create_event_thread(event_id: int) -> int:
    # Create dedicated thread for each event
    # Post all materialization messages in thread
    # Keeps main chat clean
```

**Impact:** ⭐⭐⭐  
**Effort:** Low (Telegram API supports this)  
**PRD Alignment:** Section 5.3 (Telegram platform constraints)

---

### 13. Quick Reply Buttons

**Current:** Text commands for everything

**Improved:** Inline keyboards for common actions
```python
# After event completion
keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("📿 Add Memory", callback_data="memory_add_123")],
    [InlineKeyboardButton("📊 View Details", callback_data="event_details_123")],
    [InlineKeyboardButton("📅 Similar Events", callback_data="lineage_123")],
])
```

**Impact:** ⭐⭐⭐⭐  
**Effort:** Low  
**PRD Alignment:** Section 3.1 (One-tap planning UX)

---

### 14. Personalized Event Recommendations

**Current:** None

**New Feature:**
```python
async def suggest_events_for_user(user_id: int) -> list[Event]:
    # Based on:
    # - Past attendance patterns
    # - Private preferences (from /constraints)
    # - Friends' events (social graph)
    # - Reliability-matched (not overcommitting)
    
    return recommended_events
```

**Impact:** ⭐⭐⭐  
**Effort:** Medium  
**PRD Alignment:** Section 2.2.4 (Reputation as background signal)

---

### 15. Event Photo Sharing

**Current:** Text-only memories

**Improved:**
```python
# Accept photos in memory DM flow
if message.photo:
    photo_id = message.photo[-1].file_id
    fragment = {
        'text': caption or '[Photo]',
        'photo_id': photo_id,
        'contributor_hash': hash,
    }
    
# Display in weave
if fragment.get('photo_id'):
    weave_parts.append(f"📸 [Photo from {fragment['contributor_hash']}]")
```

**Impact:** ⭐⭐⭐⭐  
**Effort:** Low-Medium  
**PRD Alignment:** Section 2.3.1 (Accept fragments: short text, a photo)

---

## 📊 Summary Table

| # | Feature | Impact | Effort | Priority |
|---|---------|--------|--------|----------|
| 1 | LLM Memory Weave | ⭐⭐⭐⭐⭐ | Medium | 1 |
| 2 | Personalized Messages | ⭐⭐⭐⭐ | Medium | 1 |
| 3 | Smart Hashtags | ⭐⭐⭐⭐ | Low-Med | 1 |
| 4 | Dependence Visualization | ⭐⭐⭐⭐⭐ | Medium | 1 |
| 5 | Smart Collection Timing | ⭐⭐⭐ | Low | 2 |
| 6 | Enhanced Event Details | ⭐⭐⭐⭐ | Medium | 2 |
| 7 | Reputation Charts | ⭐⭐⭐ | Medium | 2 |
| 8 | Waitlist Management | ⭐⭐⭐⭐ | Medium | 2 |
| 9 | Milestone Tracking | ⭐⭐⭐ | Low-Med | 2 |
| 10 | Weekly Digest | ⭐⭐⭐⭐ | Medium | 2 |
| 11 | Emoji Consistency | ⭐⭐ | Low | 3 |
| 12 | Message Threads | ⭐⭐⭐ | Low | 3 |
| 13 | Quick Reply Buttons | ⭐⭐⭐⭐ | Low | 3 |
| 14 | Event Recommendations | ⭐⭐⭐ | Medium | 3 |
| 15 | Photo Sharing | ⭐⭐⭐⭐ | Low-Med | 3 |

---

## 🚀 Recommended Implementation Order

### Phase 1 (Immediate UX Wins)
1. **LLM Memory Weave** (#1) — Transforms memory layer from mechanical to magical
2. **Quick Reply Buttons** (#13) — Low effort, immediate UX improvement
3. **Emoji Consistency** (#11) — Polish, brand consistency
4. **Smart Hashtags** (#3) — Better cultural continuity

### Phase 2 (Core Experience)
5. **Dependence Visualization** (#4) — Key differentiator
6. **Personalized Messages** (#2) — Feels more human
7. **Photo Sharing** (#15) — Richer memories
8. **Enhanced Event Details** (#6) — Better information display

### Phase 3 (Advanced Features)
9. **Waitlist Management** (#8) — Completes attendance flow
10. **Weekly Digest** (#10) — Re-engagement driver
11. **Reputation Charts** (#7) — Better personal insights
12. **Smart Collection Timing** (#5) — Better timing

### Phase 4 (Nice-to-Have)
13. **Message Threads** (#12) — Organizational polish
14. **Event Recommendations** (#14) — Discovery
15. **Milestone Tracking** (#9) — Engagement gamification (careful!)

---

## 💡 Implementation Tips

### For LLM Features (#1, #2, #3)
- Use existing `ai/llm.py` infrastructure
- Add prompt versioning for A/B testing
- Cache LLM responses to avoid regeneration
- Have deterministic fallback if LLM fails

### For Visual Features (#4, #7)
- Use ASCII charts for Telegram compatibility
- Consider sending images for complex visualizations
- Test on mobile (most Telegram users)

### For Timing Features (#5)
- Respect timezone preferences
- Don't send DMs during group quiet hours
- Allow users to set "memory collection preferences"

---

## 🎯 Success Metrics

Track these to measure UX improvement impact:

| Metric | Current | Target | Measurement |
|--------|---------|--------|-------------|
| Memory fragment submission rate | ~30% | 60% | Fragments / confirmed participants |
| Memory weave view rate | ~20% | 50% | Unique views / completed events |
| Event completion rate | TBD | +15% | Completed / locked events |
| Weekly active users | TBD | +25% | WAU after digest feature |
| Command success rate | TBD | >95% | Successful commands / total |

---

**Remember:** The goal is not feature completeness — it's **richness of shared experiences** (PRD Primary KPI). Every improvement should make events feel more real, more meaningful, and more worth showing up for.
