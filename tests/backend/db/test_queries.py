"""
Unit tests for database query functions.

Covers:
- Story 1.2: Quota Tracking (log_api_call, get_daily_quota_usage)
- Story 3.2: Settings Management (get_setting, set_setting)

TIER 1 Safety Tests: 100% coverage required for quota tracking functions.

Test IDs from test design documents:
- 1.2-UNIT-004 through 1.2-UNIT-011
- T3.2-BE-016, T3.2-BE-017
"""

import pytest
import json
from datetime import datetime, timezone, timedelta
from backend.db.queries import log_api_call, get_daily_quota_usage, get_setting, set_setting


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


# =============================================================================
# get_setting() Tests (Story 3.2)
# =============================================================================


def test_get_setting_returns_correct_value(test_db, monkeypatch):
    """
    Test that get_setting() returns correct value for existing key (T3.2-BE-016).

    Tests:
    - Returns JSON-encoded string value
    - Handles different data types (int, bool, string)
    - Uses SQL placeholders (TIER 1)
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Insert test settings with unique keys
    now = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT INTO settings (key, value, updated_at, created_at) VALUES (?, ?, ?, ?)",
        ("test_int_setting", json.dumps(45), now, now),
    )
    test_db.execute(
        "INSERT INTO settings (key, value, updated_at, created_at) VALUES (?, ?, ?, ?)",
        ("test_grid_setting", json.dumps(12), now, now),
    )
    test_db.execute(
        "INSERT INTO settings (key, value, updated_at, created_at) VALUES (?, ?, ?, ?)",
        ("test_bool_setting", json.dumps(False), now, now),
    )
    test_db.commit()

    # Act & Assert: Test integer setting
    result_int = get_setting("test_int_setting", conn=test_db)
    assert json.loads(result_int) == 45  # JSON-decoded value is int

    # Act & Assert: Test another integer setting
    result_grid = get_setting("test_grid_setting", conn=test_db)
    assert json.loads(result_grid) == 12

    # Act & Assert: Test boolean setting
    result_bool = get_setting("test_bool_setting", conn=test_db)
    assert json.loads(result_bool) is False


def test_get_setting_raises_keyerror_for_nonexistent_key(test_db):
    """
    Test that get_setting() raises KeyError for non-existent key (T3.2-BE-016).

    Tests edge case: Setting key doesn't exist in database.
    """
    # Act & Assert
    with pytest.raises(KeyError) as exc_info:
        get_setting("nonexistent_key", conn=test_db)

    assert "nonexistent_key" in str(exc_info.value)


@pytest.mark.tier1
def test_get_setting_uses_sql_placeholders(test_db, monkeypatch):
    """
    Test that get_setting() uses SQL placeholders (T3.2-BE-016).

    TIER 1 Rule 6: SQL injection prevention.
    Tests that malicious key names don't execute as SQL.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Insert a normal setting
    now = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT INTO settings (key, value, updated_at, created_at) VALUES (?, ?, ?, ?)",
        ("test_setting", json.dumps("test_value"), now, now),
    )
    test_db.commit()

    # Act: Try to use SQL injection in key name
    malicious_key = "test_setting' OR '1'='1"

    # Assert: Should raise KeyError (not find the malicious key)
    with pytest.raises(KeyError):
        get_setting(malicious_key, conn=test_db)

    # Verify original setting still exists (table not corrupted)
    result = get_setting("test_setting", conn=test_db)
    assert json.loads(result) == "test_value"


# =============================================================================
# set_setting() Tests (Story 3.2)
# =============================================================================


def test_set_setting_inserts_new_key(test_db, monkeypatch):
    """
    Test that set_setting() inserts new key correctly (T3.2-BE-017).

    Tests INSERT behavior of upsert operation.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Act: Insert new setting
    set_setting("new_setting_key", json.dumps(100))

    # Assert: Setting exists in database
    result = test_db.execute(
        "SELECT key, value FROM settings WHERE key = ?", ("new_setting_key",)
    ).fetchone()

    assert result is not None
    assert result["key"] == "new_setting_key"
    assert json.loads(result["value"]) == 100


def test_set_setting_updates_existing_key(test_db, monkeypatch):
    """
    Test that set_setting() updates existing key correctly (T3.2-BE-017).

    Tests UPDATE behavior of upsert operation.
    Tests that no duplicate rows are created.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Insert initial value with unique key
    now = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT INTO settings (key, value, updated_at, created_at) VALUES (?, ?, ?, ?)",
        ("test_update_key", json.dumps(30), now, now),
    )
    test_db.commit()

    # Act: Update existing setting
    set_setting("test_update_key", json.dumps(90))

    # Assert: Value updated
    result = test_db.execute(
        "SELECT value FROM settings WHERE key = ?", ("test_update_key",)
    ).fetchone()
    assert json.loads(result["value"]) == 90

    # Assert: No duplicate rows created
    count = test_db.execute(
        "SELECT COUNT(*) FROM settings WHERE key = ?", ("test_update_key",)
    ).fetchone()[0]
    assert count == 1, "set_setting created duplicate row instead of updating"


@pytest.mark.tier1
def test_set_setting_uses_utc_timestamps(test_db, monkeypatch):
    """
    Test that set_setting() uses UTC timestamps (T3.2-BE-017).

    TIER 1 Rule 3: Always use UTC for timestamps.
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
    set_setting("test_utc_setting", json.dumps("test_value"))

    # Assert: Timestamp uses UTC (ends with +00:00 or Z)
    result = test_db.execute(
        "SELECT updated_at FROM settings WHERE key = ?", ("test_utc_setting",)
    ).fetchone()

    timestamp = result["updated_at"]
    assert timestamp.endswith("+00:00") or timestamp.endswith(
        "Z"
    ), f"Timestamp must use UTC, got: {timestamp}"


def test_set_setting_stores_json_encoded_values(test_db, monkeypatch):
    """
    Test that set_setting() stores values as JSON-encoded strings (T3.2-BE-017).

    Verifies values are stored as strings, not raw integers/booleans.
    """

    # Arrange
    def mock_get_connection():
        from contextlib import contextmanager

        @contextmanager
        def _mock():
            yield test_db

        return _mock()

    monkeypatch.setattr("backend.db.queries.get_connection", mock_get_connection)

    # Act: Store various types as JSON
    set_setting("int_setting", json.dumps(45))
    set_setting("bool_setting", json.dumps(True))
    set_setting("string_setting", json.dumps("hello"))

    # Assert: All values stored as JSON strings
    int_result = test_db.execute(
        "SELECT value FROM settings WHERE key = ?", ("int_setting",)
    ).fetchone()
    assert int_result["value"] == "45"  # String, not int
    assert json.loads(int_result["value"]) == 45  # Can parse back to int

    bool_result = test_db.execute(
        "SELECT value FROM settings WHERE key = ?", ("bool_setting",)
    ).fetchone()
    assert bool_result["value"] == "true"  # String, not bool
    assert json.loads(bool_result["value"]) is True  # Can parse back to bool

    string_result = test_db.execute(
        "SELECT value FROM settings WHERE key = ?", ("string_setting",)
    ).fetchone()
    assert string_result["value"] == '"hello"'  # JSON-encoded string
    assert json.loads(string_result["value"]) == "hello"  # Can parse back
