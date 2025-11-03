"""
TIER 1 Safety Tests for Grace Video Logging (Story 4.3, Task 15).

These tests verify critical child safety rules around grace videos:
- Grace videos MUST be excluded from daily limit calculations (TIER 1 Rule 2)
- Grace videos MUST use SQL placeholders (TIER 1 Rule 6)
- Grace videos MUST use UTC timestamps (TIER 1 Rule 3)
- Grace mode MUST filter banned videos (TIER 1 Rule 1)

TIER 1 tests MUST pass before deployment.
Coverage requirement: 100% for safety-critical code.
"""

import pytest
from datetime import datetime, timezone

from backend.db.queries import (
    insert_watch_history,
    get_available_videos,
)
from backend.services.viewing_session import get_daily_limit
from tests.backend.conftest import (
    setup_content_source,
    create_test_video,
    setup_test_videos,
    ban_video,
)


@pytest.mark.tier1
def test_grace_video_excluded_from_daily_limit(test_db, monkeypatch):
    """
    TIER 1 Rule 2: Grace videos MUST NOT count toward daily limit.

    Verifies that grace_play=1 videos are excluded from time calculations.
    This is critical - if grace videos count, child gets less viewing time.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Insert watch history with mix of grace and normal plays
    # Normal plays: 10 minutes (should count)
    insert_watch_history(
        video_id="video1",
        completed=True,
        duration_watched_seconds=600,  # 10 minutes
        manual_play=False,
        grace_play=False,
    )

    # Grace play: 5 minutes (should NOT count)
    insert_watch_history(
        video_id="video2",
        completed=True,
        duration_watched_seconds=300,  # 5 minutes
        manual_play=False,
        grace_play=True,  # Grace video
    )

    # Manual play: 3 minutes (should NOT count)
    insert_watch_history(
        video_id="video3",
        completed=True,
        duration_watched_seconds=180,  # 3 minutes
        manual_play=True,
        grace_play=False,
    )

    # Act: Get daily limit
    limit = get_daily_limit()

    # Assert: Only normal play should count (10 minutes)
    assert limit["minutesWatched"] == 10, (
        f"Expected 10 minutes watched (grace and manual excluded), "
        f"got {limit['minutesWatched']}"
    )

    # Assert: Grace video did NOT inflate the count
    assert (
        limit["minutesRemaining"] == 20
    ), f"Expected 20 minutes remaining (30 - 10), got {limit['minutesRemaining']}"


@pytest.mark.tier1
def test_grace_video_uses_sql_placeholders(test_db, monkeypatch):
    """
    TIER 1 Rule 6: Grace video logging MUST use SQL placeholders.

    Verifies SQL injection prevention by attempting malicious video_id.
    If placeholders are not used, this test will fail or cause SQL errors.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Attempt SQL injection via malicious video_id
    malicious_video_id = "video1'; DROP TABLE watch_history; --"

    # Act: Insert watch history with malicious input
    # This should be safely parameterized and NOT execute the SQL injection
    try:
        insert_watch_history(
            video_id=malicious_video_id,
            completed=True,
            duration_watched_seconds=300,
            manual_play=False,
            grace_play=True,
        )
    except Exception as e:
        pytest.fail(f"SQL injection attempt caused error: {e}")

    # Assert: Watch history was safely inserted (table not dropped)
    # Note: We query directly because get_watch_history_for_date() excludes grace videos
    cursor = test_db.execute("SELECT * FROM watch_history")
    history = cursor.fetchall()
    assert len(history) == 1, "Watch history should have 1 entry"

    # Assert: Malicious video_id was safely stored as literal string
    assert (
        history[0]["video_id"] == malicious_video_id
    ), "Video ID should be stored literally (SQL injection prevented)"


