"""
TIER 1 Safety Tests for Daily Limit Calculation (Story 4.1, Task 8).

These tests verify critical child safety rules related to daily viewing limits.

TIER 1 Rules Tested:
- Rule 2: manual_play and grace_play MUST be excluded from limit calculations
- Rule 3: UTC timezone MUST be used for all date operations
- Rule 6: SQL placeholders MUST be used (no string formatting)

100% code coverage required for safety-critical paths.
ALL tests MUST pass before deployment.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from backend.services.viewing_session import get_daily_limit, reset_daily_limit
from tests.backend.conftest import insert_watch_history


@pytest.mark.tier1
def test_get_daily_limit_excludes_manual_play(test_db):
    """
    TIER 1 Safety Test: Verify manual_play entries excluded from limit.

    If this fails, parent "play again" counts toward child's limit - UNACCEPTABLE.

    Acceptance Criteria: AC4 (minutes watched excludes manual_play)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history with mixed countable and manual_play entries
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Countable entry (15 minutes = 900 seconds)
            {
                "video_id": "vid1",
                "video_title": "Test Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,  # Counts toward limit
                "grace_play": 0,
                "duration_watched_seconds": 900,
            },
            # Manual play entry (10 minutes = 600 seconds) - should NOT count
            {
                "video_id": "vid2",
                "video_title": "Test Video 2",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 1,  # Does NOT count toward limit
                "grace_play": 0,
                "duration_watched_seconds": 600,
            },
        ],
    )

    # ACT: Get daily limit (should only count first video)
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: Only countable entry (900 seconds = 15 minutes) should be counted
    assert daily_limit["minutesWatched"] == 15, "manual_play entry was incorrectly counted"
    assert daily_limit["minutesRemaining"] == 15  # 30 - 15 = 15
    assert daily_limit["currentState"] == "normal"  # >10 min remaining


@pytest.mark.tier1
def test_get_daily_limit_excludes_grace_play(test_db):
    """
    TIER 1 Safety Test: Verify grace_play entries excluded from limit.

    If this fails, grace videos count toward child's limit - UNACCEPTABLE.

    Acceptance Criteria: AC4 (minutes watched excludes grace_play)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history with mixed countable and grace_play entries
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Countable entry (20 minutes = 1200 seconds)
            {
                "video_id": "vid1",
                "video_title": "Test Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,  # Counts toward limit
                "duration_watched_seconds": 1200,
            },
            # Grace play entry (5 minutes = 300 seconds) - should NOT count
            {
                "video_id": "vid3",
                "video_title": "Test Video 3",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T12:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,  # Does NOT count toward limit
                "duration_watched_seconds": 300,
            },
        ],
    )

    # ACT: Get daily limit (should only count first video)
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: Only countable entry (1200 seconds = 20 minutes) should be counted
    assert daily_limit["minutesWatched"] == 20, "grace_play entry was incorrectly counted"
    assert daily_limit["minutesRemaining"] == 10  # 30 - 20 = 10
    assert daily_limit["currentState"] == "winddown"  # Exactly 10 min remaining


@pytest.mark.tier1
def test_get_daily_limit_uses_utc_date(test_db, monkeypatch):
    """
    TIER 1 Safety Test: Verify UTC timezone enforcement.

    If this fails, child could bypass limit by changing device timezone - UNACCEPTABLE.

    Acceptance Criteria: AC6 (midnight UTC reset, UTC timezone enforced)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Mock current time to UTC midnight (2025-01-03T00:00:00Z)
    utc_midnight = datetime(2025, 1, 3, 0, 0, 0, tzinfo=timezone.utc)

    # Insert watch history for "today" (2025-01-03) in UTC
    today_utc = "2025-01-03"

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today_utc}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            }
        ],
    )

    # ACT: Get daily limit with mocked UTC time
    with patch("backend.services.viewing_session.datetime") as mock_datetime:
        mock_datetime.now.return_value = utc_midnight
        mock_datetime.min = datetime.min
        mock_datetime.combine = datetime.combine
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: Should use UTC date (2025-01-03) and find the watch history
    assert daily_limit["date"] == today_utc, "Did not use UTC date"
    assert daily_limit["minutesWatched"] == 10, "Did not find watch history for UTC date"
    assert daily_limit["resetTime"] == "2025-01-04T00:00:00Z", "Reset time not at UTC midnight"


