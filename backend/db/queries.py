"""
Database query functions and connection management.

TIER 2 Rule 7: Always use context manager for database access.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from backend.config import DATABASE_PATH


@contextmanager
def get_connection():
    """
    Context manager for database connections.

    Usage:
        with get_connection() as conn:
            result = conn.execute("SELECT ...").fetchall()

    TIER 2 Rule 7: Always use context manager, even for reads.
    Provides automatic commit/rollback on errors.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    conn.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key constraints

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =============================================================================
# API QUOTA TRACKING (Story 1.2)
# =============================================================================


def log_api_call(
    api_name: str, quota_cost: int, success: bool, error_message: str | None = None
) -> None:
    """
    Log YouTube API call for quota tracking.

    TIER 1 Rules Applied:
    - Rule 3: Always use UTC for timestamps (datetime.now(timezone.utc))
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        api_name: Name of API operation (e.g., 'youtube_search', 'youtube_videos')
        quota_cost: Quota units consumed (e.g., 100 for search, 1 for videos)
        success: True if API call succeeded, False if failed
        error_message: Optional error message if success=False

    Example:
        log_api_call('youtube_search', 100, True)
        log_api_call('youtube_videos', 1, False, 'HTTP 403: quotaExceeded')
    """
    # TIER 1 Rule 3: Always use UTC for timestamps
    timestamp = datetime.now(timezone.utc).isoformat()

    # TIER 1 Rule 6: Always use SQL placeholders
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO api_usage_log
               (api_name, quota_cost, timestamp, success, error_message)
               VALUES (?, ?, ?, ?, ?)""",
            (api_name, quota_cost, timestamp, int(success), error_message),
        )


def get_daily_quota_usage(date: str) -> int:
    """
    Get total quota usage for a specific date (YYYY-MM-DD format).

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Args:
        date: ISO date string in YYYY-MM-DD format (e.g., '2025-10-18')

    Returns:
        Total quota units used on that date (0 if no usage)

    Example:
        today = datetime.now(timezone.utc).date().isoformat()
        usage = get_daily_quota_usage(today)
        print(f"Used {usage} quota units today")
    """
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COALESCE(SUM(quota_cost), 0) FROM api_usage_log WHERE DATE(timestamp) = ?",
            (date,),
        ).fetchone()
        return int(result[0])


# =============================================================================
# CONTENT SOURCE MANAGEMENT (Story 1.3)
# =============================================================================


def get_source_by_source_id(source_id: str) -> dict | None:
    """
    Get content source by YouTube source ID (channel or playlist ID).

    Used for duplicate detection before adding new sources.

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Args:
        source_id: YouTube channel ID or playlist ID

    Returns:
        Dict of source row if exists, None otherwise

    Example:
        existing = get_source_by_source_id('UC_x5XG1OV2P6uZZ5FSM9Ttw')
        if existing:
            print(f"Source already exists: {existing['name']}")
    """
    with get_connection() as conn:
        result = conn.execute(
            "SELECT * FROM content_sources WHERE source_id = ?", (source_id,)
        ).fetchone()
        return dict(result) if result else None


def insert_content_source(
    source_id: str,
    source_type: str,
    name: str,
    video_count: int,
    last_refresh: str,
    fetch_method: str,
    added_at: str,
) -> int:
    """
    Insert new content source (channel or playlist).

    TIER 1 Rules Applied:
    - Rule 3: Always use UTC for timestamps (caller must provide UTC timestamps)
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        source_id: YouTube channel ID or playlist ID
        source_type: 'channel' or 'playlist'
        name: Channel or playlist name
        video_count: Number of videos in source
        last_refresh: ISO 8601 UTC timestamp of last refresh
        fetch_method: 'api' (only supported method)
        added_at: ISO 8601 UTC timestamp when source was added

    Returns:
        ID of inserted content_sources row

    Example:
        now = datetime.now(timezone.utc).isoformat()
        source_id = insert_content_source(
            'UC_x5XG1OV2P6uZZ5FSM9Ttw',
            'channel',
            'Google Developers',
            150,
            now,
            'api',
            now
        )
    """
    # TIER 1 Rule 6: Always use SQL placeholders
    with get_connection() as conn:
        cursor = conn.execute(
            """INSERT INTO content_sources
               (source_id, source_type, name, video_count, last_refresh, fetch_method, added_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (source_id, source_type, name, video_count, last_refresh, fetch_method, added_at),
        )
        return int(cursor.lastrowid)


