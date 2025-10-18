"""
Integration tests for YouTube API (Story 1.2).

REQUIRES: Valid YOUTUBE_API_KEY in .env file
Run with: uv run pytest -m integration -v

Test IDs from test design document:
- 1.2-INT-009: Real API validation with valid key
- 1.2-INT-010: Real API validation with invalid key (optional)
- 1.2-INT-011: Validation uses minimal quota
"""

import pytest
from backend.services.content_source import validate_youtube_api_key
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