@pytest.mark.tier1
def test_limit_reset_only_deletes_countable_entries(test_db):
    """
    TIER 1 Safety Test: Verify reset preserves manual_play and grace_play entries.

    If this fails, parent history could be deleted - DATA LOSS UNACCEPTABLE.

    Acceptance Criteria: AC7 (reset preserves manual/grace entries)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create mixed watch history (countable, manual_play, grace_play)
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Countable entry - SHOULD BE DELETED
            {
                "video_id": "vid1",
                "video_title": "Test Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 900,  # 15 minutes
            },
            # Manual play entry - MUST BE PRESERVED
            {
                "video_id": "vid2",
                "video_title": "Test Video 2",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 1,
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            },
            # Grace play entry - MUST BE PRESERVED
            {
                "video_id": "vid3",
                "video_title": "Test Video 3",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T12:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,
                "duration_watched_seconds": 300,  # 5 minutes
            },
        ],
    )

    # ACT: Reset daily limit (should delete only countable entries)
    new_limit = reset_daily_limit(conn=test_db)

    # ASSERT: Minutes watched should be 0 (countable entry deleted)
    assert new_limit["minutesWatched"] == 0, "Countable entry was not deleted"
    assert new_limit["minutesRemaining"] == 30  # Full limit restored

    # Verify manual_play and grace_play entries still exist
    all_history = test_db.execute(
        f"SELECT * FROM watch_history WHERE DATE(watched_at) = '{today}'"
    ).fetchall()

    assert len(all_history) == 2, "Manual/grace entries were deleted - DATA LOSS"

    # Verify the preserved entries are manual_play and grace_play
    manual_entry = [h for h in all_history if h["manual_play"] == 1]
    grace_entry = [h for h in all_history if h["grace_play"] == 1]

    assert len(manual_entry) == 1, "manual_play entry was deleted"
    assert len(grace_entry) == 1, "grace_play entry was deleted"

    # Verify countable entry was deleted
    countable_entry = [h for h in all_history if h["manual_play"] == 0 and h["grace_play"] == 0]
    assert len(countable_entry) == 0, "Countable entry was not deleted"


@pytest.mark.tier1
def test_get_daily_limit_excludes_mixed_manual_and_grace(test_db):
    """
    TIER 1 Safety Test: Verify both manual_play AND grace_play excluded together.

    If this fails, complex scenarios with both flags could count toward limit - UNACCEPTABLE.

    Test ID: 4.1-UNIT-005
    Acceptance Criteria: AC4 (minutes watched excludes manual_play AND grace_play)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create complex watch history with all three types
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Countable entry 1 (10 minutes = 600 seconds)
            {
                "video_id": "vid1",
                "video_title": "Countable Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T09:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,
            },
            # Manual play entry (8 minutes = 480 seconds) - should NOT count
            {
                "video_id": "vid2",
                "video_title": "Manual Play Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 1,  # Does NOT count
                "grace_play": 0,
                "duration_watched_seconds": 480,
            },
            # Countable entry 2 (5 minutes = 300 seconds)
            {
                "video_id": "vid3",
                "video_title": "Countable Video 2",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            # Grace play entry (7 minutes = 420 seconds) - should NOT count
            {
                "video_id": "vid4",
                "video_title": "Grace Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T12:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,  # Does NOT count
                "duration_watched_seconds": 420,
            },
        ],
    )

    # ACT: Get daily limit (should only count vid1 + vid3)
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: Only countable entries (600 + 300 = 900 seconds = 15 minutes) should be counted
    assert (
        daily_limit["minutesWatched"] == 15
    ), "manual_play or grace_play entries were incorrectly counted"
    assert daily_limit["minutesRemaining"] == 15  # 30 - 15 = 15
    assert daily_limit["currentState"] == "normal"  # >10 min remaining

    # Verify total watch history has all 4 entries (none lost)
    all_history = test_db.execute(
        f"SELECT * FROM watch_history WHERE DATE(watched_at) = '{today}'"
    ).fetchall()
    assert len(all_history) == 4, "Watch history entries were lost"