def bulk_insert_videos(content_source_id: int, videos: list[dict]) -> int:
    """
    Efficiently insert multiple videos using executemany().

    TIER 1 Rules Applied:
    - Rule 3: Always use UTC for timestamps (fetched_at, published_at in video dicts)
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        content_source_id: Foreign key to content_sources table
        videos: List of video dicts with keys:
            - video_id: YouTube video ID
            - title: Video title
            - youtube_channel_id: YouTube channel ID (denormalized)
            - youtube_channel_name: Channel name (denormalized)
            - thumbnail_url: Thumbnail URL
            - duration_seconds: Video duration in seconds
            - published_at: ISO 8601 UTC timestamp
            - fetched_at: ISO 8601 UTC timestamp

    Returns:
        Number of videos inserted

    Example:
        videos = [
            {
                'video_id': 'dQw4w9WgXcQ',
                'title': 'Never Gonna Give You Up',
                'youtube_channel_id': 'UCuAXFkgsw1L7xaCfnd5JJOw',
                'youtube_channel_name': 'Rick Astley',
                'thumbnail_url': 'https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg',
                'duration_seconds': 212,
                'published_at': '2009-10-25T06:57:33Z',
                'fetched_at': '2025-10-18T14:30:00Z'
            }
        ]
        count = bulk_insert_videos(source_id=1, videos=videos)
    """
    if not videos:
        return 0

    # TIER 1 Rule 6: Always use SQL placeholders
    # Convert list of dicts to list of tuples for executemany()
    video_tuples = [
        (
            video["video_id"],
            video["title"],
            content_source_id,
            video["youtube_channel_id"],
            video["youtube_channel_name"],
            video["thumbnail_url"],
            video["duration_seconds"],
            video["published_at"],
            video["fetched_at"],
            1,  # is_available defaults to 1 (True)
        )
        for video in videos
    ]

    with get_connection() as conn:
        conn.executemany(
            """INSERT INTO videos
               (video_id, title, content_source_id, youtube_channel_id, youtube_channel_name,
                thumbnail_url, duration_seconds, published_at, fetched_at, is_available)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            video_tuples,
        )

    return len(videos)


# =============================================================================
# SETTINGS MANAGEMENT (Story 1.4)
# =============================================================================


def get_setting(key: str) -> str:
    """
    Get a setting value from the settings table.

    Settings are stored as JSON-encoded strings. Caller is responsible
    for parsing the JSON value (e.g., json.loads() for complex values).

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Args:
        key: Setting key (e.g., 'admin_password_hash', 'daily_limit_minutes')

    Returns:
        JSON-encoded string value from settings table

    Raises:
        KeyError: If setting key does not exist

    Example:
        import json
        password_hash_json = get_setting('admin_password_hash')
        password_hash = json.loads(password_hash_json)  # Unwrap JSON encoding
    """
    with get_connection() as conn:
        result = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if result is None:
            raise KeyError(f"Setting '{key}' not found")
        return result[0]


def set_setting(key: str, value: str) -> None:
    """
    Update or insert a setting value in the settings table.

    Caller is responsible for JSON-encoding complex values before passing.

    TIER 1 Rules Applied:
    - Rule 3: Always use UTC for timestamps (datetime.now(timezone.utc))
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        key: Setting key
        value: JSON-encoded string value

    Example:
        import json
        from passlib.hash import bcrypt

        # Hash password and JSON-encode it
        hashed = bcrypt.hash("admin_password")
        json_value = json.dumps(hashed)
        set_setting('admin_password_hash', json_value)
    """
    # TIER 1 Rule 3: Always use UTC for timestamps
    updated_at = datetime.now(timezone.utc).isoformat()

    # TIER 1 Rule 6: Always use SQL placeholders
    with get_connection() as conn:
        # Use INSERT OR REPLACE for upsert behavior
        conn.execute(
            """INSERT OR REPLACE INTO settings (key, value, updated_at)
               VALUES (?, ?, ?)""",
            (key, value, updated_at),
        )
