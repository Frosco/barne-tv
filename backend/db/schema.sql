-- backend/db/schema.sql
-- Safe YouTube Viewer Database Schema
-- SQLite 3.45.0+
-- All timestamps in ISO 8601 format (UTC)
-- BOOLEAN columns stored as INTEGER: 0 = false, 1 = true

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

-- =============================================================================
-- CONTENT SOURCES
-- =============================================================================

CREATE TABLE IF NOT EXISTS content_sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL UNIQUE,
    source_type TEXT NOT NULL CHECK(source_type IN ('channel', 'playlist')),
    name TEXT NOT NULL,
    video_count INTEGER NOT NULL DEFAULT 0 CHECK(video_count >= 0),
    last_refresh TEXT NOT NULL,
    fetch_method TEXT NOT NULL CHECK(fetch_method IN ('api')),
    added_at TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_content_sources_source_id ON content_sources(source_id);
CREATE INDEX idx_content_sources_type ON content_sources(source_type);

-- =============================================================================
-- VIDEOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL,                    -- YouTube video ID (NOT UNIQUE - duplicates allowed)
    title TEXT NOT NULL,
    content_source_id INTEGER NOT NULL,

    -- Denormalized YouTube metadata (not FKs)
    youtube_channel_id TEXT NOT NULL,
    youtube_channel_name TEXT NOT NULL,

    thumbnail_url TEXT NOT NULL,
    duration_seconds INTEGER NOT NULL CHECK(duration_seconds >= 0),
    published_at TEXT NOT NULL,
    fetched_at TEXT NOT NULL,

    -- INTEGER 0/1: When video becomes unavailable anywhere, marks ALL duplicate instances
    is_available INTEGER NOT NULL DEFAULT 1 CHECK(is_available IN (0, 1)),

    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),

    FOREIGN KEY (content_source_id)
        REFERENCES content_sources(id)
        ON DELETE CASCADE
);

-- DESIGN DECISION: video_id is NOT UNIQUE across table
-- Same YouTube video can appear from multiple sources (duplicate rows)
-- When marked unavailable, ALL instances are marked (global availability)
CREATE INDEX idx_videos_video_id ON videos(video_id);
CREATE INDEX idx_videos_content_source ON videos(content_source_id);
CREATE INDEX idx_videos_duration ON videos(duration_seconds);
CREATE INDEX idx_videos_available ON videos(is_available);
CREATE INDEX idx_videos_channel ON videos(youtube_channel_id);
CREATE INDEX idx_videos_available_source ON videos(is_available, content_source_id);

-- =============================================================================
-- WATCH HISTORY
-- =============================================================================

CREATE TABLE IF NOT EXISTS watch_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- Denormalized video info (survives video deletion)
    video_id TEXT NOT NULL,
    video_title TEXT NOT NULL,
    channel_name TEXT NOT NULL,

    watched_at TEXT NOT NULL,

    -- INTEGER 0/1 flags
    completed INTEGER NOT NULL CHECK(completed IN (0, 1)),
    manual_play INTEGER NOT NULL DEFAULT 0 CHECK(manual_play IN (0, 1)),
    grace_play INTEGER NOT NULL DEFAULT 0 CHECK(grace_play IN (0, 1)),

    duration_watched_seconds INTEGER NOT NULL CHECK(duration_watched_seconds >= 0),

    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Index on DATE() function - queries MUST use DATE(watched_at) to benefit from this index
CREATE INDEX idx_watch_history_date ON watch_history(DATE(watched_at));
CREATE INDEX idx_watch_history_video ON watch_history(video_id);
CREATE INDEX idx_watch_history_watched_at ON watch_history(watched_at);
CREATE INDEX idx_watch_history_channel ON watch_history(channel_name);

-- Composite index for daily limit calculation
CREATE INDEX idx_watch_history_date_flags
    ON watch_history(DATE(watched_at), manual_play, grace_play);

-- =============================================================================
-- LIMIT WARNINGS (Story 4.2)
-- =============================================================================

