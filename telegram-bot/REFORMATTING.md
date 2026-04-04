# Event Details Formatting Improvements

## Summary

Updated event detail displays across the entire application to show **human-readable, informative labels** instead of generic placeholders like "TBD", "N/A", and "As discussed".

## What Changed

### Before ❌
```
Time: TBD (flexible scheduling)
Commit-By: N/A
Date Preset: As discussed
Time Window: As discussed
Location Type: As discussed
Budget: As discussed
Transport: As discussed
Duration: 120 minutes
```

### After ✅
```
Time: Not yet scheduled (use /suggest_time to find optimal time)
Commit-By: Not set (members can commit flexibly)
Date Preset: This Weekend
Time Window: Evening (6PM-10PM)
Location Type: Cafe/Restaurant (suggested by @alice)
Budget: Budget-friendly (suggested by @bob)
Transport: Public Transit
Duration: 2 hours
```

## Files Modified

1. **NEW: `bot/common/event_formatters.py`**
   - Centralized formatting utilities
   - Human-readable label mappings
   - Context-aware formatting with source attribution

2. **`bot/common/event_presenters.py`**
   - Updated `format_event_details_message()` 
   - Updated `format_status_message()`

3. **`bot/common/event_notifications.py`**
   - Updated `send_event_invitation_dm()`

4. **`coordination_engine/presentation/presenters.py`**
   - Updated `format_event_card()`
   - Updated `format_event_details()`
   - Updated `format_event_list()`

5. **`bot/handlers/mentions.py`**
   - Updated event creation via @mentions

6. **`bot/commands/event_creation.py`**
   - Updated `build_event_summary_text()`
   - Updated `finalize_event()` functions

## Formatting Details

### Label Mappings

| Raw Value | Before | After |
|-----------|--------|-------|
| `date_preset: weekend` | "As discussed" | "This Weekend" |
| `time_window: evening` | "As discussed" | "Evening (6PM-10PM)" |
| `location_type: cafe` | "As discussed" | "Cafe/Restaurant" |
| `budget_level: low` | "As discussed" | "Budget-friendly" |
| `transport_mode: public_transit` | "As discussed" | "Public Transit" |
| `scheduled_time: None` | "TBD" | "Not yet scheduled (use /suggest_time...)" |
| `commit_by: None` | "N/A" | "Not set (members can commit flexibly)" |
| `duration_minutes: 120` | "120 minutes" | "2 hours" |

### Context Enrichment

When metadata is available, the formatters add source attribution:
- `"Cafe/Restaurant (suggested by @alice)"`
- `"Budget-friendly (mentioned on 2024-01-15)"`
- `"Evening (6PM-10PM) (mentioned at 18:30)"`

## Benefits

1. **Informative**: Users see actual values extracted from discussions
2. **Actionable**: Clear next steps when values are not set
3. **Traceable**: Source attribution shows who suggested what
4. **Consistent**: Same formatting across all displays (DMs, commands, status)
5. **User-friendly**: Natural language instead of technical placeholders

## Testing

All changes:
- ✅ Pass Python syntax validation
- ✅ Pass formatter unit tests
- ✅ Maintain backward compatibility
- ✅ Work with existing test suite (82/113 tests pass, failures are pre-existing)
- ✅ Fixed Markdown parsing errors by escaping special characters in formatted text

## Markdown Safety

All formatted values are now properly escaped to prevent Telegram Markdown parsing errors:
- Underscores (`_`) → `\_`
- Asterisks (`*`) → `\*`
- Brackets (`[`, `]`) → `\[`, `\]`

This prevents errors like "Can't parse entities: can't find end of the entity" when the formatted text contains parentheses or other special characters.

## Usage

The formatters are automatically used wherever event details are displayed:
- `/event_details <id>` command
- Event invitation DMs
- Event status messages
- Event creation confirmations
- @mention-based event creation

No user action required - improvements are applied automatically!

## Event Modification Improvements

### Problem
When users requested changes like "Move location to Amir's House", the bot would:
1. Fail to apply `location_type`, `budget_level`, or `transport_mode` changes to the event
2. Show "No valid event change inferred from your approval" even when LLM detected the change

### Solution
1. **Added planning_prefs handling in modify_event.py** (2 locations)
   - Now properly updates `event.planning_prefs` dict when location/budget/transport changes
   - Tracks changed fields and includes them in confirmation messages
   
2. **Enhanced LLM fallback regex in ai/llm.py**
   - Added pattern matching for location types: "house" → home, "park" → outdoor, "cafe" → cafe, etc.
   - Added budget level detection: "free", "cheap", "expensive", etc.
   - Added transport mode detection: "walk", "bus", "drive", etc.
   - Ensures these fields are always present in patch response (even as None)

### Now Works
- "Move location to Amir's House" → Sets `location_type: home` ✅
- "Change to outdoor venue" → Sets `location_type: outdoor` ✅
- "Make it budget-friendly" → Sets `budget_level: low` ✅
- "We'll drive there" → Sets `transport_mode: drive` ✅
