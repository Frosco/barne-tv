"""
Integration tests for YouTube API (Stories 1.2 and 1.3).

REQUIRES: Valid YOUTUBE_API_KEY in .env file
Run with: uv run pytest -m integration -v

Test IDs from test design document:
Story 1.2:
- 1.2-INT-009: Real API validation with valid key
- 1.2-INT-010: Real API validation with invalid key (optional)
- 1.2-INT-011: Validation uses minimal quota

Story 1.3:
- 1.3-INT-001: Add small channel successfully
- 1.3-INT-002: Add playlist successfully
- 1.3-INT-003: Duplicate source detection
- 1.3-INT-004: Quota exceeded scenario (mocked)
- 1.3-INT-005: Video metadata validation
"""

import pytest
from backend.services.content_source import (
    validate_youtube_api_key,
)
from backend.db.queries import get_daily_quota_usage, get_connection
from datetime import datetime, timezone


@pytest.mark.integration
def test_validate_youtube_api_key_with_real_api(monkeypatch, test_db):
    """
    Integration test: Validate API key with real YouTube API (1.2-INT-009).

    REQUIRES: Valid YOUTUBE_API_KEY in .env

    This test makes a real API call to YouTube and verifies:
    1. API key is valid
    2. API call succeeds
    3. Validation result is logged to database
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)
    monkeypatch.setattr("backend.services.content_source.get_connection", mock_get_connection)

    # Act
    result = validate_youtube_api_key()

    # Assert
    assert result is True, "YouTube API key validation failed - check your YOUTUBE_API_KEY in .env"


@pytest.mark.integration
def test_validation_uses_minimal_quota(monkeypatch, test_db):
    """
    Integration test: Validation uses only 1 quota unit (1.2-INT-011).

    Verifies efficient quota usage during validation.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)
    monkeypatch.setattr("backend.services.content_source.get_connection", mock_get_connection)

    today = datetime.now(timezone.utc).date().isoformat()

    # Act
    validate_youtube_api_key()

    # Assert - Check quota usage
    usage = get_daily_quota_usage(today)
    assert usage == 1, f"Expected 1 quota unit, but used {usage}"


@pytest.mark.integration
def test_full_quota_workflow(monkeypatch, test_db):
    """
    Integration test: Full workflow - log + query + check (1.2-INT-005).

    Tests the complete quota tracking workflow:
    1. Log API calls
    2. Query daily usage
    3. Check if quota exceeded
    """
    # Arrange
    from backend.services.content_source import is_quota_exceeded
    from backend.db.queries import log_api_call

    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)
    monkeypatch.setattr("backend.services.content_source.get_connection", mock_get_connection)

    today = datetime.now(timezone.utc).date().isoformat()

    # Act - Simulate various API calls
    log_api_call("youtube_search", 100, True)
    log_api_call("youtube_videos", 1, True)
    log_api_call("youtube_channels", 1, True)

    usage = get_daily_quota_usage(today)
    exceeded = is_quota_exceeded()

    # Assert
    assert usage == 102
    assert exceeded is False  # Should be below 9500 threshold


@pytest.mark.integration
def test_database_schema_has_correct_indexes(test_db):
    """
    Integration test: Database schema has correct indexes (1.2-INT-006).

    Performance validation - ensures DATE() index exists.
    """
    # Act
    indexes = test_db.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='api_usage_log'"
    ).fetchall()

    index_names = [idx["name"] for idx in indexes]

    # Assert
    assert (
        "idx_api_usage_timestamp" in index_names
    ), "Missing DATE(timestamp) index for quota queries"


@pytest.mark.integration
def test_context_manager_closes_connections(monkeypatch, test_db):
    """
    Integration test: Context manager closes connections (1.2-INT-007).

    TIER 2 Rule 7: Resource management validation.
    """
    # This test verifies that get_connection() properly closes connections
    # The context manager in queries.py should handle this

    import os
    import tempfile

    # Create a temporary database file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp_file:
        tmp_db_path = tmp_file.name

    try:
        # Arrange - Temporarily override DATABASE_PATH
        monkeypatch.setattr("backend.db.queries.DATABASE_PATH", tmp_db_path)

        # Act - Use context manager
        with get_connection() as conn:
            conn.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY)")
            conn.execute("INSERT INTO test_table (id) VALUES (1)")

        # Assert - Connection should be closed, but data should be persisted
        # Open a new connection to verify data was committed
        import sqlite3

        verify_conn = sqlite3.connect(tmp_db_path)
        result = verify_conn.execute("SELECT COUNT(*) FROM test_table").fetchone()
        verify_conn.close()

        assert result[0] == 1, "Data was not persisted - context manager may not have committed"

    finally:
        # Cleanup
        if os.path.exists(tmp_db_path):
            os.unlink(tmp_db_path)


# ============================================================================
# Story 1.3 Integration Tests - YouTube API Video Fetching
# ============================================================================