CREATE TABLE IF NOT EXISTS limit_warnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    warning_type TEXT NOT NULL CHECK(warning_type IN ('10min', '5min', '2min')),
    shown_at TEXT NOT NULL,                    -- ISO 8601 UTC timestamp
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Index on DATE() function for daily queries
CREATE INDEX idx_limit_warnings_date ON limit_warnings(DATE(shown_at));
CREATE INDEX idx_limit_warnings_type ON limit_warnings(warning_type);

-- =============================================================================
-- BANNED VIDEOS
-- =============================================================================

CREATE TABLE IF NOT EXISTS banned_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    video_id TEXT NOT NULL UNIQUE,
    banned_at TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX idx_banned_videos_video_id ON banned_videos(video_id);

-- =============================================================================
-- SETTINGS
-- =============================================================================

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,                       -- JSON-encoded values
    updated_at TEXT NOT NULL,

    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- =============================================================================
-- API CALL LOG (Legacy - kept for compatibility)
-- =============================================================================

CREATE TABLE IF NOT EXISTS api_call_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    operation TEXT NOT NULL,
    quota_cost INTEGER NOT NULL CHECK(quota_cost > 0),

    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);

-- Index on DATE() function for daily aggregation
CREATE INDEX idx_api_log_date ON api_call_log(DATE(timestamp));

-- =============================================================================
-- API USAGE LOG (Story 1.2 - YouTube API Quota Tracking)
-- =============================================================================

CREATE TABLE IF NOT EXISTS api_usage_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_name TEXT NOT NULL,                    -- 'youtube_search', 'youtube_videos', etc.
    quota_cost INTEGER NOT NULL,               -- 100 for search, 1 for videos, etc.
    timestamp TEXT NOT NULL,                   -- ISO 8601 UTC format
    success INTEGER NOT NULL CHECK(success IN (0, 1)),  -- 1 = success, 0 = failure
    error_message TEXT,                        -- Error details if success=0

    CONSTRAINT chk_quota_cost CHECK (quota_cost > 0)
);

-- Index on DATE() function for daily quota aggregation
-- MUST use DATE(timestamp) in queries to benefit from this index
CREATE INDEX idx_api_usage_timestamp ON api_usage_log(DATE(timestamp));

-- =============================================================================
-- INITIAL DATA (JSON-encoded values)
-- =============================================================================

-- Default settings with proper JSON encoding
INSERT OR IGNORE INTO settings (key, value, updated_at) VALUES
    ('daily_limit_minutes', '30', datetime('now')),
    ('grid_size', '9', datetime('now')),
    ('audio_enabled', 'true', datetime('now')),
    ('admin_password_hash', '""', datetime('now'));

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Available videos view (excludes banned and unavailable)
-- Uses NOT EXISTS for better performance than NOT IN
CREATE VIEW IF NOT EXISTS available_videos AS
SELECT v.*
FROM videos v
WHERE v.is_available = 1
  AND NOT EXISTS (
      SELECT 1 FROM banned_videos b WHERE b.video_id = v.video_id
  );

-- Today's watch history (countable toward limit)
CREATE VIEW IF NOT EXISTS todays_countable_history AS
SELECT *
FROM watch_history
WHERE DATE(watched_at) = DATE('now')
  AND manual_play = 0
  AND grace_play = 0;

-- Daily stats view for admin dashboard
CREATE VIEW IF NOT EXISTS daily_stats AS
SELECT
    DATE(watched_at) as date,
    COUNT(*) as videos_watched,
    SUM(duration_watched_seconds) / 60 as minutes_watched,
    SUM(CASE WHEN manual_play = 1 THEN 1 ELSE 0 END) as manual_plays,
    SUM(CASE WHEN grace_play = 1 THEN 1 ELSE 0 END) as grace_plays
FROM watch_history
GROUP BY DATE(watched_at)
ORDER BY date DESC;

-- =============================================================================
-- TRIGGERS
-- =============================================================================

CREATE TRIGGER IF NOT EXISTS update_content_sources_timestamp
AFTER UPDATE ON content_sources
BEGIN
    UPDATE content_sources
    SET updated_at = datetime('now')
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_videos_timestamp
AFTER UPDATE ON videos
BEGIN
    UPDATE videos
    SET updated_at = datetime('now')
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_settings_timestamp
AFTER UPDATE ON settings
BEGIN
    UPDATE settings
    SET updated_at = datetime('now')
    WHERE key = NEW.key;
END;
