"""
Integration Tests for Daily Limit API Endpoints (Story 4.1, Task 9).

Tests the HTTP API contracts for daily limit status and reset endpoints.

Tests verify:
- API response formats
- Authentication requirements
- State persistence
- Error handling
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch

from backend.auth import create_session
from tests.backend.conftest import insert_watch_history


def test_get_limit_status_returns_current_state(test_client, test_db):
    """
    Integration Test: GET /api/limit/status returns current daily limit state.

    Acceptance Criteria: AC1, AC2, AC10 (watch history tracked, settings used, status returned)
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

    # ACT: Call API endpoint
    response = test_client.get("/api/limit/status")

    # ASSERT: Response structure and content
    assert response.status_code == 200

    data = response.json()
    assert "date" in data
    assert "minutesWatched" in data
    assert "minutesRemaining" in data
    assert "currentState" in data
    assert "resetTime" in data

    # Verify calculated state
    assert data["date"] == today
    assert data["minutesWatched"] == 10
    assert data["minutesRemaining"] == 20  # 30 - 10
    assert data["currentState"] == "normal"  # >10 min remaining


def test_reset_limit_requires_authentication(test_client, test_db):
    """
    Integration Test: POST /admin/limit/reset requires valid session.

    Acceptance Criteria: AC7 (admin can reset, authentication required)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: No session cookie (unauthenticated)

    # ACT: Call API endpoint without authentication
    response = test_client.post("/admin/limit/reset")

    # ASSERT: Should return 401 Unauthorized
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"


def test_reset_limit_deletes_countable_history(test_client, test_db):
    """
    Integration Test: POST /admin/limit/reset deletes countable watch history.

    Acceptance Criteria: AC7 (reset deletes countable entries, preserves manual/grace)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create authenticated session
    session_id = create_session()
    test_client.cookies.set("session_id", session_id)

    # Create mixed watch history
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Countable entry - should be deleted
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
            # Manual play entry - should be preserved
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
        ],
    )

    # ACT: Call API endpoint to reset limit
    response = test_client.post("/admin/limit/reset")

    # ASSERT: Response structure and content
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Daglig grense tilbakestilt"
    assert "newLimit" in data

    # Verify new limit state
    new_limit = data["newLimit"]
    assert new_limit["minutesWatched"] == 0  # Countable entry deleted
    assert new_limit["minutesRemaining"] == 30  # Full limit restored

    # Verify database state - manual_play entry still exists
    all_history = test_db.execute(
        f"SELECT * FROM watch_history WHERE DATE(watched_at) = '{today}'"
    ).fetchall()

    assert len(all_history) == 1  # Only manual_play entry remains
    assert all_history[0]["manual_play"] == 1  # Verify it's the manual_play entry


