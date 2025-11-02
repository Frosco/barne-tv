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


def get_all_content_sources() -> list[dict]:
    """
    Get all content sources ordered by most recently added first.

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Returns:
        List of source dicts with all fields

    Example:
        sources = get_all_content_sources()
        for source in sources:
            print(f"{source['name']}: {source['video_count']} videos")
    """
    with get_connection() as conn:
        results = conn.execute("SELECT * FROM content_sources ORDER BY added_at DESC").fetchall()
        return [dict(row) for row in results]


def get_source_by_id(id: int) -> dict | None:
    """
    Get content source by primary key ID.

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Args:
        id: Primary key of content_sources table

    Returns:
        Dict of source row if exists, None otherwise

    Example:
        source = get_source_by_id(3)
        if source:
            print(f"Found source: {source['name']}")
    """
    with get_connection() as conn:
        result = conn.execute("SELECT * FROM content_sources WHERE id = ?", (id,)).fetchone()
        return dict(result) if result else None


def delete_content_source(id: int) -> None:
    """
    Delete content source by ID.

    CASCADE DELETE will automatically remove all videos associated with
    this source due to foreign key constraint.

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Args:
        id: Primary key of content_sources table

    Example:
        delete_content_source(3)  # Deletes source and all its videos
    """
    with get_connection() as conn:
        conn.execute("DELETE FROM content_sources WHERE id = ?", (id,))


def update_content_source_refresh(id: int, last_refresh: str, video_count: int) -> None:
    """
    Update last_refresh timestamp and video_count after refreshing source.

    TIER 1 Rules Applied:
    - Rule 3: Caller must provide UTC timestamp for last_refresh
    - Rule 6: Always use SQL placeholders

    TIER 2 Rule 7: Always use context manager.

    Args:
        id: Primary key of content_sources table
        last_refresh: ISO 8601 UTC timestamp of refresh
        video_count: Updated video count

    Example:
        now = datetime.now(timezone.utc).isoformat()
        update_content_source_refresh(3, now, 487)
    """
    with get_connection() as conn:
        conn.execute(
            """UPDATE content_sources 
               SET last_refresh = ?, video_count = ?, updated_at = datetime('now')
               WHERE id = ?""",
            (last_refresh, video_count, id),
        )


def count_source_videos(content_source_id: int) -> int:
    """
    Count videos associated with a content source.

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Args:
        content_source_id: Primary key of content_sources table

    Returns:
        Number of videos associated with this source

    Example:
        count = count_source_videos(3)
        print(f"Source has {count} videos")
    """
    with get_connection() as conn:
        result = conn.execute(
            "SELECT COUNT(*) FROM videos WHERE content_source_id = ?", (content_source_id,)
        ).fetchone()
        return int(result[0])


def get_source_video_ids(content_source_id: int) -> set[str]:
    """
    Get all video IDs associated with a content source.

    Returns a set for efficient membership testing when filtering new videos.

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Args:
        content_source_id: Primary key of content_sources table

    Returns:
        Set of video_id strings

    Example:
        existing_ids = get_source_video_ids(3)
        new_ids = [vid for vid in fetched_ids if vid not in existing_ids]
    """
    with get_connection() as conn:
        results = conn.execute(
            "SELECT video_id FROM videos WHERE content_source_id = ?", (content_source_id,)
        ).fetchall()
        return {row["video_id"] for row in results}


# =============================================================================
# VIDEO SELECTION (Story 2.1)
# =============================================================================


