ALTER TABLE events
ADD COLUMN IF NOT EXISTS planning_prefs JSONB DEFAULT '{}'::jsonb;
