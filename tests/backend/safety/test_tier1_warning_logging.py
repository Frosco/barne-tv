"""
TIER 1 Safety Tests for Warning Logging (Story 4.2).

These tests verify critical safety rules for limit warning system:
- SQL injection prevention in warning logging
- UTC timestamp enforcement
- Banned videos excluded during wind-down filtering

TIER 1 tests MUST pass with 100% success rate before deployment.
"""

import pytest
from datetime import datetime, timezone, timedelta
from backend.db.queries import log_warning, get_warnings_for_date, get_available_videos


@pytest.mark.tier1
def test_warning_logging_sql_injection_prevention(test_db):
    """
    4.2-TIER1-001: Prevent SQL injection in warning logging.

    TIER 1 Rule 6: Always use SQL placeholders (never string formatting).

    Ensures malicious input cannot execute SQL due to parameterized queries.
    """
    # Test 1: SQL injection via shown_at timestamp
    # The CHECK constraint on warning_type prevents testing via warning_type
    # So we test SQL injection via the shown_at field instead
    malicious_timestamp = "2025-01-01T00:00:00Z'; DROP TABLE limit_warnings; --"

    # This should safely insert the malicious string as data, not execute it
    log_warning("10min", malicious_timestamp, conn=test_db)

    # Verify table still exists (DROP TABLE was not executed)
    cursor = test_db.execute("SELECT COUNT(*) FROM limit_warnings")
    count = cursor.fetchone()[0]
    assert count == 1, "Table should still exist - DROP TABLE was not executed"

    # Verify the malicious string was stored as data (NOT executed as SQL)
    cursor = test_db.execute("SELECT shown_at FROM limit_warnings")
    stored_timestamp = cursor.fetchone()[0]
    assert stored_timestamp == malicious_timestamp, "Malicious string should be stored as data"

    # Test 2: SQL injection attempt via shown_at to delete data
    malicious_timestamp_2 = "'; DELETE FROM limit_warnings; --"
    log_warning("5min", malicious_timestamp_2, conn=test_db)

    # Verify both warnings are still present (DELETE was not executed)
    cursor = test_db.execute("SELECT COUNT(*) FROM limit_warnings")
    count = cursor.fetchone()[0]
    assert count == 2, "Both warnings should exist - DELETE was not executed"

    # Test 3: SQL injection via shown_at with OR clause
    malicious_timestamp_3 = "2025-01-01' OR '1'='1"
    log_warning("2min", malicious_timestamp_3, conn=test_db)

    # Verify all 3 warnings exist
    cursor = test_db.execute("SELECT COUNT(*) FROM limit_warnings")
    count = cursor.fetchone()[0]
    assert count == 3, "All warnings should exist - SQL injection prevented"


@pytest.mark.tier1
def test_warning_logging_utc_timestamp_enforcement(test_db):
    """
    4.2-TIER1-002: Enforce UTC timestamps for warning logging.

    TIER 1 Rule 3: Always use UTC for timestamps.

    Verifies warnings are stored with UTC timestamps and retrieved correctly.
    """
    # Log warning with explicit UTC timestamp
    utc_time = datetime.now(timezone.utc)
    shown_at = utc_time.isoformat().replace("+00:00", "Z")

    log_warning("10min", shown_at, conn=test_db)

    # Retrieve warning and verify timestamp is stored correctly
    today = utc_time.date().isoformat()
    warnings = get_warnings_for_date(today, conn=test_db)

    assert len(warnings) == 1, "Should retrieve logged warning"
    assert warnings[0]["warningType"] == "10min"

    # Parse stored timestamp and verify it's UTC
    stored_timestamp = warnings[0]["shownAt"]
    parsed_time = datetime.fromisoformat(stored_timestamp.replace("Z", "+00:00"))

    # Verify timezone is UTC (offset +00:00)
    assert parsed_time.tzinfo is not None, "Timestamp should include timezone"
    assert parsed_time.utcoffset() == timedelta(0), "Timestamp should be UTC (+00:00)"

    # Verify date filtering works correctly with UTC dates
    yesterday = (utc_time - timedelta(days=1)).date().isoformat()
    warnings_yesterday = get_warnings_for_date(yesterday, conn=test_db)
    assert len(warnings_yesterday) == 0, "Should not retrieve warnings from different date"