def get_available_videos(
    exclude_banned: bool = True, max_duration_seconds: int | None = None, conn=None
) -> list[dict]:
    """
    Fetch available videos with optional filtering.

    TIER 1 Rules Applied:
    - Rule 1: ALWAYS filter banned and unavailable videos
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        exclude_banned: If True, filter out banned videos (default True)
        max_duration_seconds: If provided, filter videos by maximum duration (for wind-down mode)
        conn: Optional database connection (for testing). If None, creates new connection.

    Returns:
        List of video dicts with camelCase keys for frontend consistency

    Example:
        # Get all available videos
        videos = get_available_videos()

        # Get available videos for wind-down mode (max 5 minutes)
        wind_down_videos = get_available_videos(max_duration_seconds=300)
    """
    # TIER 1 Rule 1: ALWAYS filter unavailable videos
    query = """
        SELECT video_id, title, youtube_channel_name, thumbnail_url, duration_seconds
        FROM videos
        WHERE is_available = 1
    """

    params = []

    # TIER 1 Rule 1: ALWAYS filter banned videos when exclude_banned=True
    if exclude_banned:
        query += " AND video_id NOT IN (SELECT video_id FROM banned_videos)"

    # Filter by duration for wind-down mode
    if max_duration_seconds is not None:
        query += " AND duration_seconds <= ?"
        params.append(max_duration_seconds)

    # TIER 1 Rule 6: Use SQL placeholders
    if conn is not None:
        # For testing: use provided connection
        if params:
            results = conn.execute(query, tuple(params)).fetchall()
        else:
            results = conn.execute(query).fetchall()
    else:
        # TIER 2 Rule 7: Always use context manager for production
        with get_connection() as conn:
            if params:
                results = conn.execute(query, tuple(params)).fetchall()
            else:
                results = conn.execute(query).fetchall()

    # Convert to list of dicts with camelCase keys for frontend
    videos = []
    for row in results:
        videos.append(
            {
                "videoId": row["video_id"],
                "title": row["title"],
                "youtubeChannelName": row["youtube_channel_name"],
                "thumbnailUrl": row["thumbnail_url"],
                "durationSeconds": row["duration_seconds"],
            }
        )

    return videos


def get_watch_history_for_date(date: str, conn=None) -> list[dict]:
    """
    Get watch history for a specific date, excluding manual_play and grace_play.

    TIER 1 Rules Applied:
    - Rule 2: ALWAYS exclude manual_play and grace_play from countable history
    - Rule 3: Use UTC dates for all date operations
    - Rule 6: Always use SQL placeholders

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        date: ISO date string in YYYY-MM-DD format (UTC)
        conn: Optional database connection (for testing). If None, creates new connection.

    Returns:
        List of watch history dicts for the specified date

    Example:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        history = get_watch_history_for_date(today)
        minutes_watched = sum(h['duration_watched_seconds'] for h in history) / 60
    """
    # TIER 1 Rule 2: ALWAYS exclude manual_play and grace_play
    # TIER 1 Rule 3: Use UTC dates
    query = """
        SELECT video_id, video_title, channel_name, watched_at,
               duration_watched_seconds, completed
        FROM watch_history
        WHERE DATE(watched_at) = ?
        AND manual_play = 0
        AND grace_play = 0
    """

    # If connection provided (testing), use it directly
    if conn is not None:
        # TIER 1 Rule 6: Use SQL placeholders
        results = conn.execute(query, (date,)).fetchall()
    else:
        # TIER 2 Rule 7: Always use context manager for production
        with get_connection() as conn:
            # TIER 1 Rule 6: Use SQL placeholders
            results = conn.execute(query, (date,)).fetchall()

    # Convert to list of dicts with camelCase keys
    history = []
    for row in results:
        history.append(
            {
                "videoId": row["video_id"],
                "videoTitle": row["video_title"],
                "channelName": row["channel_name"],
                "watchedAt": row["watched_at"],
                "durationWatchedSeconds": row["duration_watched_seconds"],
                "completed": bool(row["completed"]),
            }
        )

    return history


def check_grace_consumed(date: str, conn=None) -> bool:
    """
    Check if a grace video has been consumed for a specific date.

    TIER 1 Rules Applied:
    - Rule 2: Grace videos marked with grace_play=1
    - Rule 6: Use SQL placeholders

    TIER 2 Rule 7: Always use context manager.

    Args:
        date: Date string in YYYY-MM-DD format (UTC)
        conn: Optional database connection (for testing). If None, creates new connection.

    Returns:
        True if a grace video (grace_play=1) exists for the date, False otherwise

    Example:
        # Check if grace consumed today
        today = datetime.now(timezone.utc).date().isoformat()
        is_locked = check_grace_consumed(today)
    """
    query = """
        SELECT COUNT(*) as count
        FROM watch_history
        WHERE DATE(watched_at) = ?
        AND grace_play = 1
    """

    if conn:
        # For testing: use provided connection
        result = conn.execute(query, (date,)).fetchone()
    else:
        # TIER 2 Rule 7: Always use context manager for production
        with get_connection() as conn:
            result = conn.execute(query, (date,)).fetchone()

    return result["count"] > 0


# =============================================================================
# SETTINGS MANAGEMENT (Story 1.4)
# =============================================================================


