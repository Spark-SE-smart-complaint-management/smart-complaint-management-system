-- REQ-41/42: channel preferences and a retryable delivery outbox.
-- These are additive tables; the existing notifications table is unchanged.
CREATE TABLE IF NOT EXISTS notification_preferences (
    id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    channels TEXT NOT NULL DEFAULT '["in_app"]',
    updated_at DATETIME NOT NULL
);

CREATE TABLE IF NOT EXISTS notification_deliveries (
    id INTEGER PRIMARY KEY,
    notification_id INTEGER NOT NULL REFERENCES notifications(id) ON DELETE CASCADE,
    channel VARCHAR(10) NOT NULL,
    idempotency_key VARCHAR(64) NOT NULL UNIQUE,
    delivery_status VARCHAR(15) NOT NULL DEFAULT 'Pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    next_attempt_at DATETIME,
    created_at DATETIME NOT NULL,
    updated_at DATETIME NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_notification_deliveries_due
    ON notification_deliveries(delivery_status, next_attempt_at);