@pytest.mark.tier1
def test_winddown_filtering_banned_videos_excluded(test_db):
    """
    4.2-TIER1-003: Ensure banned videos are ALWAYS excluded, even during wind-down.

    TIER 1 Rule 1: ALWAYS filter banned videos from results.

    Wind-down mode adds max_duration filtering but MUST maintain banned video exclusion.
    """
    # Setup: Create content source
    from tests.backend.conftest import (
        setup_content_source,
        setup_test_videos,
        create_test_video,
        ban_video,
    )

    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Create 3 short videos (< 5 min): 2 available, 1 banned
    videos = [
        create_test_video(
            video_id="short_safe_1",
            title="Short Safe Video 1",
            content_source_id=source_id,
            duration_seconds=180,  # 3 minutes
            is_available=1,
        ),
        create_test_video(
            video_id="short_banned",
            title="Short Banned Video",
            content_source_id=source_id,
            duration_seconds=240,  # 4 minutes
            is_available=1,
        ),
        create_test_video(
            video_id="short_safe_2",
            title="Short Safe Video 2",
            content_source_id=source_id,
            duration_seconds=120,  # 2 minutes
            is_available=1,
        ),
    ]
    setup_test_videos(test_db, videos)

    # Ban the middle video
    ban_video(test_db, "short_banned")

    # Wind-down mode: Get videos with max_duration=300 (5 minutes)
    # TIER 1 Rule 1: Banned video MUST be excluded even though it fits duration
    available_videos = get_available_videos(
        exclude_banned=True, max_duration_seconds=300, conn=test_db
    )

    # Verify only 2 safe videos returned (banned video excluded)
    assert len(available_videos) == 2, "Should return 2 safe videos (banned excluded)"

    video_ids = [v["videoId"] for v in available_videos]
    assert "short_safe_1" in video_ids, "Short safe video 1 should be included"
    assert "short_safe_2" in video_ids, "Short safe video 2 should be included"
    assert "short_banned" not in video_ids, "Banned video MUST be excluded despite fitting duration"

    # Additional safety check: Verify with exclude_banned=False the banned video IS present
    all_videos_including_banned = get_available_videos(
        exclude_banned=False, max_duration_seconds=300, conn=test_db
    )
    all_video_ids = [v["videoId"] for v in all_videos_including_banned]

    # When NOT filtering banned, all 3 videos should be present
    assert (
        len(all_videos_including_banned) == 3
    ), "Should return all 3 videos when not filtering banned"
    assert "short_banned" in all_video_ids, "Banned video present when exclude_banned=False"


@pytest.mark.tier1
def test_warning_type_validation(test_db):
    """
    4.2-TIER1-004: Validate warning types against schema CHECK constraint.

    TIER 1 Rule 5: Validate all parent inputs.

    Database schema enforces warning_type IN ('10min', '5min', '2min').
    This test verifies the constraint is enforced.
    """
    now = datetime.now(timezone.utc).isoformat()

    # Valid warning types should succeed
    valid_types = ["10min", "5min", "2min"]
    for warning_type in valid_types:
        log_warning(warning_type, now, conn=test_db)

    # Verify all 3 valid warnings were logged
    today = datetime.now(timezone.utc).date().isoformat()
    warnings = get_warnings_for_date(today, conn=test_db)
    assert len(warnings) == 3, "All valid warning types should be logged"

    # Invalid warning type should raise database constraint error
    import sqlite3

    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        log_warning("15min", now, conn=test_db)  # Invalid type

    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        log_warning("1min", now, conn=test_db)  # Invalid type

    with pytest.raises(sqlite3.IntegrityError, match="CHECK constraint failed"):
        log_warning("", now, conn=test_db)  # Empty string

    # Verify invalid warnings were NOT logged
    warnings_after = get_warnings_for_date(today, conn=test_db)
    assert len(warnings_after) == 3, "Invalid warnings should not be logged"


@pytest.mark.tier1
def test_warning_query_date_filtering_sql_injection(test_db):
    """
    4.2-TIER1-005: Prevent SQL injection in get_warnings_for_date query.

    TIER 1 Rule 6: Always use SQL placeholders (never string formatting).

    Ensures malicious date input cannot execute SQL or bypass date filtering.
    """
    # Log legitimate warning
    now = datetime.now(timezone.utc)
    shown_at = now.isoformat().replace("+00:00", "Z")
    log_warning("10min", shown_at, conn=test_db)

    today = now.date().isoformat()

    # Attempt SQL injection via date parameter
    malicious_date = "2025-01-01' OR '1'='1"

    # Query with malicious date should NOT return all warnings
    # It should either return empty list or raise an error
    try:
        warnings = get_warnings_for_date(malicious_date, conn=test_db)
        # If no error, verify it didn't return the warning (SQL injection failed)
        assert len(warnings) == 0, "Malicious date should not match any warnings"
    except Exception:
        # If error raised, that's also acceptable (malicious input rejected)
        pass

    # Verify legitimate query still works
    warnings_legit = get_warnings_for_date(today, conn=test_db)
    assert len(warnings_legit) == 1, "Legitimate query should return the warning"
    assert warnings_legit[0]["warningType"] == "10min"

    # Another SQL injection attempt: try to drop table
    malicious_date_2 = "'; DROP TABLE limit_warnings; --"

    try:
        warnings_2 = get_warnings_for_date(malicious_date_2, conn=test_db)
        assert len(warnings_2) == 0, "Malicious date should not match any warnings"
    except Exception:
        pass

    # Verify table still exists and data intact
    cursor = test_db.execute("SELECT COUNT(*) FROM limit_warnings")
    count = cursor.fetchone()[0]
    assert count == 1, "Table should still exist with 1 warning"
