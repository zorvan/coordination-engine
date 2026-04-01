# Coordination Engine v2 — Migration Checklist

Use this checklist to safely migrate from v1 to v2.

---

## Pre-Migration

### 1. Backup Everything

```bash
# Database backup
pg_dump your_database > backup_$(date +%Y%m%d_%H%M%S).sql

# Code backup
git status
git add .
git commit -m "Pre-v2 migration backup"
git tag v1-backup-$(date +%Y%m%d)
```

- [ ] Database backed up
- [ ] Code committed
- [ ] Git tag created

### 2. Review Changes

- [ ] Read `docs/v2/coordination-engine-PRD.md`
- [ ] Read `docs/v2/IMPLEMENTATION_SUMMARY.md`
- [ ] Read `docs/v2/QUICKSTART.md`

### 3. Test Environment

- [ ] Set up staging/test database
- [ ] Clone production data to staging (anonymized if needed)
- [ ] Test migration on staging first

---

## Migration Steps

### Step 1: Update Code

```bash
# Pull latest v2 code
git pull origin main  # or your v2 branch
```

- [ ] New service files present
- [ ] Modified files updated
- [ ] No merge conflicts

### Step 2: Update Dependencies

```bash
# Check requirements
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

- [ ] Dependencies installed
- [ ] No version conflicts

### Step 3: Update Environment

Add to `.env`:

```bash
# v2 Feature flags
ENABLE_MATERIALIZATION=true
ENABLE_MEMORY_LAYER=true
ENABLE_REPUTATION_EFFECTS=false
ENABLE_IDEMPOTENCY=false
JSON_LOGS=false
ENVIRONMENT=development
```

- [ ] Environment variables added
- [ ] `.env` file updated (not committed!)

### Step 4: Run Database Migration

```bash
# Dry run (if possible)
python scripts/migrate_v2.py --dry-run

# Actual migration
python scripts/migrate_v2.py
```

Expected output:
```
============================================================
Coordination Engine v2 Database Migration
============================================================

Connecting to database...
  ✓ Database connection successful
Migrating events table...
  ...
  
✓ Migration completed successfully!
```

- [ ] Migration script ran without errors
- [ ] All new tables created
- [ ] All new columns added
- [ ] Data migrated (attendance_list → event_participants)
- [ ] Indexes created

### Step 5: Verify Database

```sql
-- Check events table
\d events

-- Should show new columns:
-- min_participants, target_participants, collapse_at, 
-- lock_deadline, version

-- Check new tables exist
\d event_participants
\d idempotency_keys
\d event_state_transitions
\d event_memories

-- Check data migrated
SELECT COUNT(*) FROM event_participants;
SELECT COUNT(*) FROM events WHERE attendance_list IS NOT NULL;
```

- [ ] New columns present in `events`
- [ ] New tables exist
- [ ] Participant data migrated
- [ ] Indexes created

### Step 6: Start Bot

```bash
# Start bot
python main.py

# Check logs
tail -f bot.log
```

Look for:
```
Logging configured root=INFO telegram=INFO httpx=WARNING json=False
Database tables initialized
Bot started. Press Ctrl+C to stop.
```

- [ ] Bot starts without errors
- [ ] Database connection successful
- [ ] No import errors
- [ ] Logging configured correctly

---

## Post-Migration Verification

### Test Layer 1: Coordination

#### Test Event Creation
```
/organize_event
```
- [ ] Event created successfully
- [ ] New fields present (min_participants, etc.)

#### Test Join
```
/join [event_id]
```
- [ ] User added to event_participants table
- [ ] No errors in logs

#### Test State Transitions
```
/lock [event_id]
```
- [ ] Lock succeeds if threshold met
- [ ] Lock fails if threshold not met
- [ ] Transition logged in event_state_transitions

### Test Layer 2: Materialization

#### Check Announcements
- [ ] Bot posts "X just joined" message to group
- [ ] Bot posts threshold celebration
- [ ] Bot posts lock announcement with participant list
- [ ] Cancellations sent privately to organizer only

#### Check Nudges
- [ ] No public shaming messages
- [ ] Recognition-based framing used
- [ ] Mutual dependence messages work

### Test Layer 3: Memory

#### Test Memory Commands
```
/recall
```
- [ ] Shows recent memories (or "no memories yet")

```
/memory [event_id]
```
- [ ] Shows memory weave for completed event

```
/remember [event_id] test memory
```
- [ ] Accepts memory fragment
- [ ] Stores in event_memories table

#### Test Memory Collection
After completing an event:
- [ ] Bot DMs participants requesting memories
- [ ] Memories collected and stored
- [ ] Weave generated and posted to group

### Test Logging

```bash
# Check logs
tail -f bot.log | grep "event_state"
```

Should show structured logs:
```
2025-12-20 10:30:45 - coord_bot.services.event_state - INFO - Event state transition
```

- [ ] Logs appear correctly
- [ ] Correlation IDs present (if JSON_LOGS=true)
- [ ] No sensitive data in logs

---

## Rollback Plan

If something goes wrong:

### Quick Rollback

```bash
# Stop bot
Ctrl+C

