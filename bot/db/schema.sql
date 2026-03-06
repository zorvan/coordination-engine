-- Database schema for Telegram Coordination Bot

-- 1. Users: Global identity across groups
CREATE TABLE IF NOT EXISTS users (
    user_id SERIAL PRIMARY KEY,
    telegram_user_id BIGINT UNIQUE NOT NULL,
    username VARCHAR(255) UNIQUE,
    display_name VARCHAR(255),
    reputation FLOAT DEFAULT 1.0 CHECK (reputation >= 0 AND reputation <= 5),
    expertise_per_activity JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Groups: Telegram group context
CREATE TABLE IF NOT EXISTS groups (
    group_id SERIAL PRIMARY KEY,
    telegram_group_id BIGINT UNIQUE NOT NULL,
    group_name VARCHAR(255),
    group_type VARCHAR(50) DEFAULT 'casual' CHECK (group_type IN ('casual', 'gathering', 'tournament')),
    member_list JSONB DEFAULT '[]',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Events: Gathering lifecycle
CREATE TABLE IF NOT EXISTS events (
    event_id SERIAL PRIMARY KEY,
    group_id INTEGER REFERENCES groups(group_id) ON DELETE CASCADE,
    event_type VARCHAR(100) NOT NULL,
    description TEXT,
    organizer_telegram_user_id BIGINT,
    scheduled_time TIMESTAMP,
    commit_by TIMESTAMP,
    duration_minutes INTEGER DEFAULT 120,
    threshold_attendance INTEGER DEFAULT 0,
    attendance_list JSONB DEFAULT '[]',
    planning_prefs JSONB DEFAULT '{}',
    ai_score FLOAT DEFAULT 0.0,
    state VARCHAR(20) DEFAULT 'proposed' CHECK (state IN ('proposed', 'interested', 'confirmed', 'locked', 'completed', 'cancelled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    locked_at TIMESTAMP,
    completed_at TIMESTAMP
);

-- 4. Constraints: Conditional participation
CREATE TABLE IF NOT EXISTS constraints (
    constraint_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    target_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    event_id INTEGER REFERENCES events(event_id) ON DELETE CASCADE,
    type VARCHAR(50) NOT NULL CHECK (
        type IN ('if_joins', 'if_attends', 'unless_joins')
        OR type LIKE 'available:%'
    ),
    confidence FLOAT DEFAULT 1.0 CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 5. Reputation: Activity-specific credibility
CREATE TABLE IF NOT EXISTS reputation (
    reputation_id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    activity_type VARCHAR(100) NOT NULL,
    score FLOAT DEFAULT 1.0 CHECK (score >= 0 AND score <= 5),
    decay_rate FLOAT DEFAULT 0.05,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, activity_type)
);

-- 6. Logs: Audit trail
CREATE TABLE IF NOT EXISTS logs (
    log_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) ON DELETE SET NULL,
    user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    action VARCHAR(100) NOT NULL CHECK (action IN ('organize_event', 'join', 'confirm', 'cancel', 'suggest_time', 'nudge', 'constraint_update')),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB DEFAULT '{}'
);

-- 7. Feedback: Post-event ratings
CREATE TABLE IF NOT EXISTS feedback (
    feedback_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    score_type VARCHAR(50) NOT NULL CHECK (score_type IN ('event_quality', 'member_reliability', 'ai_suggestion')),
    value FLOAT NOT NULL CHECK (value >= 0 AND value <= 5),
    comment TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(event_id, user_id, score_type)
);

-- 8. EarlyFeedback: Pre-event behavioral signals (normalized)
CREATE TABLE IF NOT EXISTS early_feedback (
    early_feedback_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) ON DELETE CASCADE,
    source_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    target_user_id INTEGER REFERENCES users(user_id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL CHECK (
        source_type IN ('constraint', 'discussion', 'private_peer', 'system')
    ),
    signal_type VARCHAR(50) NOT NULL DEFAULT 'overall' CHECK (
        signal_type IN ('overall', 'reliability', 'cooperation', 'toxicity', 'commitment', 'trust')
    ),
    value FLOAT NOT NULL CHECK (value >= 0 AND value <= 5),
    weight FLOAT DEFAULT 0.5 CHECK (weight >= 0 AND weight <= 1),
    confidence FLOAT DEFAULT 0.6 CHECK (confidence >= 0 AND confidence <= 1),
    sanitized_comment TEXT,
    is_private BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 9. AILog: AI decision tracking
CREATE TABLE IF NOT EXISTS ailog (
    ailog_id SERIAL PRIMARY KEY,
    event_id INTEGER REFERENCES events(event_id) ON DELETE SET NULL,
    recommendation_type VARCHAR(100) NOT NULL CHECK (recommendation_type IN ('suggest_time', 'threshold_prediction', 'conflict_warning', 'nudge_trigger')),
    recommendation_value TEXT NOT NULL,
    confidence FLOAT,
    is_fallback BOOLEAN DEFAULT FALSE,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_events_group ON events(group_id);
CREATE INDEX IF NOT EXISTS idx_events_state ON events(state);
CREATE INDEX IF NOT EXISTS idx_constraints_event ON constraints(event_id);
CREATE INDEX IF NOT EXISTS idx_logs_event ON logs(event_id);
CREATE INDEX IF NOT EXISTS idx_feedback_event ON feedback(event_id);
CREATE INDEX IF NOT EXISTS idx_early_feedback_event ON early_feedback(event_id);
CREATE INDEX IF NOT EXISTS idx_early_feedback_target ON early_feedback(target_user_id);
CREATE INDEX IF NOT EXISTS idx_early_feedback_source ON early_feedback(source_user_id);
CREATE INDEX IF NOT EXISTS idx_early_feedback_source_type ON early_feedback(source_type);
CREATE INDEX IF NOT EXISTS idx_ailog_event ON ailog(event_id);
CREATE INDEX IF NOT EXISTS idx_reputation_user ON reputation(user_id);