def test_limit_status_persists_across_requests(test_client, test_db):
    """
    Integration Test: Limit status recalculated from database on each request (stateless API).

    Acceptance Criteria: AC8 (watch history persists, state recalculated from DB)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history
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
                "duration_watched_seconds": 300,  # 5 minutes
            }
        ],
    )

    # ACT 1: First request
    response1 = test_client.get("/api/limit/status")
    data1 = response1.json()

    # Add more watch history
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid2",
                "video_title": "Test Video 2",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            }
        ],
    )

    # ACT 2: Second request (should see updated state)
    response2 = test_client.get("/api/limit/status")
    data2 = response2.json()

    # ASSERT: State changed between requests
    assert response1.status_code == 200
    assert response2.status_code == 200

    # First request: 5 minutes watched
    assert data1["minutesWatched"] == 5
    assert data1["minutesRemaining"] == 25

    # Second request: 15 minutes watched (5 + 10)
    assert data2["minutesWatched"] == 15
    assert data2["minutesRemaining"] == 15

    # Verify state recalculated (not cached)
    assert data1["minutesWatched"] != data2["minutesWatched"]


# =============================================================================
# TIER 1 SAFETY INTEGRATION TESTS
# =============================================================================


@pytest.mark.tier1
def test_end_to_end_limit_calculation_with_db(test_client, test_db):
    """
    TIER 1 Integration Test: End-to-end daily limit calculation through API with real database.

    Verifies the complete flow: HTTP request → route → service → database query → response.

    Test ID: 4.1-INT-008
    Acceptance Criteria: AC4 (full integration test for limit calculation)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create mixed watch history (countable, manual, grace)
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            # Countable entry (12 minutes = 720 seconds)
            {
                "video_id": "vid1",
                "video_title": "Countable Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 720,
            },
            # Manual play entry (5 minutes = 300 seconds) - should NOT count
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
            # Grace play entry (3 minutes = 180 seconds) - should NOT count
            {
                "video_id": "vid3",
                "video_title": "Grace Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T12:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,
                "duration_watched_seconds": 180,
            },
        ],
    )

    # ACT: Call API endpoint (full stack integration)
    response = test_client.get("/api/limit/status")

    # ASSERT: Response should reflect only countable entry (12 minutes)
    assert response.status_code == 200

    data = response.json()
    assert data["date"] == today
    assert data["minutesWatched"] == 12, "manual_play or grace_play entries were counted"
    assert data["minutesRemaining"] == 18  # 30 - 12 = 18
    assert data["currentState"] == "normal"  # >10 min remaining

    # Verify database still has all 3 entries (nothing lost)
    all_history = test_db.execute(
        f"SELECT COUNT(*) as count FROM watch_history WHERE DATE(watched_at) = '{today}'"
    ).fetchone()
    assert all_history["count"] == 3, "Watch history entries were lost during query"


@pytest.mark.tier1
def test_db_query_uses_utc_date_function(test_db):
    """
    TIER 1 Integration Test: Verify database query uses DATE('now') for UTC.

    SQLite's DATE('now') returns UTC date, ensuring consistent timezone behavior.

    Test ID: 4.1-INT-011
    Acceptance Criteria: AC6 (database-level UTC enforcement)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history for "today" in UTC
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T14:30:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 900,  # 15 minutes
            }
        ],
    )

    # ACT: Query using DATE('now') directly (simulating get_watch_history_for_date query)
    # This tests that SQLite's DATE() function works correctly with UTC timestamps
    result = test_db.execute(
        """
        SELECT COUNT(*) as count
        FROM watch_history
        WHERE DATE(watched_at) = DATE('now')
        AND manual_play = 0
        AND grace_play = 0
        """
    ).fetchone()

    # ASSERT: Should find the entry if DATE('now') returns UTC date
    # If SQLite was using local timezone, this could fail
    assert result["count"] == 1, "DATE('now') did not return UTC date - timezone mismatch"

    # Verify the date from DATE('now') matches Python's UTC date
    sqlite_date = test_db.execute("SELECT DATE('now') as date").fetchone()
    assert (
        sqlite_date["date"] == today
    ), f"SQLite DATE('now') = {sqlite_date['date']} but Python UTC date = {today}"


# =============================================================================
# P1 INTEGRATION TESTS - DATABASE AND API
# =============================================================================


def test_watch_history_insert_with_all_fields(test_db):
    """
    P1 Integration Test: Verify watch history entry inserted with all fields.

    Test ID: 4.1-INT-001
    Acceptance Criteria: AC1 (watch history database tracking)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE
    today = datetime.now(timezone.utc).date().isoformat()

    # ACT: Insert watch history with all fields
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "test_video_123",
                "video_title": "Test Video Title",
                "channel_name": "Test Channel Name",
                "watched_at": f"{today}T14:30:15Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,
                "duration_watched_seconds": 425,
            }
        ],
    )

    # ASSERT: Verify all fields persisted
    result = test_db.execute(
        "SELECT * FROM watch_history WHERE video_id = 'test_video_123'"
    ).fetchone()

    assert result is not None
    assert result["video_id"] == "test_video_123"
    assert result["video_title"] == "Test Video Title"
    assert result["channel_name"] == "Test Channel Name"
    assert result["watched_at"] == f"{today}T14:30:15Z"
    assert result["completed"] == 1
    assert result["manual_play"] == 0
    assert result["grace_play"] == 1
    assert result["duration_watched_seconds"] == 425


