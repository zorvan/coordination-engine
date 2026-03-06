-- Add normalized pre-event behavioral feedback table.
CREATE TABLE IF NOT EXISTS early_feedback (
    early_feedback_id SERIAL PRIMARY KEY,
    event_id INTEGER NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    source_user_id INTEGER REFERENCES users(user_id) ON DELETE SET NULL,
    target_user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    source_type VARCHAR(50) NOT NULL CHECK (
        source_type IN ('constraint', 'discussion', 'private_peer', 'system')
    ),
    signal_type VARCHAR(50) NOT NULL DEFAULT 'overall' CHECK (
        signal_type IN ('overall', 'reliability', 'cooperation', 'toxicity', 'commitment', 'trust')
    ),
    value FLOAT NOT NULL CHECK (value >= 0 AND value <= 5),
    weight FLOAT NOT NULL DEFAULT 0.5 CHECK (weight >= 0 AND weight <= 1),
    confidence FLOAT NOT NULL DEFAULT 0.6 CHECK (confidence >= 0 AND confidence <= 1),
    sanitized_comment TEXT,
    is_private BOOLEAN NOT NULL DEFAULT FALSE,
    metadata JSONB NOT NULL DEFAULT '{}',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_early_feedback_event
    ON early_feedback(event_id);
CREATE INDEX IF NOT EXISTS idx_early_feedback_target
    ON early_feedback(target_user_id);
CREATE INDEX IF NOT EXISTS idx_early_feedback_source
    ON early_feedback(source_user_id);
CREATE INDEX IF NOT EXISTS idx_early_feedback_source_type
    ON early_feedback(source_type);