def get_setting(key: str, conn=None) -> str:
    """
    Get a setting value from the settings table.

    Settings are stored as JSON-encoded strings. Caller is responsible
    for parsing the JSON value (e.g., json.loads() for complex values).

    TIER 1 Rule 6: Always use SQL placeholders.
    TIER 2 Rule 7: Always use context manager.

    Args:
        key: Setting key (e.g., 'admin_password_hash', 'daily_limit_minutes')
        conn: Optional database connection (for testing). If None, creates new connection.

    Returns:
        JSON-encoded string value from settings table

    Raises:
        KeyError: If setting key does not exist

    Example:
        import json
        password_hash_json = get_setting('admin_password_hash')
        password_hash = json.loads(password_hash_json)  # Unwrap JSON encoding
    """
    if conn is not None:
        result = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
        if result is None:
            raise KeyError(f"Setting '{key}' not found")
        return result[0]
    else:
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
        import bcrypt

        # Hash password and JSON-encode it
        password_bytes = "admin_password".encode('utf-8')
        hashed_bytes = bcrypt.hashpw(password_bytes, bcrypt.gensalt())
        hashed = hashed_bytes.decode('utf-8')
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


# =============================================================================
# WATCH HISTORY TRACKING (Story 2.2)
# =============================================================================


def insert_watch_history(
    video_id: str,
    completed: bool,
    duration_watched_seconds: int,
    manual_play: bool = False,
    grace_play: bool = False,
) -> dict:
    """
    Insert watch history record for video playback tracking.

    TIER 1 Rules Applied:
    - Rule 2: manual_play and grace_play default to False for normal child playback
    - Rule 3: Always use UTC for timestamps (datetime.now(timezone.utc))
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        video_id: YouTube video ID (11 characters)
        completed: True if video played to end, False if interrupted
        duration_watched_seconds: Actual watch time in seconds
        manual_play: True if parent "Play Again", False if child selection (default False)
        grace_play: True if grace video, False if normal (default False)

    Returns:
        Dict of inserted watch_history row

    Example:
        # Normal child playback (counts toward limit)
        history = insert_watch_history('dQw4w9WgXcQ', completed=True, duration_watched_seconds=212)

        # Partial watch (back button pressed after 45 seconds)
        history = insert_watch_history('abc123def45', completed=False, duration_watched_seconds=45)

        # Parent "Play Again" (doesn't count toward limit)
        history = insert_watch_history('xyz789abc12', completed=True, duration_watched_seconds=180, manual_play=True)
    """
    # TIER 1 Rule 3: Always use UTC for timestamps
    watched_at = datetime.now(timezone.utc).isoformat()

    # Denormalize video title and channel name from videos table
    # Get first matching video (any duplicate instance is fine)
    with get_connection() as conn:
        video = conn.execute(
            "SELECT title, youtube_channel_name FROM videos WHERE video_id = ? LIMIT 1",
            (video_id,),
        ).fetchone()

        if not video:
            # If video not in database, use placeholder values
            video_title = "Unknown Video"
            channel_name = "Unknown Channel"
        else:
            video_title = video["title"]
            channel_name = video["youtube_channel_name"]

        # TIER 1 Rule 6: Always use SQL placeholders
        # TIER 1 Rule 2: manual_play and grace_play default to False
        cursor = conn.execute(
            """INSERT INTO watch_history
               (video_id, video_title, channel_name, watched_at, completed,
                manual_play, grace_play, duration_watched_seconds)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                video_id,
                video_title,
                channel_name,
                watched_at,
                int(completed),
                int(manual_play),
                int(grace_play),
                duration_watched_seconds,
            ),
        )

        # Fetch and return the inserted row
        history_id = cursor.lastrowid
        result = conn.execute("SELECT * FROM watch_history WHERE id = ?", (history_id,)).fetchone()

        return dict(result)


def update_video_availability(video_id: str, is_available: bool = False) -> int:
    """
    Mark video as unavailable (or available) globally across ALL duplicate instances.

    TIER 1 Rules Applied:
    - Rule 1: When video becomes unavailable, marks ALL duplicate instances globally
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        video_id: YouTube video ID (11 characters)
        is_available: False to mark unavailable (default), True to mark available

    Returns:
        Number of video rows updated (could be multiple duplicates)

    Example:
        # Mark video unavailable after YouTube error 100/150
        count = update_video_availability('dQw4w9WgXcQ', is_available=False)
        print(f"Marked {count} duplicate instances as unavailable")

        # Restore video availability (rare)
        count = update_video_availability('abc123def45', is_available=True)
    """
    # TIER 1 Rule 6: Always use SQL placeholders
    # TIER 1 Rule 1: Update ALL duplicate instances globally
    with get_connection() as conn:
        cursor = conn.execute(
            "UPDATE videos SET is_available = ? WHERE video_id = ?",
            (int(is_available), video_id),
        )
        return cursor.rowcount


# =============================================================================
# DAILY LIMIT MANAGEMENT (Story 4.1)
# =============================================================================


def delete_todays_countable_history(date: str, conn=None) -> int:
    """
    Delete today's countable watch history entries (for parent limit reset).

    TIER 1 Rules Applied:
    - Rule 2: Only delete entries where manual_play=0 AND grace_play=0
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        date: ISO date string in YYYY-MM-DD format (UTC)
        conn: Optional database connection (for testing). If None, creates new connection.

    Returns:
        Number of watch_history rows deleted

    Example:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        count = delete_todays_countable_history(today)
        print(f"Deleted {count} countable watch history entries")
    """
    # TIER 1 Rule 2: Only delete countable entries (manual_play=0 AND grace_play=0)
    # TIER 1 Rule 6: Always use SQL placeholders
    query = """
        DELETE FROM watch_history
        WHERE DATE(watched_at) = ?
        AND manual_play = 0
        AND grace_play = 0
    """

    if conn is not None:
        # For testing: use provided connection
        cursor = conn.execute(query, (date,))
        return cursor.rowcount
    else:
        # TIER 2 Rule 7: Always use context manager for production
        with get_connection() as conn:
            cursor = conn.execute(query, (date,))
            return cursor.rowcount


# =============================================================================
# LIMIT WARNINGS (Story 4.2)
# =============================================================================


def log_warning(warning_type: str, shown_at: str, conn=None) -> None:
    """
    Log a limit warning when shown to child.

    TIER 1 Rules Applied:
    - Rule 3: Always use UTC for timestamps (shown_at must be UTC)
    - Rule 6: Always use SQL placeholders (never string formatting)

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        warning_type: Type of warning ('10min', '5min', '2min')
        shown_at: ISO 8601 UTC timestamp when warning was shown
        conn: Optional database connection (for testing). If None, creates new connection.

    Example:
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).isoformat()
        log_warning('10min', now)
    """
    # TIER 1 Rule 6: Always use SQL placeholders
    if conn is not None:
        # For testing: use provided connection
        conn.execute(
            """INSERT INTO limit_warnings (warning_type, shown_at)
               VALUES (?, ?)""",
            (warning_type, shown_at),
        )
        conn.commit()
    else:
        # TIER 2 Rule 7: Always use context manager for production
        with get_connection() as conn:
            conn.execute(
                """INSERT INTO limit_warnings (warning_type, shown_at)
                   VALUES (?, ?)""",
                (warning_type, shown_at),
            )


def get_warnings_for_date(date: str, conn=None) -> list[dict]:
    """
    Get all limit warnings for a specific date.

    TIER 1 Rules Applied:
    - Rule 3: Use UTC dates for all date operations
    - Rule 6: Always use SQL placeholders

    TIER 2 Rule 7: Always use context manager for database access.

    Args:
        date: ISO date string in YYYY-MM-DD format (UTC)
        conn: Optional database connection (for testing). If None, creates new connection.

    Returns:
        List of warning dicts with camelCase keys for frontend consistency

    Example:
        from datetime import datetime, timezone
        today = datetime.now(timezone.utc).date().isoformat()
        warnings = get_warnings_for_date(today)
        for warning in warnings:
            print(f"{warning['warningType']} shown at {warning['shownAt']}")
    """
    # TIER 1 Rule 6: Always use SQL placeholders
    if conn is not None:
        # For testing: use provided connection
        results = conn.execute(
            """SELECT warning_type, shown_at, created_at
               FROM limit_warnings
               WHERE DATE(shown_at) = ?
               ORDER BY shown_at ASC""",
            (date,),
        ).fetchall()
    else:
        # TIER 2 Rule 7: Always use context manager for production
        with get_connection() as conn:
            results = conn.execute(
                """SELECT warning_type, shown_at, created_at
                   FROM limit_warnings
                   WHERE DATE(shown_at) = ?
                   ORDER BY shown_at ASC""",
                (date,),
            ).fetchall()

    # Convert to list of dicts with camelCase keys
    warnings = []
    for row in results:
        warnings.append(
            {
                "warningType": row["warning_type"],
                "shownAt": row["shown_at"],
                "createdAt": row["created_at"],
            }
        )

    return warnings