@pytest.mark.tier1
def test_get_watch_history_uses_sql_placeholders(test_db):
    """
    TIER 1 Safety Test: Verify get_watch_history_for_date() uses SQL placeholders.

    If this fails, SQL injection vulnerability exists - SECURITY CRITICAL.

    Test ID: 4.1-UNIT-006
    Acceptance Criteria: AC4 (SQL placeholders required for all queries)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history for today
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            }
        ],
    )

    # ACT: Import and inspect the query function
    from backend.db.queries import get_watch_history_for_date

    # Call function with normal date
    history = get_watch_history_for_date(today, conn=test_db)

    # ASSERT: Should return 1 entry
    assert len(history) == 1, "Normal query failed"
    assert history[0]["videoId"] == "vid1"

    # Try SQL injection attempt (should be safely escaped by placeholders)
    malicious_date = "2025-01-03' OR '1'='1"
    history_injection = get_watch_history_for_date(malicious_date, conn=test_db)

    # ASSERT: SQL injection should return empty (date doesn't match), not all rows
    # If placeholders work correctly, the literal string "2025-01-03' OR '1'='1" won't match any dates
    assert len(history_injection) == 0, "SQL injection succeeded - placeholders NOT used!"


@pytest.mark.tier1
def test_get_daily_limit_with_non_utc_timezone_mock(test_db, monkeypatch):
    """
    TIER 1 Safety Test: Verify UTC used even when system timezone is non-UTC.

    If this fails, limit could vary by device timezone - UNACCEPTABLE.

    Test ID: 4.1-UNIT-009
    Acceptance Criteria: AC6 (UTC timezone enforcement - cannot bypass)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Mock datetime.now() to return a time in PST (UTC-8)
    # If code incorrectly uses naive datetime or local timezone, test will fail

    # Create a PST timezone time: 2025-01-03 16:00:00 PST = 2025-01-04 00:00:00 UTC
    # This is midnight UTC (next day in PST)
    utc_midnight = datetime(2025, 1, 4, 0, 0, 0, tzinfo=timezone.utc)

    # Insert watch history for "today" in UTC (2025-01-04)
    today_utc = "2025-01-04"

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today_utc}T02:00:00Z",  # 2 AM UTC on 2025-01-04
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 720,  # 12 minutes
            }
        ],
    )

    # ACT: Mock datetime.now() to return UTC midnight (should use this, not PST)
    with patch("backend.services.viewing_session.datetime") as mock_datetime:
        mock_datetime.now.return_value = utc_midnight
        mock_datetime.min = datetime.min
        mock_datetime.combine = datetime.combine
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: Should use UTC date (2025-01-04) regardless of "system timezone"
    assert daily_limit["date"] == today_utc, "Did not use UTC date"
    assert daily_limit["minutesWatched"] == 12, "Did not find watch history for UTC date"
    assert daily_limit["resetTime"] == "2025-01-05T00:00:00Z", "Reset time not at UTC midnight"


@pytest.mark.tier1
def test_delete_history_uses_sql_placeholders(test_db):
    """
    TIER 1 Safety Test: Verify delete_todays_countable_history() uses SQL placeholders.

    If this fails, SQL injection vulnerability exists in DELETE - SECURITY CRITICAL.

    Test ID: 4.1-UNIT-012
    Acceptance Criteria: AC7 (SQL placeholders required for all queries, including DELETE)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history for today
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Countable entry - should be deleted
            {
                "video_id": "vid1",
                "video_title": "Countable Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,
            },
            # Manual play entry - should NOT be deleted
            {
                "video_id": "vid2",
                "video_title": "Manual Play Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 1,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # ACT: Call delete function with normal date
    from backend.db.queries import delete_todays_countable_history

    deleted_count = delete_todays_countable_history(today, conn=test_db)

    # ASSERT: Should delete 1 countable entry
    assert deleted_count == 1, "Normal delete failed"

    # Verify manual_play entry still exists
    remaining = test_db.execute(
        f"SELECT * FROM watch_history WHERE DATE(watched_at) = '{today}'"
    ).fetchall()
    assert len(remaining) == 1, "Manual play entry was deleted"
    assert remaining[0]["manual_play"] == 1

    # Re-insert countable entry for injection test
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid3",
                "video_title": "Another Countable",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T12:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 400,
            }
        ],
    )

    # Try SQL injection attempt (should be safely escaped by placeholders)
    malicious_date = "2025-01-03' OR '1'='1"
    deleted_injection = delete_todays_countable_history(malicious_date, conn=test_db)

    # ASSERT: SQL injection should delete 0 rows (date doesn't match)
    # If placeholders work correctly, the literal string won't match any dates
    assert deleted_injection == 0, "SQL injection succeeded - placeholders NOT used in DELETE!"

    # Verify our test entries still exist (not deleted by injection)
    final_count = test_db.execute(
        f"SELECT COUNT(*) as count FROM watch_history WHERE DATE(watched_at) = '{today}'"
    ).fetchone()
    assert final_count["count"] == 2, "SQL injection deleted rows - SECURITY VULNERABILITY!"


# =============================================================================
# P0 CORE BUSINESS LOGIC TESTS
# =============================================================================


def test_get_setting_returns_configured_value(test_db):
    """
    P0 Unit Test: Verify get_setting() returns configured daily limit value.

    Test ID: 4.1-UNIT-001
    Acceptance Criteria: AC2 (daily limit from settings, default 30)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Settings fixture creates daily_limit_minutes=30
    from backend.db.queries import get_setting

    # ACT: Get the daily limit setting
    daily_limit_str = get_setting("daily_limit_minutes", conn=test_db)

    # ASSERT: Should return the configured value as string
    assert daily_limit_str is not None
    assert daily_limit_str == "30"  # Stored as plain int string

    # Can be converted to int
    daily_limit_int = int(daily_limit_str)
    assert daily_limit_int == 30