def test_watched_at_stored_as_iso8601_utc(test_db):
    """
    P1 Integration Test: Verify watched_at stored as ISO 8601 UTC timestamp.

    Test ID: 4.1-INT-002
    Acceptance Criteria: AC1 (timestamps in ISO 8601 UTC format)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE
    today = datetime.now(timezone.utc).date().isoformat()
    timestamp_utc = f"{today}T08:30:45Z"

    # ACT: Insert watch history with UTC timestamp
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid_iso8601",
                "video_title": "Test",
                "channel_name": "Test",
                "watched_at": timestamp_utc,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        ],
    )

    # ASSERT: Timestamp matches ISO 8601 format with 'Z' suffix
    result = test_db.execute(
        "SELECT watched_at FROM watch_history WHERE video_id = 'vid_iso8601'"
    ).fetchone()

    assert result["watched_at"] == timestamp_utc
    assert result["watched_at"].endswith("Z"), "Timestamp should end with 'Z' for UTC"
    assert "T" in result["watched_at"], "Timestamp should contain 'T' separator"


def test_manual_play_flag_persists_correctly(test_db):
    """
    P1 Integration Test: Verify manual_play flag persists correctly in database.

    Test ID: 4.1-INT-003
    Acceptance Criteria: AC1 (manual_play flag persistence)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE
    today = datetime.now(timezone.utc).date().isoformat()

    # ACT: Insert entries with manual_play = 0 and 1
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "manual_0",
                "video_title": "Normal Video",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "manual_1",
                "video_title": "Manual Play Video",
                "channel_name": "Test",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 1,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # ASSERT: Both flags persisted correctly
    result_0 = test_db.execute(
        "SELECT manual_play FROM watch_history WHERE video_id = 'manual_0'"
    ).fetchone()
    result_1 = test_db.execute(
        "SELECT manual_play FROM watch_history WHERE video_id = 'manual_1'"
    ).fetchone()

    assert result_0["manual_play"] == 0
    assert result_1["manual_play"] == 1


def test_grace_play_flag_persists_correctly(test_db):
    """
    P1 Integration Test: Verify grace_play flag persists correctly in database.

    Test ID: 4.1-INT-004
    Acceptance Criteria: AC1 (grace_play flag persistence)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE
    today = datetime.now(timezone.utc).date().isoformat()

    # ACT: Insert entries with grace_play = 0 and 1
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "grace_0",
                "video_title": "Normal Video",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            },
            {
                "video_id": "grace_1",
                "video_title": "Grace Video",
                "channel_name": "Test",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,
                "duration_watched_seconds": 300,
            },
        ],
    )

    # ASSERT: Both flags persisted correctly
    result_0 = test_db.execute(
        "SELECT grace_play FROM watch_history WHERE video_id = 'grace_0'"
    ).fetchone()
    result_1 = test_db.execute(
        "SELECT grace_play FROM watch_history WHERE video_id = 'grace_1'"
    ).fetchone()

    assert result_0["grace_play"] == 0
    assert result_1["grace_play"] == 1


def test_limit_status_uses_settings_value(test_client, test_db):
    """
    P1 Integration Test: Verify GET /api/limit/status uses settings value.

    Test ID: 4.1-INT-005
    Acceptance Criteria: AC2 (daily limit retrieved from settings)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Settings fixture has daily_limit_minutes=30
    # Create watch history with 10 minutes watched
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            }
        ],
    )

    # ACT: Get limit status
    response = test_client.get("/api/limit/status")

    # ASSERT: Uses setting (30 minutes), calculates 20 remaining
    assert response.status_code == 200
    data = response.json()

    assert data["minutesWatched"] == 10
    assert data["minutesRemaining"] == 20  # 30 (setting) - 10 (watched)


