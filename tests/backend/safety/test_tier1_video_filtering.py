"""
TIER 1 Child Safety Tests - Video Filtering (Story 2.1)

These tests verify adherence to TIER 1 safety rules for video grid filtering.
ALL TIER 1 tests MUST pass 100% before deployment.

Coverage Requirement: 100% for video filtering logic
"""

import pytest


# =============================================================================
# TIER 1 RULE 1: Video Selection Filtering (Story 2.1)
# =============================================================================


@pytest.mark.tier1
def test_rule1_banned_videos_never_appear_in_grid(test_db):
    """
    TIER 1 Rule 1: Banned videos must NEVER appear in video grid.

    Tests 50 times to verify randomness doesn't bypass filtering.

    Verifies:
    - Banned videos filtered from get_available_videos()
    - Filtering works across random selections
    - get_videos_for_grid() never returns banned videos
    """
    from backend.db.queries import get_connection, get_available_videos
    from backend.services.viewing_session import get_videos_for_grid

    # Add some videos to the test database
    with get_connection() as conn:
        # Add a content source (use unique ID to avoid conflicts with other tests)
        import uuid

        source_id_unique = f"UCtest_{uuid.uuid4().hex[:8]}"
        conn.execute(
            """INSERT INTO content_sources
               (source_id, source_type, name, video_count, last_refresh, fetch_method, added_at)
               VALUES (?, ?, ?, ?, datetime('now'), ?, datetime('now'))""",
            (source_id_unique, "channel", "Test Channel", 20, "api"),
        )
        source_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Add 20 videos with unique IDs
        video_ids_created = []
        for i in range(20):
            video_id = f"video_{i}_{uuid.uuid4().hex[:8]}"
            video_ids_created.append(video_id)
            conn.execute(
                """INSERT INTO videos
                   (video_id, title, content_source_id, youtube_channel_id, youtube_channel_name,
                    thumbnail_url, duration_seconds, published_at, fetched_at, is_available)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 1)""",
                (
                    video_id,
                    f"Test Video {i}",
                    source_id,
                    source_id_unique,
                    "Test Channel",
                    f"https://i.ytimg.com/vi/{video_id}/default.jpg",
                    300,
                ),
            )

        # Ban 5 videos (use the IDs we just created)
        banned_ids = [video_ids_created[i] for i in [1, 5, 10, 15, 19]]
        for video_id in banned_ids:
            conn.execute(
                "INSERT INTO banned_videos (video_id, banned_at) VALUES (?, datetime('now'))",
                (video_id,),
            )

    # Test 50 times to verify randomness doesn't bypass filtering
    for iteration in range(50):
        # Get available videos
        available = get_available_videos(exclude_banned=True)

        # Verify NO banned videos appear
        available_ids = {v["videoId"] for v in available}
        assert not any(
            banned_id in available_ids for banned_id in banned_ids
        ), f"Iteration {iteration}: Banned video found in available videos"

        # Also test through get_videos_for_grid
        videos, _ = get_videos_for_grid(9)
        grid_ids = {v["videoId"] for v in videos}
        assert not any(
            banned_id in grid_ids for banned_id in banned_ids
        ), f"Iteration {iteration}: Banned video found in grid"


@pytest.mark.tier1
def test_rule1_unavailable_videos_never_appear_in_grid(test_db):
    """
    TIER 1 Rule 1: Unavailable videos must NEVER appear in video grid.

    Tests 50 times to verify randomness doesn't bypass filtering.

    Verifies:
    - is_available=0 videos filtered from get_available_videos()
    - Filtering works across random selections
    - get_videos_for_grid() never returns unavailable videos
    """
    from backend.db.queries import get_connection, get_available_videos
    from backend.services.viewing_session import get_videos_for_grid

    # Add videos to test database
    with get_connection() as conn:
        # Add content source (use unique ID to avoid conflicts)
        import uuid

        source_id_unique = f"UCtest_{uuid.uuid4().hex[:8]}"
        conn.execute(
            """INSERT INTO content_sources
               (source_id, source_type, name, video_count, last_refresh, fetch_method, added_at)
               VALUES (?, ?, ?, ?, datetime('now'), ?, datetime('now'))""",
            (source_id_unique, "channel", "Test Channel 2", 20, "api"),
        )
        source_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Add 20 videos with unique IDs, mark 5 as unavailable
        unavailable_ids = []
        for i in range(20):
            is_available = 0 if i in [2, 7, 12, 16, 18] else 1
            video_id = f"video_unavail_{i}_{uuid.uuid4().hex[:8]}"
            if is_available == 0:
                unavailable_ids.append(video_id)

            conn.execute(
                """INSERT INTO videos
                   (video_id, title, content_source_id, youtube_channel_id, youtube_channel_name,
                    thumbnail_url, duration_seconds, published_at, fetched_at, is_available)
                   VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)""",
                (
                    video_id,
                    f"Test Video Unavail {i}",
                    source_id,
                    source_id_unique,
                    "Test Channel 2",
                    f"https://i.ytimg.com/vi/{video_id}/default.jpg",
                    300,
                    is_available,
                ),
            )

    # Test 50 times to verify randomness doesn't bypass filtering
    for iteration in range(50):
        # Get available videos
        available = get_available_videos(exclude_banned=True)

        # Verify NO unavailable videos appear
        available_ids = {v["videoId"] for v in available}
        assert not any(
            unavail_id in available_ids for unavail_id in unavailable_ids
        ), f"Iteration {iteration}: Unavailable video found in available videos"

        # Also test through get_videos_for_grid
        videos, _ = get_videos_for_grid(9)
        grid_ids = {v["videoId"] for v in videos}
        assert not any(
            unavail_id in grid_ids for unavail_id in unavailable_ids
        ), f"Iteration {iteration}: Unavailable video found in grid"


