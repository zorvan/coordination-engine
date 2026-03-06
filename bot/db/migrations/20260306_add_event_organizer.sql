-- Add explicit organizer to events for access control.
ALTER TABLE events
ADD COLUMN IF NOT EXISTS organizer_telegram_user_id BIGINT;

CREATE INDEX IF NOT EXISTS idx_events_organizer_tg
ON events(organizer_telegram_user_id);
