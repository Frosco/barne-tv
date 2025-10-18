"""
Unit tests for database query functions (Story 1.2 - Quota Tracking).

TIER 1 Safety Tests: 100% coverage required for quota tracking functions.

Test IDs from test design document:
- 1.2-UNIT-004 through 1.2-UNIT-011
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.db.queries import log_api_call, get_daily_quota_usage


# =============================================================================
# log_api_call() Tests
# =============================================================================


def test_log_api_call_inserts_correct_data(test_db, monkeypatch):
    """
    Test that log_api_call() inserts data correctly (1.2-UNIT-004).

    TIER 1 Safety Test - Must pass 100%
    """
    # Arrange
    api_name = "youtube_search"
    quota_cost = 100
    success = True

    # Mock get_connection to use test_db
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Act
    log_api_call(api_name, quota_cost, success)

    # Assert
    result = test_db.execute(
        "SELECT api_name, quota_cost, success FROM api_usage_log WHERE api_name = ?",
        (api_name,),
    ).fetchone()

    assert result is not None
    assert result["api_name"] == "youtube_search"
    assert result["quota_cost"] == 100
    assert result["success"] == 1


@pytest.mark.tier1
def test_log_api_call_uses_utc_timestamps(test_db, monkeypatch):
    """
    Test that log_api_call() uses UTC timestamps (1.2-UNIT-005).

    TIER 1 Rule 3: Always use UTC for timestamps.
    Critical for DATA-002 risk mitigation.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Act
    log_api_call("youtube_search", 100, True)

    # Assert
    result = test_db.execute(
        "SELECT timestamp FROM api_usage_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    timestamp = result["timestamp"]

    # ISO 8601 with UTC indicator (either +00:00 or Z)
    assert timestamp.endswith("+00:00") or timestamp.endswith(
        "Z"
    ), f"Timestamp must use UTC, got: {timestamp}"


def test_log_api_call_handles_null_error_message(test_db, monkeypatch):
    """
    Test that log_api_call() handles NULL error_message (1.2-UNIT-006).

    Error message is optional (only for failed calls).
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Act
    log_api_call("youtube_videos", 1, True, error_message=None)

    # Assert
    result = test_db.execute(
        "SELECT error_message FROM api_usage_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    assert result["error_message"] is None


@pytest.mark.tier1
def test_log_api_call_uses_sql_placeholders(test_db, monkeypatch):
    """
    Test that log_api_call() uses SQL placeholders (1.2-UNIT-007).

    TIER 1 Rule 6: SQL injection prevention.
    Tests that malicious input doesn't execute as SQL.
    """
    # Arrange
    malicious_api_name = "youtube_search'; DROP TABLE api_usage_log; --"

    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Act
    log_api_call(malicious_api_name, 100, True)

    # Assert - table should still exist and contain the malicious string as data
    result = test_db.execute("SELECT COUNT(*) FROM api_usage_log").fetchone()
    assert result[0] == 1

    # Verify the malicious string was stored as data, not executed as SQL
    result = test_db.execute(
        "SELECT api_name FROM api_usage_log WHERE api_name = ?", (malicious_api_name,)
    ).fetchone()
    assert result is not None
    assert result["api_name"] == malicious_api_name


# =============================================================================
# get_daily_quota_usage() Tests
# =============================================================================


@pytest.mark.tier1
def test_get_daily_quota_usage_returns_correct_sum(test_db, monkeypatch):
    """
    Test that get_daily_quota_usage() sums correctly (1.2-UNIT-008).

    TIER 1 Safety Test - Critical for quota enforcement.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    today = datetime.now(timezone.utc).date().isoformat()

    # Insert test data
    log_api_call("youtube_search", 100, True)
    log_api_call("youtube_videos", 1, True)
    log_api_call("youtube_search", 100, True)

    # Act
    usage = get_daily_quota_usage(today)

    # Assert
    assert usage == 201


@pytest.mark.tier1
def test_get_daily_quota_usage_excludes_previous_days(test_db, monkeypatch):
    """
    Test that quota calculation excludes previous days (1.2-UNIT-009).

    TIER 1 Safety Test - Critical for DATA-002 risk (UTC timezone handling).
    This is THE critical test for preventing limit bypass.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    today = datetime.now(timezone.utc).date().isoformat()
    yesterday = (datetime.now(timezone.utc).date() - timedelta(days=1)).isoformat()

    # Insert yesterday's usage (should be excluded)
    test_db.execute(
        """INSERT INTO api_usage_log
           (api_name, quota_cost, timestamp, success)
           VALUES (?, ?, ?, ?)""",
        ("youtube_search", 5000, f"{yesterday}T12:00:00+00:00", 1),
    )
    test_db.commit()

    # Insert today's usage
    log_api_call("youtube_search", 100, True)

    # Act
    usage = get_daily_quota_usage(today)

    # Assert - Only today's usage should be counted
    assert (
        usage == 100
    ), f"Expected 100 (today only), got {usage} - previous day leaked into calculation"


def test_get_daily_quota_usage_returns_zero_for_no_usage(test_db, monkeypatch):
    """
    Test that quota usage returns 0 for day with no usage (1.2-UNIT-010).

    Edge case: Empty database or new day.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    future_date = "2099-12-31"

    # Act
    usage = get_daily_quota_usage(future_date)

    # Assert
    assert usage == 0


@pytest.mark.tier1
def test_get_daily_quota_usage_handles_multiple_calls_same_day(test_db, monkeypatch):
    """
    Test quota calculation with multiple API calls same day (1.2-UNIT-011).

    Real-world scenario: Many API calls throughout the day.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    today = datetime.now(timezone.utc).date().isoformat()

    # Simulate various API calls
    log_api_call("youtube_search", 100, True)  # Search for videos
    log_api_call("youtube_videos", 1, True)  # Get video details
    log_api_call("youtube_videos", 1, True)  # Another video
    log_api_call("youtube_channels", 1, True)  # Channel info
    log_api_call("youtube_search", 100, True)  # Another search
    log_api_call("youtube_videos", 1, False, "Network error")  # Failed call (still counts)

    # Act
    usage = get_daily_quota_usage(today)

    # Assert
    assert usage == 204  # 100 + 1 + 1 + 1 + 100 + 1