# =============================================================================
# TIER 1 RULE 2: Time Limit Calculation (Story 2.1)
# =============================================================================


@pytest.mark.tier1
def test_rule2_time_limits_exclude_manual_play_and_grace_play(tmp_path, monkeypatch):
    """
    TIER 1 Rule 2: Time limits must exclude manual_play and grace_play.

    Verifies:
    - manual_play=1 videos not counted in daily limit
    - grace_play=1 videos not counted in daily limit
    - Only manual_play=0 AND grace_play=0 count toward limit
    - get_daily_limit() returns correct minutes_watched
    """
    import sqlite3
    from pathlib import Path
    from datetime import datetime, timezone
    from backend.db.queries import get_connection, get_watch_history_for_date
    from backend.services.viewing_session import get_daily_limit

    # Set up isolated test database
    db_file = tmp_path / "test_tier1_rule2.db"
    monkeypatch.setattr("backend.config.DATABASE_PATH", str(db_file))
    monkeypatch.setattr("backend.db.queries.DATABASE_PATH", str(db_file))

    # Create database and load schema (includes default settings)
    conn = sqlite3.connect(str(db_file))
    schema_path = Path(__file__).parent.parent.parent.parent / "backend" / "db" / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())
    conn.close()

    # TIER 1 Rule 3: Use UTC for all date operations
    today = datetime.now(timezone.utc).date().isoformat()

    # Add watch history with different flag combinations
    with get_connection() as conn:
        # 10 minutes - counts toward limit (both flags 0)
        conn.execute(
            """INSERT INTO watch_history
               (video_id, video_title, channel_name, watched_at, completed,
                manual_play, grace_play, duration_watched_seconds)
               VALUES (?, ?, ?, datetime('now'), 1, 0, 0, ?)""",
            ("video_1", "Video 1", "Channel", 600),  # 10 minutes
        )

        # 5 minutes - manual_play=1, should NOT count
        conn.execute(
            """INSERT INTO watch_history
               (video_id, video_title, channel_name, watched_at, completed,
                manual_play, grace_play, duration_watched_seconds)
               VALUES (?, ?, ?, datetime('now'), 1, 1, 0, ?)""",
            ("video_2", "Video 2", "Channel", 300),  # 5 minutes
        )

        # 8 minutes - grace_play=1, should NOT count
        conn.execute(
            """INSERT INTO watch_history
               (video_id, video_title, channel_name, watched_at, completed,
                manual_play, grace_play, duration_watched_seconds)
               VALUES (?, ?, ?, datetime('now'), 1, 0, 1, ?)""",
            ("video_3", "Video 3", "Channel", 480),  # 8 minutes
        )

        # 7 minutes - both flags 1, should NOT count
        conn.execute(
            """INSERT INTO watch_history
               (video_id, video_title, channel_name, watched_at, completed,
                manual_play, grace_play, duration_watched_seconds)
               VALUES (?, ?, ?, datetime('now'), 1, 1, 1, ?)""",
            ("video_4", "Video 4", "Channel", 420),  # 7 minutes
        )

        # 12 minutes - counts toward limit (both flags 0)
        conn.execute(
            """INSERT INTO watch_history
               (video_id, video_title, channel_name, watched_at, completed,
                manual_play, grace_play, duration_watched_seconds)
               VALUES (?, ?, ?, datetime('now'), 1, 0, 0, ?)""",
            ("video_5", "Video 5", "Channel", 720),  # 12 minutes
        )

    # Verify get_watch_history_for_date excludes manual_play and grace_play
    history = get_watch_history_for_date(today)

    # Should only return 2 videos (video_1 and video_5)
    assert (
        len(history) == 2
    ), "Should only return countable history (manual_play=0 AND grace_play=0)"

    history_ids = {h["videoId"] for h in history}
    assert "video_1" in history_ids, "video_1 should be in countable history"
    assert "video_5" in history_ids, "video_5 should be in countable history"
    assert "video_2" not in history_ids, "video_2 (manual_play=1) should be excluded"
    assert "video_3" not in history_ids, "video_3 (grace_play=1) should be excluded"
    assert "video_4" not in history_ids, "video_4 (both flags=1) should be excluded"

    # Verify total duration (10 + 12 = 22 minutes)
    total_seconds = sum(h["durationWatchedSeconds"] for h in history)
    assert total_seconds == 1320, "Total should be 1320 seconds (22 minutes)"

    # Verify get_daily_limit calculates correctly
    daily_limit = get_daily_limit()

    # Should report 22 minutes watched (10 + 12), not 42 minutes (all videos)
    assert (
        daily_limit["minutesWatched"] == 22
    ), "Daily limit should only count manual_play=0 AND grace_play=0"
    assert daily_limit["minutesRemaining"] == 8, "Should have 8 minutes remaining (30 - 22)"