def test_empty_watch_history_returns_zero_minutes(test_client, test_db):
    """
    P1 Integration Test: Verify empty watch history returns 0 minutes watched.

    Test ID: 4.1-INT-006
    Acceptance Criteria: AC3 (tracking begins on first video)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: No watch history (baseline state)

    # ACT: Get limit status
    response = test_client.get("/api/limit/status")

    # ASSERT: 0 minutes watched, full limit remaining
    assert response.status_code == 200
    data = response.json()

    assert data["minutesWatched"] == 0
    assert data["minutesRemaining"] == 30  # Full limit
    assert data["currentState"] == "normal"


def test_first_video_watch_increments_from_zero(test_client, test_db):
    """
    P1 Integration Test: Verify first video watch increments from 0.

    Test ID: 4.1-INT-007
    Acceptance Criteria: AC3 (tracking begins on first video)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Start with empty history
    response_before = test_client.get("/api/limit/status")
    assert response_before.json()["minutesWatched"] == 0

    # Insert first video watch (7 minutes)
    today = datetime.now(timezone.utc).date().isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "first_video",
                "video_title": "First Video",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 420,  # 7 minutes
            }
        ],
    )

    # ACT: Get limit status after first video
    response_after = test_client.get("/api/limit/status")

    # ASSERT: Incremented from 0 to 7 minutes
    assert response_after.status_code == 200
    data = response_after.json()

    assert data["minutesWatched"] == 7
    assert data["minutesRemaining"] == 23  # 30 - 7


def test_grace_state_persists_until_grace_video_watched(test_client, test_db):
    """
    P1 Integration Test: Verify grace state persists until grace video consumed.

    Test ID: 4.1-INT-010
    Acceptance Criteria: AC5 (grace screen offered, state persists)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history that reaches limit
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1800,  # 30 minutes
            }
        ],
    )

    # ACT 1: Get limit status (should be grace)
    response1 = test_client.get("/api/limit/status")
    data1 = response1.json()

    assert data1["currentState"] == "grace"
    assert data1["minutesRemaining"] == 0

    # ACT 2: Get status again (grace should persist)
    response2 = test_client.get("/api/limit/status")
    data2 = response2.json()

    assert data2["currentState"] == "grace", "Grace state should persist"

    # ACT 3: Consume grace video
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "grace_video",
                "video_title": "Grace Video",
                "channel_name": "Test",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,  # Grace video
                "duration_watched_seconds": 300,  # 5 minutes
            }
        ],
    )

    # ACT 4: Get status after grace consumed
    response3 = test_client.get("/api/limit/status")
    data3 = response3.json()

    # ASSERT: State should now be locked
    assert data3["currentState"] == "locked", "State should be locked after grace consumed"


def test_reset_returns_updated_limit_state(test_client, test_db):
    """
    P1 Integration Test: Verify POST /admin/limit/reset returns updated state.

    Test ID: 4.1-INT-014
    Acceptance Criteria: AC7 (reset returns updated limit info)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create authenticated session and watch history
    session_id = create_session()
    test_client.cookies.set("session_id", session_id)

    today = datetime.now(timezone.utc).date().isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Test Video",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 900,  # 15 minutes
            }
        ],
    )

    # ACT: Reset limit
    response = test_client.post("/admin/limit/reset")

    # ASSERT: Response contains updated limit state
    assert response.status_code == 200
    data = response.json()

    assert data["success"] is True
    assert "newLimit" in data
    assert data["newLimit"]["minutesWatched"] == 0
    assert data["newLimit"]["minutesRemaining"] == 30
    assert data["newLimit"]["currentState"] == "normal"


