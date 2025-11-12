# Database Schema

Complete SQL DDL for SQLite database with all tables, indexes, and constraints reflecting the simplified architecture and all edge case handling.

## Schema Overview

```
content_sources (8 rows typical)
    └─┬─> videos (4000+ rows)
         ├─> watch_history (100s of rows)
         └─> banned_videos (few rows)

settings (5-10 rows)
api_call_log (100s of rows)
```

## Full Schema Definition

```sql
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

-- Composite index for daily limit calculation
CREATE INDEX idx_watch_history_date_flags 
    ON watch_history(DATE(watched_at), manual_play, grace_play);

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
-- API CALL LOG
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
```

## Database Initialization Script

```python
# backend/db/init_db.py
"""
Database initialization script.
Run once on first setup or to reset database.
"""

import sqlite3
import json
import os
from pathlib import Path
import sys

DATABASE_PATH = os.getenv('DATABASE_PATH', '/opt/youtube-viewer/data/app.db')
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

def init_database():
    """Initialize database with schema."""
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DATABASE_PATH)
    
    # Enable WAL mode
    conn.execute("PRAGMA journal_mode=WAL")
    
    with open(SCHEMA_PATH) as f:
        schema_sql = f.read()
    
    conn.executescript(schema_sql)
    conn.commit()
    conn.close()
    
    print(f"Database initialized at {DATABASE_PATH}")

def set_admin_password(password: str):
    """Set initial admin password with proper JSON encoding."""
    import bcrypt

    password_bytes = password.encode('utf-8')
    hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
    hashed = hashed_bytes.decode('utf-8')

    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute(
        "UPDATE settings SET value = ?, updated_at = datetime('now') WHERE key = 'admin_password_hash'",
        (json.dumps(hashed),)  # Proper JSON encoding
    )
    conn.commit()
    conn.close()

    print("Admin password set")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Usage: python init_db.py <admin_password>")
        sys.exit(1)
    
    init_database()
    set_admin_password(sys.argv[1])
```

## Database Maintenance Script

```python
# backend/db/maintenance.py
"""
Database maintenance operations.
Can be run manually or scheduled via systemd timer.
"""

from backend.db.queries import get_connection
import logging

logger = logging.getLogger(__name__)

def cleanup_old_history(days_to_keep: int = 90) -> int:
    """
    Remove watch history older than N days.
    
    Returns:
        Number of rows deleted
    """
    query = "DELETE FROM watch_history WHERE DATE(watched_at) < DATE('now', ?)"
    
    with get_connection() as conn:
        cursor = conn.execute(query, (f'-{days_to_keep} days',))
        count = cursor.rowcount
    
    logger.info(f"Deleted {count} old watch history entries")
    return count

def cleanup_old_api_logs(days_to_keep: int = 30) -> int:
    """
    Remove API call logs older than N days.
    
    Returns:
        Number of rows deleted
    """
    query = "DELETE FROM api_call_log WHERE DATE(timestamp) < DATE('now', ?)"
    
    with get_connection() as conn:
        cursor = conn.execute(query, (f'-{days_to_keep} days',))
        count = cursor.rowcount
    
    logger.info(f"Deleted {count} old API log entries")
    return count

def update_video_counts():
    """Recalculate video counts for all sources."""
    query = """
        UPDATE content_sources 
        SET video_count = (
            SELECT COUNT(*) 
            FROM videos 
            WHERE content_source_id = content_sources.id
        ),
        updated_at = datetime('now')
    """
    
    with get_connection() as conn:
        conn.execute(query)
    
    logger.info("Updated video counts for all sources")

def vacuum_database():
    """Reclaim space and optimize database."""
    # VACUUM cannot run inside transaction
    import sqlite3
    from backend.db.queries import DATABASE_PATH
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("VACUUM")
    conn.close()
    
    logger.info("Database vacuumed")

def checkpoint_wal():
    """Checkpoint WAL file to main database."""
    import sqlite3
    from backend.db.queries import DATABASE_PATH
    
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA wal_checkpoint(FULL)")
    conn.close()
    
    logger.info("WAL checkpoint completed")

if __name__ == '__main__':
    # Run all maintenance tasks
    cleanup_old_history(90)
    cleanup_old_api_logs(30)
    update_video_counts()
    checkpoint_wal()
    vacuum_database()
```

## Sample Queries

```sql
-- Get videos for grid (wind-down mode, 8 minutes remaining)
SELECT * FROM available_videos
WHERE duration_seconds <= 480
ORDER BY RANDOM()
LIMIT 9;

-- Calculate today's minutes watched (excluding manual and grace)
-- Uses composite index: idx_watch_history_date_flags
SELECT SUM(duration_watched_seconds) / 60 as minutes
FROM watch_history
WHERE DATE(watched_at) = DATE('now')
  AND manual_play = 0
  AND grace_play = 0;

-- Get recently watched video IDs (last 24 hours)
SELECT DISTINCT video_id
FROM watch_history
WHERE watched_at > datetime('now', '-24 hours');

-- Mark video unavailable globally (affects ALL duplicate instances)
UPDATE videos 
SET is_available = 0, updated_at = datetime('now')
WHERE video_id = ?;

-- Reset daily limit (parent override)
DELETE FROM watch_history 
WHERE DATE(watched_at) = DATE('now');

-- Check if grace video already used today
SELECT COUNT(*) as grace_used
FROM watch_history
WHERE DATE(watched_at) = DATE('now')
  AND grace_play = 1;

-- Admin dashboard: Sources with accurate counts
SELECT 
    cs.*,
    COUNT(v.id) as actual_video_count,
    SUM(CASE WHEN v.is_available = 1 THEN 1 ELSE 0 END) as available_count
FROM content_sources cs
LEFT JOIN videos v ON v.content_source_id = cs.id
GROUP BY cs.id;
```

## Key Design Decisions

**1. No Unique Constraint on video_id**
- Same YouTube video can appear from multiple sources
- Simplifies source removal (CASCADE DELETE)
- Trade-off: Small storage overhead for duplicates

**2. Global Video Availability**
- When video marked unavailable, ALL duplicate instances marked
- If YouTube returns error, video is globally unavailable, not per-source
- Simplifies availability tracking

**3. Denormalized Data in watch_history**
- video_title and channel_name copied, not FKs
- History survives video/source deletion
- Parent can always see what was watched

**4. Three Boolean Flags for Watch Types**
```sql
completed       -- Did video play to end?
manual_play     -- Parent's "play again"? (doesn't count)
grace_play      -- Child's grace video? (doesn't count)
```

**5. Indexes for Performance**
- Most queries filter by: date, is_available, content_source_id
- Composite indexes cover common query patterns
- Daily limit calculation is fast: `idx_watch_history_date_flags`

**6. Views for Common Queries**
- `available_videos`: Excludes banned and unavailable (uses NOT EXISTS)
- `todays_countable_history`: Only videos that count toward limit
- `daily_stats`: Admin dashboard overview

**7. CASCADE DELETE Strategy**
```
content_sources deleted → videos CASCADE deleted
videos deleted → watch_history preserved (no FK)
```

**8. CHECK Constraints**
- Data integrity enforced at database level
- Prevents negative durations, invalid flags, etc.

**9. JSON-Encoded Settings**
- Consistent JSON encoding for all setting values
- Allows storing various data types in single table

**10. Functional Indexes**
- DATE() indexes require queries to use DATE() function
- Documented in schema for developer clarity

**11. SQLite WAL Mode**
- Better concurrency for reads
- Checkpoint before backup to ensure consistency

---

