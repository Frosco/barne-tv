"""
Backend test fixtures and utilities.

Provides pytest fixtures for database testing and helper functions for
setting up test data.
"""

import sqlite3
from pathlib import Path
from datetime import datetime, timezone
import pytest


@pytest.fixture
def test_db():
    """
    Create in-memory test database with full schema.

    Yields a SQLite connection with the complete database schema loaded.
    Database is automatically cleaned up after test completes.

    Usage:
        def test_something(test_db):
            cursor = test_db.execute("SELECT * FROM videos")
            assert cursor.fetchall() == []
    """
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Load and execute schema
    schema_path = Path(__file__).parent.parent.parent / "backend" / "db" / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    yield conn

    conn.close()


def create_test_video(
    video_id: str = "test_video_001",
    title: str = "Test Video",
    content_source_id: int = 1,
    youtube_channel_id: str = "UCtest",
    youtube_channel_name: str = "Test Channel",
    thumbnail_url: str = "https://example.com/thumb.jpg",
    duration_seconds: int = 300,
    published_at: str | None = None,
    fetched_at: str | None = None,
    is_available: int = 1,
) -> dict:
    """
    Generate a test video dictionary with sensible defaults.

    Args:
        video_id: YouTube video ID
        title: Video title
        content_source_id: Foreign key to content_sources
        youtube_channel_id: YouTube channel ID
        youtube_channel_name: Channel name
        thumbnail_url: Thumbnail URL
        duration_seconds: Video duration in seconds
        published_at: ISO 8601 timestamp (UTC)
        fetched_at: ISO 8601 timestamp (UTC)
        is_available: 1 (available) or 0 (unavailable)

    Returns:
        Dictionary with all required fields for videos table
    """
    now = datetime.now(timezone.utc).isoformat()
    return {
        "video_id": video_id,
        "title": title,
        "content_source_id": content_source_id,
        "youtube_channel_id": youtube_channel_id,
        "youtube_channel_name": youtube_channel_name,
        "thumbnail_url": thumbnail_url,
        "duration_seconds": duration_seconds,
        "published_at": published_at or now,
        "fetched_at": fetched_at or now,
        "is_available": is_available,
    }


def setup_test_videos(conn: sqlite3.Connection, videos: list[dict]) -> None:
    """
    Insert multiple test videos into the database.

    Args:
        conn: SQLite connection
        videos: List of video dictionaries (from create_test_video)

    Example:
        setup_test_videos(test_db, [
            create_test_video(video_id="vid1", title="Video 1"),
            create_test_video(video_id="vid2", title="Video 2"),
        ])
    """
    for video in videos:
        conn.execute(
            """
            INSERT INTO videos (
                video_id, title, content_source_id,
                youtube_channel_id, youtube_channel_name,
                thumbnail_url, duration_seconds,
                published_at, fetched_at, is_available
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                video["video_id"],
                video["title"],
                video["content_source_id"],
                video["youtube_channel_id"],
                video["youtube_channel_name"],
                video["thumbnail_url"],
                video["duration_seconds"],
                video["published_at"],
                video["fetched_at"],
                video["is_available"],
            ),
        )
    conn.commit()


def ban_video(conn: sqlite3.Connection, video_id: str) -> None:
    """
    Add a video to the banned_videos table.

    Args:
        conn: SQLite connection
        video_id: YouTube video ID to ban

    Example:
        ban_video(test_db, "dangerous_video_123")
    """
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        "INSERT INTO banned_videos (video_id, banned_at) VALUES (?, ?)",
        (video_id, now),
    )
    conn.commit()


def insert_watch_history(conn: sqlite3.Connection, records: list[dict]) -> None:
    """
    Insert watch history records into the database.

    Args:
        conn: SQLite connection
        records: List of watch history dictionaries

    Example:
        insert_watch_history(test_db, [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": "2025-10-08T10:00:00+00:00",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300
            }
        ])
    """
    for record in records:
        conn.execute(
            """
            INSERT INTO watch_history (
                video_id, video_title, channel_name,
                watched_at, completed, manual_play, grace_play,
                duration_watched_seconds
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                record["video_id"],
                record["video_title"],
                record["channel_name"],
                record["watched_at"],
                record["completed"],
                record.get("manual_play", 0),
                record.get("grace_play", 0),
                record["duration_watched_seconds"],
            ),
        )
    conn.commit()


def setup_content_source(
    conn: sqlite3.Connection,
    source_id: str = "UCtest",
    source_type: str = "channel",
    name: str = "Test Channel",
    video_count: int = 0,
) -> int:
    """
    Insert a content source and return its ID.

    Args:
        conn: SQLite connection
        source_id: YouTube channel or playlist ID
        source_type: 'channel' or 'playlist'
        name: Human-readable name
        video_count: Number of videos from this source

    Returns:
        Integer ID of the inserted content source

    Example:
        source_id = setup_content_source(test_db, "UCblippi", "channel", "Blippi")
    """
    now = datetime.now(timezone.utc).isoformat()
    cursor = conn.execute(
        """
        INSERT INTO content_sources (
            source_id, source_type, name, video_count,
            last_refresh, fetch_method, added_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (source_id, source_type, name, video_count, now, "api", now),
    )
    conn.commit()
    return cursor.lastrowid