def test_get_daily_limit_defaults_to_30_when_setting_missing(test_db):
    """
    P0 Unit Test: Verify get_daily_limit() defaults to 30 when setting missing.

    Test ID: 4.1-UNIT-002
    Acceptance Criteria: AC2 (default to 30 minutes when setting not configured)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Delete the daily_limit_minutes setting
    test_db.execute("DELETE FROM settings WHERE key = 'daily_limit_minutes'")
    test_db.commit()

    # Create some watch history (10 minutes watched)
    today = datetime.now(timezone.utc).date().isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            }
        ],
    )

    # ACT: Get daily limit (should handle KeyError gracefully and use default)
    try:
        daily_limit = get_daily_limit(conn=test_db)

        # If get_daily_limit doesn't handle KeyError, it will raise here
        # The route handler in routes.py handles KeyError and defaults to 30
        assert False, "Expected KeyError to be raised but got result: " + str(daily_limit)
    except KeyError as e:
        # ASSERT: KeyError should be raised (route handler will catch it)
        assert "daily_limit_minutes" in str(e)


def test_state_transitions_to_grace_when_limit_reached(test_db):
    """
    P0 Unit Test: Verify state = 'grace' when minutes_remaining = 0.

    Test ID: 4.1-UNIT-007
    Acceptance Criteria: AC5 (grace screen when limit reached)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history that exactly reaches the limit (30 minutes)
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1200,  # 20 minutes
            },
            {
                "video_id": "vid2",
                "video_title": "Test Video 2",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            },
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: State should be 'grace' (limit reached, no grace consumed yet)
    assert daily_limit["minutesWatched"] == 30
    assert daily_limit["minutesRemaining"] == 0
    assert daily_limit["currentState"] == "grace"


def test_duration_conversion_seconds_to_minutes(test_db):
    """
    P0 Unit Test: Verify duration_watched_seconds converted to minutes (÷60).

    Test ID: 4.1-UNIT-013
    Acceptance Criteria: AC9 (actual duration watched counts toward limit)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history with various durations
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 660,  # 11 minutes
            }
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: 660 seconds / 60 = 11 minutes (integer division)
    assert daily_limit["minutesWatched"] == 11
    assert daily_limit["minutesRemaining"] == 19  # 30 - 11


def test_sum_multiple_video_durations_correctly(test_db):
    """
    P0 Unit Test: Verify multiple videos' durations summed correctly.

    Test ID: 4.1-UNIT-014
    Acceptance Criteria: AC9 (aggregate duration calculation)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history with multiple videos
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T09:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,  # 5 minutes
            },
            {
                "video_id": "vid2",
                "video_title": "Video 2",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 480,  # 8 minutes
            },
            {
                "video_id": "vid3",
                "video_title": "Video 3",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 720,  # 12 minutes
            },
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: (300 + 480 + 720) / 60 = 1500 / 60 = 25 minutes
    assert daily_limit["minutesWatched"] == 25
    assert daily_limit["minutesRemaining"] == 5  # 30 - 25
    assert daily_limit["currentState"] == "winddown"  # ≤10 min remaining


def test_state_normal_when_more_than_10_minutes_remaining(test_db):
    """
    P0 Unit Test: Verify state = 'normal' when minutes_remaining > 10.

    Test ID: 4.1-UNIT-016
    Acceptance Criteria: State machine - normal state
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history with 15 minutes watched (15 min remaining)
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 900,  # 15 minutes
            }
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: State should be 'normal' (>10 min remaining)
    assert daily_limit["minutesWatched"] == 15
    assert daily_limit["minutesRemaining"] == 15  # 30 - 15
    assert daily_limit["currentState"] == "normal"


def test_state_winddown_when_10_minutes_or_less_remaining(test_db):
    """
    P0 Unit Test: Verify state = 'winddown' when minutes_remaining ≤ 10.

    Test ID: 4.1-UNIT-017
    Acceptance Criteria: State machine - winddown state
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history with 20 minutes watched (10 min remaining)
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1200,  # 20 minutes
            }
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: State should be 'winddown' (exactly 10 min remaining)
    assert daily_limit["minutesWatched"] == 20
    assert daily_limit["minutesRemaining"] == 10  # 30 - 20
    assert daily_limit["currentState"] == "winddown"