def test_watch_history_addition_reflects_immediately_in_status(test_client, test_db):
    """
    P1 Integration Test: Verify added watch history reflects immediately in status.

    Test ID: 4.1-INT-017
    Acceptance Criteria: AC8 (state recalculated from DB on each request)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Get initial status (should be 0)
    response1 = test_client.get("/api/limit/status")
    data1 = response1.json()
    assert data1["minutesWatched"] == 0

    # ACT: Add watch history (12 minutes)
    today = datetime.now(timezone.utc).date().isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "new_video",
                "video_title": "New Video",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 720,  # 12 minutes
            }
        ],
    )

    # ASSERT: Status immediately reflects change (no caching)
    response2 = test_client.get("/api/limit/status")
    data2 = response2.json()

    assert data2["minutesWatched"] == 12, "Change should reflect immediately"
    assert data2["minutesRemaining"] == 18


# =============================================================================
# P2 EDGE CASE TESTS
# =============================================================================


def test_reset_handles_db_connection_failure_gracefully(test_client, test_db, monkeypatch):
    """
    P2 Integration Test: Verify POST /admin/limit/reset handles DB failure gracefully.

    Test ID: 4.1-INT-015
    Acceptance Criteria: AC7 (error handling + rollback)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create authenticated session
    session_id = create_session()
    test_client.cookies.set("session_id", session_id)

    # Mock reset_daily_limit to raise an exception
    from backend.services import viewing_session

    original_reset = viewing_session.reset_daily_limit

    def mock_reset_failure(conn=None):
        raise Exception("Database connection lost")

    monkeypatch.setattr(viewing_session, "reset_daily_limit", mock_reset_failure)

    # ACT: Attempt to reset limit
    response = test_client.post("/admin/limit/reset")

    # ASSERT: Should return 500 with error message
    assert response.status_code == 500
    data = response.json()
    assert data["error"] == "Internal error"
    assert data["message"] == "Noe gikk galt"

    # Restore original function
    monkeypatch.setattr(viewing_session, "reset_daily_limit", original_reset)


def test_daily_limit_zero_triggers_immediate_grace(test_db):
    """
    P2 Integration Test: Verify daily limit = 0 immediately triggers grace state.

    Test ID: 4.1-INT-019
    Acceptance Criteria: Edge case - zero limit configuration
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Set daily limit to 0
    test_db.execute("UPDATE settings SET value = '0' WHERE key = 'daily_limit_minutes'")
    test_db.commit()

    # ACT: Get daily limit (no watch history needed)
    from backend.services.viewing_session import get_daily_limit

    daily_limit = get_daily_limit(conn=test_db)

    # ASSERT: Should be in grace state immediately (0 minutes remaining)
    assert daily_limit["minutesWatched"] == 0
    assert daily_limit["minutesRemaining"] == 0
    assert daily_limit["currentState"] == "grace"


def test_multiple_resets_per_day_no_limit(test_client, test_db):
    """
    P2 Integration Test: Verify multiple resets per day are allowed.

    Test ID: 4.1-INT-020
    Acceptance Criteria: AC7 (parent flexibility - unlimited resets)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create authenticated session
    session_id = create_session()
    test_client.cookies.set("session_id", session_id)

    today = datetime.now(timezone.utc).date().isoformat()

    # ACT 1: First reset
    response1 = test_client.post("/admin/limit/reset")
    assert response1.status_code == 200

    # Add watch history
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 600,  # 10 minutes
            }
        ],
    )

    # ACT 2: Second reset
    response2 = test_client.post("/admin/limit/reset")
    assert response2.status_code == 200
    data2 = response2.json()

    # ASSERT: Second reset succeeded
    assert data2["success"] is True
    assert data2["newLimit"]["minutesWatched"] == 0

    # Add more history
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid2",
                "video_title": "Video 2",
                "channel_name": "Test",
                "watched_at": f"{today}T11:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,  # 5 minutes
            }
        ],
    )

    # ACT 3: Third reset
    response3 = test_client.post("/admin/limit/reset")
    assert response3.status_code == 200
    data3 = response3.json()

    # ASSERT: Third reset also succeeded (no limit on resets)
    assert data3["success"] is True
    assert data3["newLimit"]["minutesWatched"] == 0


