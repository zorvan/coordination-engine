## Report

**1. Scheduler/Cron-like functionality in main.py:**
- No built-in scheduler is configured in `main.py`
- Comments at lines 167-169 explicitly state deadline checks require `python-telegram-bot[job-queue]` and are currently manual or require external scheduler

**2. Calls to `check_and_lock_expired_events` or `check_deadline_status`:**

Files using `check_and_lock_expired_events`:
- `/home/zorvan/Work/projects/qwen3/coordination-engine/bot/bot/commands/check_deadlines.py` (lines 6, 19, 55)
  - Line 6: `from bot.common.deadline_check import check_and_lock_expired_events`
  - Line 19: `results = await check_and_lock_expired_events()` (in `/check_deadlines` command handler)
  - Line 55: `results = await check_and_lock_expired_events()` (in `run_scheduled_check` callback)

Files using `check_deadline_status`:
- None found in the codebase (function is defined but not called)

**3. Background tasks:**
- No background tasks configured
- `main.py` only sets up Telegram polling with no job queue or periodic tasks

**Complete findings:**

```
/home/zorvan/Work/projects/qwen3/coordination-engine/bot/bot/commands/check_deadlines.py
```
- Imports `check_and_lock_expired_events` from `bot.common.deadline_check`
- `handle()` function (line 19) - triggered by `/check_deadlines` command
- `run_scheduled_check()` function (line 55) - defined but never registered as a job

```
/home/zorvan/Work/projects/qwen3/coordination-engine/bot/bot/common/deadline_check.py
```
- Contains `check_and_lock_expired_events()` (lines 13-49) - checks events past deadline and auto-locks if threshold met
- Contains `check_deadline_status()` (lines 92-132) - returns deadline status for single event (unused)

**Conclusion:**
- No scheduler is running in the bot
- Deadline checking must be triggered manually via `/check_deadlines` command
- The `run_scheduled_check` function exists but is never registered with the application's JobQueue
- To enable automatic deadline checking, the bot would need to install `python-telegram-bot[job-queue]` and register a periodic job