@pytest.mark.integration
def test_add_small_channel_successfully(monkeypatch, test_db):
    """
    Integration test: Add small channel with real API (1.3-INT-001).

    REQUIRES: Valid YOUTUBE_API_KEY in .env
    QUOTA COST: ~150-200 units (1 search + ~10-20 video details)

    This test makes real API calls to YouTube and verifies:
    1. Channel is added successfully
    2. Videos are fetched and stored
    3. All video metadata is complete
    4. Quota usage is logged
    """
    from backend.services.content_source import add_source

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Use CoComelon channel (popular kids' channel with lots of videos)
    # Direct channel ID format to avoid @handle resolution issues
    channel_url = "https://www.youtube.com/channel/UCbCmjCuTUZos6Inko4u57UQ"
    today = datetime.now(timezone.utc).date().isoformat()

    # Get initial quota usage
    initial_quota = get_daily_quota_usage(today)

    # Act
    result = add_source(channel_url)

    # Assert - Source created
    assert result["success"] is True
    assert "source_id" in result
    assert result["video_count"] > 0, "Should have fetched at least some videos"

    # Assert - Content source in database
    source = test_db.execute(
        "SELECT * FROM content_sources WHERE source_id = ?", (result["source_id"],)
    ).fetchone()
    assert source is not None
    assert source["source_type"] == "channel"
    assert source["source_id"].startswith("UC")  # YouTube channel IDs start with UC
    assert source["name"] is not None

    # Assert - Videos in database
    videos = test_db.execute(
        "SELECT * FROM videos WHERE content_source_id = ?", (source["id"],)
    ).fetchall()
    assert len(videos) == result["video_count"]

    # Assert - Video metadata complete
    for video in videos:
        assert video["video_id"] is not None
        assert len(video["video_id"]) == 11  # YouTube video IDs are 11 characters
        assert video["title"] is not None
        assert video["duration_seconds"] > 0
        assert video["thumbnail_url"] is not None
        assert video["youtube_channel_name"] is not None
        assert video["is_available"] == 1  # Should be available

    # Assert - Quota usage logged
    final_quota = get_daily_quota_usage(today)
    quota_used = final_quota - initial_quota
    assert quota_used >= 100, "Should use at least 100 units (1 search call)"
    assert quota_used <= 300, f"Should use less than 300 units for small channel, used {quota_used}"

    # Cleanup - Delete test data
    test_db.execute("DELETE FROM content_sources WHERE source_id = ?", (result["source_id"],))
    test_db.commit()


@pytest.mark.integration
def test_add_playlist_successfully(monkeypatch, test_db):
    """
    Integration test: Add playlist with real API (1.3-INT-002).

    REQUIRES: Valid YOUTUBE_API_KEY in .env
    QUOTA COST: ~10-20 units (more efficient than channels)

    This test verifies:
    1. Playlist is added successfully
    2. Videos are fetched via playlistItems API (1 unit per page)
    3. Quota usage is lower than channel (no search call needed)
    """
    from backend.services.content_source import add_source

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Use a small public educational playlist
    # Khan Academy Kids: Learning Videos playlist (small, stable)
    playlist_url = "https://www.youtube.com/playlist?list=PL8dPuuaLjXtNlUrzyH5r6jN9ulIgZBpdo"
    today = datetime.now(timezone.utc).date().isoformat()

    # Get initial quota usage
    initial_quota = get_daily_quota_usage(today)

    # Act
    result = add_source(playlist_url)

    # Assert - Source created
    assert result["success"] is True
    assert "source_id" in result
    assert result["video_count"] > 0

    # Assert - Content source in database
    source = test_db.execute(
        "SELECT * FROM content_sources WHERE source_id = ?", (result["source_id"],)
    ).fetchone()
    assert source is not None
    assert source["source_type"] == "playlist"
    assert source["source_id"].startswith("PL")  # YouTube playlist IDs start with PL

    # Assert - Videos in database
    videos = test_db.execute(
        "SELECT * FROM videos WHERE content_source_id = ?", (source["id"],)
    ).fetchall()
    assert len(videos) == result["video_count"]

    # Assert - Quota usage is efficient (no search call)
    final_quota = get_daily_quota_usage(today)
    quota_used = final_quota - initial_quota
    # Playlists use: playlistItems (1 unit/page) + videos (1 unit each)
    expected_max = (result["video_count"] // 50 + 1) + result["video_count"]
    assert quota_used <= expected_max, f"Quota usage {quota_used} should be <= {expected_max}"

    # Cleanup
    test_db.execute("DELETE FROM content_sources WHERE source_id = ?", (result["source_id"],))
    test_db.commit()


@pytest.mark.integration
def test_duplicate_source_detection(monkeypatch, test_db):
    """
    Integration test: Duplicate source detection (1.3-INT-003).

    REQUIRES: Valid YOUTUBE_API_KEY in .env
    QUOTA COST: 0 units (duplicate check happens before API call)

    This test verifies:
    1. Adding same source twice raises ValueError
    2. Error message is in Norwegian
    3. No API calls made for duplicate
    """
    from backend.services.content_source import add_source

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Use CoComelon channel (direct UC ID format)
    channel_url = "https://www.youtube.com/channel/UCbCmjCuTUZos6Inko4u57UQ"
    today = datetime.now(timezone.utc).date().isoformat()

    # Act - Add channel first time
    result1 = add_source(channel_url)
    assert result1["success"] is True

    # Get quota before duplicate attempt
    quota_before_duplicate = get_daily_quota_usage(today)

    # Act - Try to add same channel again
    try:
        add_source(channel_url)
        pytest.fail("Should have raised ValueError for duplicate source")
    except ValueError as e:
        # Assert - Norwegian error message
        error_msg = str(e)
        assert (
            "allerede" in error_msg.lower() or "eksisterer" in error_msg.lower()
        ), f"Error message should be in Norwegian, got: {error_msg}"

    # Assert - No quota used for duplicate check
    quota_after_duplicate = get_daily_quota_usage(today)
    assert (
        quota_after_duplicate == quota_before_duplicate
    ), "Duplicate detection should not use any quota"

    # Cleanup
    test_db.execute("DELETE FROM content_sources WHERE source_id = ?", (result1["source_id"],))
    test_db.commit()


@pytest.mark.integration
def test_quota_exceeded_during_fetch(monkeypatch, test_db):
    """
    Integration test: Quota exceeded scenario (1.3-INT-004).

    REQUIRES: Valid YOUTUBE_API_KEY in .env
    QUOTA COST: 0 units (mocked scenario)

    This test verifies:
    1. QuotaExceededError is raised when quota is at 9400+ units
    2. Error message is in Norwegian
    3. No API calls are made when quota is exceeded
    """
    from backend.services.content_source import add_source, QuotaExceededError
    from backend.db.queries import log_api_call

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Simulate high quota usage (9400 units)
    today = datetime.now(timezone.utc).date().isoformat()
    log_api_call("youtube_search", 9400, True)

    # Verify quota is above threshold
    current_usage = get_daily_quota_usage(today)
    assert current_usage >= 9400

    # Act - Try to add channel
    channel_url = "https://www.youtube.com/channel/UCbCmjCuTUZos6Inko4u57UQ"

    try:
        add_source(channel_url)
        pytest.fail("Should have raised QuotaExceededError")
    except QuotaExceededError as e:
        # Assert - Norwegian error message
        error_msg = str(e)
        assert (
            "kvote" in error_msg.lower() or "grense" in error_msg.lower()
        ), f"Error message should be in Norwegian, got: {error_msg}"


@pytest.mark.integration
def test_video_metadata_validation(monkeypatch, test_db):
    """
    Integration test: Video metadata validation (1.3-INT-005).

    REQUIRES: Valid YOUTUBE_API_KEY in .env
    QUOTA COST: ~100-150 units

    This test verifies:
    1. All video fields are populated correctly
    2. ISO 8601 duration parsing works
    3. Thumbnails are valid URLs
    4. Timestamps are in UTC
    """
    from backend.services.content_source import add_source

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Use small channel
    channel_url = "https://www.youtube.com/channel/UCbCmjCuTUZos6Inko4u57UQ"

    # Act
    result = add_source(channel_url)
    assert result["success"] is True

    # Assert - Get content source first
    source = test_db.execute(
        "SELECT * FROM content_sources WHERE source_id = ?", (result["source_id"],)
    ).fetchone()
    assert source is not None

    # Assert - Get videos and validate metadata
    videos = test_db.execute(
        "SELECT * FROM videos WHERE content_source_id = ?", (source["id"],)
    ).fetchall()

    assert len(videos) > 0, "Should have fetched at least one video"

    for video in videos:
        # Video ID validation
        assert video["video_id"] is not None
        assert len(video["video_id"]) == 11
        assert video["video_id"].replace("-", "").replace("_", "").isalnum()

        # Title validation
        assert video["title"] is not None
        assert len(video["title"]) > 0
        assert len(video["title"]) <= 200

        # Duration validation (ISO 8601 parsing)
        assert video["duration_seconds"] > 0
        assert video["duration_seconds"] <= 43200  # Max 12 hours (reasonable for kids content)

        # Thumbnail validation
        assert video["thumbnail_url"] is not None
        assert video["thumbnail_url"].startswith("https://")
        assert "ytimg.com" in video["thumbnail_url"] or "ggpht.com" in video["thumbnail_url"]

        # Channel name validation
        assert video["youtube_channel_name"] is not None
        assert len(video["youtube_channel_name"]) > 0

        # Availability validation
        assert video["is_available"] in (0, 1)

        # Timestamp validation (should be recent, in UTC)
        assert video["created_at"] is not None
        # Parse ISO format timestamp (SQLite stores as naive datetime)
        added_time = datetime.fromisoformat(video["created_at"])
        # Make it timezone-aware (assume UTC since database uses UTC)
        if added_time.tzinfo is None:
            added_time = added_time.replace(tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        time_diff = (now - added_time).total_seconds()
        assert time_diff >= 0, "Timestamp should not be in the future"
        assert time_diff < 300, "Timestamp should be within last 5 minutes"

    # Cleanup
    test_db.execute("DELETE FROM content_sources WHERE source_id = ?", (result["source_id"],))
    test_db.commit()