def test_child_at_limit_when_parent_resets_polling_detects(test_client, test_db):
    """
    P2 Integration Test: Verify child polling detects limit reset by parent.

    Test ID: 4.1-INT-021
    Acceptance Criteria: AC8 (state recalculated on each request, polling works)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history that reaches limit
    today = datetime.now(timezone.utc).date().isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "vid1",
                "video_title": "Video 1",
                "channel_name": "Test",
                "watched_at": f"{today}T10:00:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1800,  # 30 minutes
            }
        ],
    )

    # ACT 1: Child polls and sees grace state
    response1 = test_client.get("/api/limit/status")
    data1 = response1.json()
    assert data1["currentState"] == "grace"
    assert data1["minutesRemaining"] == 0

    # Parent resets limit (in authenticated session)
    session_id = create_session()
    test_client.cookies.set("session_id", session_id)
    reset_response = test_client.post("/admin/limit/reset")
    assert reset_response.status_code == 200

    # Remove session cookie (simulate child polling without auth)
    test_client.cookies.clear()

    # ACT 2: Child polls again (30 seconds later)
    response2 = test_client.get("/api/limit/status")
    data2 = response2.json()

    # ASSERT: Child sees reset state (normal, full limit restored)
    assert data2["currentState"] == "normal"
    assert data2["minutesWatched"] == 0
    assert data2["minutesRemaining"] == 30


def test_midnight_utc_transition_automatic_reset(test_db, monkeypatch):
    """
    P2 Integration Test: Verify automatic reset at midnight UTC date boundary.

    Test ID: 4.1-INT-022
    Acceptance Criteria: AC6 (midnight UTC reset - date boundary handling)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Create watch history for "yesterday" (2025-01-03)
    yesterday = "2025-01-03"

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "yesterday_video",
                "video_title": "Yesterday Video",
                "channel_name": "Test",
                "watched_at": f"{yesterday}T23:30:00Z",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1500,  # 25 minutes
            }
        ],
    )

    # ACT: Mock current time to "today" (2025-01-04) - after midnight UTC
    from backend.services import viewing_session

    utc_today = datetime(2025, 1, 4, 0, 30, 0, tzinfo=timezone.utc)

    with patch("backend.services.viewing_session.datetime") as mock_datetime:
        mock_datetime.now.return_value = utc_today
        mock_datetime.min = datetime.min
        mock_datetime.combine = datetime.combine
        mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

        daily_limit = viewing_session.get_daily_limit(conn=test_db)

    # ASSERT: Should automatically reset (yesterday's history doesn't count)
    assert daily_limit["date"] == "2025-01-04"
    assert daily_limit["minutesWatched"] == 0  # Yesterday's videos don't count
    assert daily_limit["minutesRemaining"] == 30
    assert daily_limit["currentState"] == "normal"


def test_db_connection_failure_during_get_limit_status(test_client, test_db, monkeypatch):
    """
    P2 Integration Test: Verify GET /api/limit/status handles DB connection failure.

    Test ID: 4.1-INT-023
    Acceptance Criteria: Error handling (503 Service Unavailable)
    Story: 4.1 - Time-Based Viewing Limits
    """
    # ARRANGE: Mock get_daily_limit to raise database error
    from backend.services import viewing_session

    def mock_db_failure(conn=None):
        raise Exception("Database connection timeout")

    monkeypatch.setattr(viewing_session, "get_daily_limit", mock_db_failure)

    # ACT: Call API endpoint
    response = test_client.get("/api/limit/status")

    # ASSERT: Should return 503 Service Unavailable with Norwegian error
    assert response.status_code == 503
    data = response.json()
    assert data["error"] == "ServiceUnavailable"
    assert data["message"] == "Kunne ikke hente daglig grense"
