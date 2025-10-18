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
        return result[0]