@pytest.mark.tier1
def test_grace_video_uses_utc_timestamp(test_db, monkeypatch):
    """
    TIER 1 Rule 3: Grace videos MUST use UTC timestamps.

    Verifies that timestamps are in UTC, not local timezone.
    This is critical for midnight reset calculations.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Freeze time to a known UTC moment
    # Note: We can't mock datetime.now in the function, but we can verify the stored timestamp

    # Act: Insert grace video
    history = insert_watch_history(
        video_id="video1",
        completed=True,
        duration_watched_seconds=300,
        manual_play=False,
        grace_play=True,
    )

    # Assert: Timestamp should be ISO 8601 format with UTC indicator
    watched_at = history["watched_at"]
    assert "T" in watched_at, "Timestamp should be ISO 8601 format"

    # Assert: Parse timestamp and verify it's recent (within last minute)
    try:
        timestamp = datetime.fromisoformat(watched_at.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Invalid ISO 8601 timestamp format: {watched_at}")

    now = datetime.now(timezone.utc)
    time_diff = abs((now - timestamp).total_seconds())
    assert time_diff < 60, (
        f"Timestamp should be recent UTC time (within 60s), " f"but diff is {time_diff}s"
    )


@pytest.mark.tier1
def test_grace_mode_filters_banned_videos(test_db, monkeypatch):
    """
    TIER 1 Rule 1: Grace mode MUST filter banned videos.

    Verifies that banned videos are excluded from grace video selection.
    If banned videos appear in grace mode, child sees inappropriate content.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Create content source
    source_id = setup_content_source(
        test_db,
        source_id="UC_test",
        source_type="channel",
        name="Test Channel",
        video_count=3,
    )

    # Insert 3 videos (all short, suitable for grace mode)
    videos = [
        create_test_video(
            video_id="video1",
            title="Safe Video 1",
            content_source_id=source_id,
            youtube_channel_id="UC_test",
            youtube_channel_name="Test Channel",
            thumbnail_url="https://example.com/thumb1.jpg",
            duration_seconds=180,  # 3 minutes - fits grace mode
        ),
        create_test_video(
            video_id="video2",
            title="Safe Video 2",
            content_source_id=source_id,
            youtube_channel_id="UC_test",
            youtube_channel_name="Test Channel",
            thumbnail_url="https://example.com/thumb2.jpg",
            duration_seconds=240,  # 4 minutes - fits grace mode
        ),
        create_test_video(
            video_id="video3",
            title="Banned Video",
            content_source_id=source_id,
            youtube_channel_id="UC_test",
            youtube_channel_name="Test Channel",
            thumbnail_url="https://example.com/thumb3.jpg",
            duration_seconds=200,  # 3.3 minutes - fits grace mode
        ),
    ]
    setup_test_videos(test_db, videos)

    # Ban video3
    ban_video(test_db, video_id="video3")

    # Act: Get available videos for grace mode (max 5 minutes, exclude banned)
    available = get_available_videos(
        exclude_banned=True, max_duration_seconds=300  # 5 minutes grace mode limit
    )

    # Assert: Only 2 videos should be available (video3 is banned)
    assert len(available) == 2, f"Expected 2 videos (1 banned), got {len(available)}"

    # Assert: Banned video should NOT be in results
    video_ids = [v["videoId"] for v in available]
    assert "video3" not in video_ids, "Banned video 'video3' should NOT appear in grace mode"

    # Assert: Safe videos ARE in results
    assert "video1" in video_ids, "Safe video 'video1' should be available"
    assert "video2" in video_ids, "Safe video 'video2' should be available"


@pytest.mark.tier1
def test_grace_state_transitions(test_db, monkeypatch):
    """
    TIER 1 Safety: Verify grace state transitions are correct.

    Tests that grace state appears when limit reached and not consumed,
    and locked state appears when grace consumed.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Reach daily limit (30 minutes default)
    insert_watch_history(
        video_id="video1",
        completed=True,
        duration_watched_seconds=1800,  # 30 minutes - exactly at limit
        manual_play=False,
        grace_play=False,
    )

    # Act: Check state when limit reached, no grace consumed
    limit = get_daily_limit()

    # Assert: State should be "grace"
    assert (
        limit["currentState"] == "grace"
    ), f"Expected 'grace' state when limit reached, got '{limit['currentState']}'"
    assert limit["graceAvailable"] is True, "Grace should be available when not yet consumed"

    # Arrange: Consume grace video
    insert_watch_history(
        video_id="video2",
        completed=True,
        duration_watched_seconds=300,  # 5 minutes grace video
        manual_play=False,
        grace_play=True,
    )

    # Act: Check state after grace consumed
    limit = get_daily_limit()

    # Assert: State should be "locked"
    assert (
        limit["currentState"] == "locked"
    ), f"Expected 'locked' state after grace consumed, got '{limit['currentState']}'"
    assert limit["graceAvailable"] is False, "Grace should NOT be available after consumption"


@pytest.mark.tier1
def test_multiple_grace_plays_not_allowed(test_db, monkeypatch):
    """
    TIER 1 Safety: Verify only ONE grace video allowed per day.

    Tests that after first grace video, state becomes locked.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Reach limit and consume grace
    # Reach limit
    insert_watch_history(
        video_id="video1",
        completed=True,
        duration_watched_seconds=1800,  # 30 minutes
        manual_play=False,
        grace_play=False,
    )

    # First grace video
    insert_watch_history(
        video_id="video2",
        completed=True,
        duration_watched_seconds=300,
        manual_play=False,
        grace_play=True,
    )

    # Act: Try to get state (should be locked)
    limit = get_daily_limit()

    # Assert: State is locked, grace NOT available
    assert limit["currentState"] == "locked", "State should be locked after grace"
    assert limit["graceAvailable"] is False, "Grace should not be available"

    # Act: Attempt to log SECOND grace video (shouldn't be possible via UI, but test database)
    insert_watch_history(
        video_id="video3",
        completed=True,
        duration_watched_seconds=300,
        manual_play=False,
        grace_play=True,  # Second grace (shouldn't happen)
    )

    # Act: Check state again
    limit = get_daily_limit()

    # Assert: State remains locked (grace count should be >=1, so locked)
    assert limit["currentState"] == "locked", "State should remain locked"

    # Assert: Grace videos still don't count toward limit
    # Total watched should be 30 minutes (grace videos excluded)
    assert (
        limit["minutesWatched"] == 30
    ), f"Grace videos should not count, expected 30, got {limit['minutesWatched']}"