# Restore database
psql your_database < backup_YYYYMMDD_HHMMSS.sql

# Revert code
git checkout <previous-tag>

# Restart bot
python main.py
```

- [ ] Rollback procedure tested on staging
- [ ] Backup restore verified
- [ ] Team knows rollback procedure

### Partial Rollback

If only some features have issues:

```bash
# Disable problematic features in .env
ENABLE_MATERIALIZATION=false
ENABLE_MEMORY_LAYER=false

# Restart bot
```

---

## Monitoring

### First 24 Hours

Monitor:
- [ ] Error rate in logs
- [ ] Command success rate
- [ ] Database performance
- [ ] User reports/issues

### First Week

Track:
- [ ] Event creation rate
- [ ] Participation rate
- [ ] Memory weave generation
- [ ] Group engagement

### Metrics to Watch

```sql
-- Event state transitions per day
SELECT DATE(timestamp), COUNT(*) 
FROM event_state_transitions 
GROUP BY DATE(timestamp) 
ORDER BY DATE(timestamp);

-- Participant growth
SELECT DATE(joined_at), COUNT(*) 
FROM event_participants 
GROUP BY DATE(joined_at) 
ORDER BY DATE(joined_at);

-- Memory collection rate
SELECT DATE(created_at), COUNT(*) 
FROM event_memories 
GROUP BY DATE(created_at) 
ORDER BY DATE(created_at);
```

---

## Success Criteria

Migration is successful when:

- [ ] All existing events accessible
- [ ] New events can be created with threshold fields
- [ ] Join/confirm/cancel work via new services
- [ ] Materialization messages appear in groups
- [ ] Memory commands functional
- [ ] No data loss
- [ ] Error rate < 1%
- [ ] User-facing features working normally

---

## Troubleshooting

### Issue: Migration fails with "column already exists"

**Cause:** Migration partially run before

**Solution:**
```sql
-- Check what exists
\d events

-- Drop and re-run, or manually complete
ALTER TABLE events DROP COLUMN IF EXISTS min_participants;
-- Then re-run migration
```

### Issue: Bot won't start after migration

**Check:**
```bash
# Check logs
tail -f bot.log

# Test database connection
psql your_database -c "SELECT 1"

# Check imports
python -c "from bot.services import EventStateTransitionService"
```

### Issue: Materialization messages not appearing

**Check:**
- Bot is group admin
- `ENABLE_MATERIALIZATION=true`
- Bot has send permissions in group

### Issue: Memory collection not starting

**Check:**
- Event state is `completed`
- `ENABLE_MEMORY_LAYER=true`
- Event has confirmed participants

---

## Sign-Off

- [ ] Migration completed successfully
- [ ] All tests passing
- [ ] Team notified
- [ ] Documentation updated
- [ ] Backup retained for 30 days

**Migration completed by:** ________________  
**Date:** ________________  
**Notes:** ________________

---

## Next Steps

After successful migration:

1. Enable production features:
   ```bash
   ENABLE_IDEMPOTENCY=true
   JSON_LOGS=true
   ```

2. Set up monitoring dashboards

3. Plan Phase 2 features (reputation effects)

4. Schedule log pruning implementation

---

Good luck! 🚀