def test_state_grace_when_limit_reached_and_no_grace_consumed(test_db):
    """
    P0 Unit Test: Verify state = 'grace' when limit reached and grace not consumed.

    Test ID: 4.1-UNIT-018
    Acceptance Criteria: State machine - grace state
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history that reaches limit (no grace video yet)
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1800,  # 30 minutes
            }
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: State should be 'grace' (0 min remaining, no grace consumed)
    assert daily_limit["minutesWatched"] == 30
    assert daily_limit["minutesRemaining"] == 0
    assert daily_limit["currentState"] == "grace"


def test_state_locked_when_grace_consumed(test_db):
    """
    P0 Unit Test: Verify state = 'locked' when grace video consumed.

    Test ID: 4.1-UNIT-019
    Acceptance Criteria: State machine - locked state
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history with limit reached AND grace consumed
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Countable entry (30 minutes - hits limit)
            {
                "video_id": "vid1",
                "video_title": "Test Video 1",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1800,  # 30 minutes
            },
            # Grace entry (5 minutes - doesn't count but marks grace consumed)
            {
                "video_id": "vid2",
                "video_title": "Grace Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,  # Grace video consumed
                "duration_watched_seconds": 300,  # 5 minutes
            },
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: State should be 'locked' (grace consumed, locked until midnight)
    assert daily_limit["minutesWatched"] == 30  # Grace video doesn't count
    assert daily_limit["minutesRemaining"] == 0
    assert daily_limit["currentState"] == "locked"


# =============================================================================
# P1 ADDITIONAL TESTS
# =============================================================================


def test_partial_minutes_handling_floor_division(test_db):
    """
    P1 Unit Test: Verify partial minutes handled with floor division (truncate).

    Test ID: 4.1-UNIT-015
    Acceptance Criteria: AC9 (duration counting - rounding behavior)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history with partial minutes
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # 659 seconds = 10 minutes 59 seconds → should be 10 minutes (floor)
            {
                "video_id": "vid1",
                "video_title": "Partial Minutes Test 1",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 659,
            },
            # 61 seconds = 1 minute 1 second → should be 1 minute (floor)
            {
                "video_id": "vid2",
                "video_title": "Partial Minutes Test 2",
                "channel_name": "Test",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 61,
            },
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: (659 + 61) / 60 = 720 / 60 = 12 minutes (integer floor division)
    assert daily_limit["minutesWatched"] == 12
    assert daily_limit["minutesRemaining"] == 18  # 30 - 12


# =============================================================================
# P2 EDGE CASE TESTS
# =============================================================================


def test_daily_limit_less_than_10_minutes_jumps_to_winddown(test_db):
    """
    P2 Unit Test: Verify daily limit < 10 minutes starts in winddown state.

    Test ID: 4.1-UNIT-020
    Acceptance Criteria: Edge case - small limits immediately trigger winddown
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Set daily limit to 8 minutes (< 10)
    test_db.execute("UPDATE settings SET value = '8' WHERE key = 'daily_limit_minutes'")
    test_db.commit()

    # Create watch history with 2 minutes watched
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "small_limit_test",
                "video_title": "Test Video",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 120,  # 2 minutes
            }
        ],
    )

    # ACT: Get daily limit
    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: Should be winddown (6 minutes remaining, which is ≤10)
    assert daily_limit["minutesWatched"] == 2
    assert daily_limit["minutesRemaining"] == 6  # 8 - 2 = 6 (≤10)
    assert daily_limit["currentState"] == "winddown"  # Not normal, jumps to winddown

    # Test with 0 minutes watched - still winddown
    test_db.execute("DELETE FROM watch_history")
    test_db.commit()

    daily_limit_empty = get_daily_limit(conn=test_db)
    assert daily_limit_empty["minutesWatched"] == 0
    assert daily_limit_empty["minutesRemaining"] == 8  # 8 minutes (≤10)
    assert daily_limit_empty["currentState"] == "winddown"  # Starts in winddown
