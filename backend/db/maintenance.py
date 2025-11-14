"""
Database maintenance operations.
Can be run manually or scheduled via systemd timer.
"""

import logging

from backend.db.queries import get_connection

logger = logging.getLogger(__name__)


def cleanup_old_history(days_to_keep: int = 90) -> int:
    """
    Remove watch history older than N days.

    Args:
        days_to_keep: Number of days of history to retain

    Returns:
        Number of rows deleted
    """
    query = "DELETE FROM watch_history WHERE DATE(watched_at) < DATE('now', ?)"

    with get_connection() as conn:
        cursor = conn.execute(query, (f"-{days_to_keep} days",))
        count = int(cursor.rowcount)

    logger.info(f"Deleted {count} old watch history entries")
    return count


def cleanup_old_api_logs(days_to_keep: int = 30) -> int:
    """
    Remove API call logs older than N days.

    Args:
        days_to_keep: Number of days of logs to retain

    Returns:
        Number of rows deleted
    """
    query = "DELETE FROM api_call_log WHERE DATE(timestamp) < DATE('now', ?)"

    with get_connection() as conn:
        cursor = conn.execute(query, (f"-{days_to_keep} days",))
        count = int(cursor.rowcount)

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


if __name__ == "__main__":
    # Run all maintenance tasks
    cleanup_old_history(90)
    cleanup_old_api_logs(30)
    update_video_counts()
    checkpoint_wal()
    vacuum_database()
