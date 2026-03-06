ALTER TABLE events
ADD COLUMN IF NOT EXISTS commit_by TIMESTAMP;

-- Attendance status model now uses JSON markers like:
--   "<telegram_user_id>:invited|interested|committed|confirmed"
-- Legacy entries (plain IDs or :confirmed) remain backward-compatible in code.
