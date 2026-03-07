-- Add user preferences table for private preference profiles

CREATE TABLE IF NOT EXISTS user_preferences (
    preference_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    time_preference VARCHAR(50) DEFAULT 'any', -- any, morning, afternoon, evening, night
    activity_preference VARCHAR(100) DEFAULT 'any', -- any, social, sports, work, outdoor, indoor
    budget_preference VARCHAR(50) DEFAULT 'any', -- any, free, low, medium, high
    location_type_preference VARCHAR(100) DEFAULT 'any', -- any, home, outdoor, cafe, office, gym
    transport_preference VARCHAR(50) DEFAULT 'any', -- any, walk, public_transit, drive
    privacy_settings JSONB DEFAULT '{}', -- privacy controls for each preference type
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_user_preferences_time ON user_preferences(time_preference);
CREATE INDEX IF NOT EXISTS idx_user_preferences_activity ON user_preferences(activity_preference);
CREATE INDEX IF NOT EXISTS idx_user_preferences_budget ON user_preferences(budget_preference);
