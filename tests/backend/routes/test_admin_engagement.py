"""
Backend tests for POST /admin/engagement/reset endpoint.

Tests admin engagement reset functionality including:
- Deleting all engagement data
- Selective video reset preserving manual_play/grace_play
- SQL injection prevention (TIER 1 Rule 6)
- Authentication requirement (TIER 2 Rule 10)
"""

import pytest
from datetime import datetime, timezone, timedelta
from tests.backend.conftest import (
    create_test_video,
    setup_test_videos,
    setup_content_source,
    insert_watch_history,
)


@pytest.mark.tier1
def test_reset_endpoint_requires_authentication(test_client):
    """
    Test 4.4-INT-014: Reset endpoint requires authentication (TIER 2 Rule 10).

    TIER 2 Rule 10: Admin endpoints must verify authentication via require_auth().

    This test verifies that unauthorized requests are rejected with 401 status.

    Scenario:
    - POST /admin/engagement/reset without authentication

    Expected:
    - 401 Unauthorized response
    """
    # Act: Call endpoint without authentication
    response = test_client.post("/admin/engagement/reset")

    # Assert: 401 Unauthorized
    assert response.status_code == 401
    data = response.json()
    assert "detail" in data


@pytest.mark.integration
def test_reset_all_engagement_data(test_client, test_db):
    """
    Test 4.4-INT-011: POST /admin/engagement/reset deletes all engagement data.

    This test verifies that the reset endpoint can delete all countable
    watch history entries (manual_play=0 AND grace_play=0) when no video_id specified.

    Scenario:
    - 3 videos with watch history:
      - video_1: 5 normal watches (countable)
      - video_2: 3 normal watches + 2 manual_play watches (5 total, 3 countable)
      - video_3: 2 grace_play watches (not countable)
    - POST /admin/engagement/reset with no body

    Expected:
    - Only countable entries deleted (5 + 3 = 8 entries)
    - manual_play and grace_play preserved (2 + 2 = 4 entries remain)
    - Success response with deletedCount=8
    """
    # Arrange: Create admin session
    from backend.auth import create_session

    session_id = create_session()

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    videos = [
        create_test_video(video_id=f"video_{i}", content_source_id=source_id) for i in range(1, 4)
    ]
    setup_test_videos(test_db, videos)

    # Create watch history with different types
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []

    # video_1: 5 normal watches (countable)
    for _ in range(5):
        watch_records.append(
            {
                "video_id": "video_1",
                "video_title": "Video 1",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 0,  # Countable
                "grace_play": 0,  # Countable
                "duration_watched_seconds": 300,
            }
        )

    # video_2: 3 normal watches + 2 manual_play watches
    for i in range(5):
        watch_records.append(
            {
                "video_id": "video_2",
                "video_title": "Video 2",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 1 if i >= 3 else 0,  # Last 2 are manual_play
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    # video_3: 2 grace_play watches (not countable)
    for _ in range(2):
        watch_records.append(
            {
                "video_id": "video_3",
                "video_title": "Video 3",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,  # Grace play (not countable)
                "duration_watched_seconds": 300,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Verify initial state: 12 total watch history entries
    cursor = test_db.execute("SELECT COUNT(*) FROM watch_history")
    initial_count = cursor.fetchone()[0]
    assert initial_count == 12, f"Expected 12 initial entries, got {initial_count}"

    # Act: Reset all engagement data (authenticated)
    response = test_client.post("/admin/engagement/reset", cookies={"session_id": session_id})

    # Assert: Success response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Engasjementsdata tilbakestilt"
    assert data["deletedCount"] == 8  # 5 + 3 countable entries deleted

    # Verify database state: Only manual_play and grace_play remain
    cursor = test_db.execute("SELECT COUNT(*) FROM watch_history")
    remaining_count = cursor.fetchone()[0]
    assert remaining_count == 4, f"Expected 4 remaining entries, got {remaining_count}"

    # Verify remaining entries are all manual_play=1 OR grace_play=1
    cursor = test_db.execute(
        "SELECT COUNT(*) FROM watch_history WHERE manual_play = 0 AND grace_play = 0"
    )
    countable_remaining = cursor.fetchone()[0]
    assert (
        countable_remaining == 0
    ), f"Expected 0 countable entries remaining, got {countable_remaining}"


@pytest.mark.integration
def test_reset_single_video_preserves_manual_grace(test_client, test_db):
    """
    Test 4.4-INT-012: Reset single video preserving manual_play/grace_play.

    This test verifies that selective reset (with videoId) only deletes countable
    entries for that specific video, preserving manual_play and grace_play entries.

    Scenario:
    - video_target: 5 normal watches + 2 manual_play watches
    - video_other: 3 normal watches (should not be affected)
    - POST /admin/engagement/reset with {"videoId": "video_target"}

    Expected:
    - Only video_target's countable entries deleted (5 entries)
    - video_target's manual_play preserved (2 entries remain)
    - video_other untouched (3 entries remain)
    - Success response with deletedCount=5
    """
    # Arrange: Create admin session
    from backend.auth import create_session

    session_id = create_session()

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    videos = [
        create_test_video(video_id="video_target", content_source_id=source_id),
        create_test_video(video_id="video_other", content_source_id=source_id),
    ]
    setup_test_videos(test_db, videos)

    # Create watch history
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []

    # video_target: 5 normal watches + 2 manual_play watches
    for i in range(7):
        watch_records.append(
            {
                "video_id": "video_target",
                "video_title": "Target Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 1 if i >= 5 else 0,  # Last 2 are manual_play
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    # video_other: 3 normal watches (should be untouched)
    for _ in range(3):
        watch_records.append(
            {
                "video_id": "video_other",
                "video_title": "Other Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Verify initial state: 10 total entries
    cursor = test_db.execute("SELECT COUNT(*) FROM watch_history")
    initial_count = cursor.fetchone()[0]
    assert initial_count == 10, f"Expected 10 initial entries, got {initial_count}"

    # Act: Reset engagement for video_target only (authenticated)
    response = test_client.post(
        "/admin/engagement/reset",
        json={"videoId": "video_target"},
        cookies={"session_id": session_id},
    )

    # Assert: Success response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["deletedCount"] == 5  # Only video_target's 5 countable entries deleted

    # Verify database state: 5 entries remain (2 manual_play + 3 from video_other)
    cursor = test_db.execute("SELECT COUNT(*) FROM watch_history")
    remaining_count = cursor.fetchone()[0]
    assert remaining_count == 5, f"Expected 5 remaining entries, got {remaining_count}"

    # Verify video_target: Only manual_play entries remain
    cursor = test_db.execute("SELECT COUNT(*) FROM watch_history WHERE video_id = 'video_target'")
    target_remaining = cursor.fetchone()[0]
    assert (
        target_remaining == 2
    ), f"Expected 2 manual_play entries for video_target, got {target_remaining}"

    cursor = test_db.execute(
        """
        SELECT COUNT(*) FROM watch_history
        WHERE video_id = 'video_target' AND manual_play = 1
    """
    )
    target_manual = cursor.fetchone()[0]
    assert (
        target_manual == 2
    ), f"Expected 2 manual_play entries for video_target, got {target_manual}"

    # Verify video_other: All 3 entries untouched
    cursor = test_db.execute("SELECT COUNT(*) FROM watch_history WHERE video_id = 'video_other'")
    other_remaining = cursor.fetchone()[0]
    assert other_remaining == 3, f"Expected 3 entries for video_other, got {other_remaining}"


@pytest.mark.tier1
def test_reset_uses_sql_placeholders(test_db):
    """
    Test 4.4-INT-013: Verify SQL placeholders used (TIER 1 Rule 6).

    TIER 1 Rule 6: ALWAYS use SQL placeholders to prevent SQL injection.

    This test inspects the delete_engagement_history function source code
    to ensure SQL placeholders (?) are used, never string formatting.

    Expected:
    - Query uses '?' placeholders
    - No f-strings or % formatting in SQL
    - Parameters passed via tuple
    """
    import inspect
    from backend.db.queries import delete_engagement_history

    # Get source code of delete_engagement_history function
    source = inspect.getsource(delete_engagement_history)

    # Verify SQL placeholders are used (? marker)
    assert "WHERE video_id = ?" in source, "Must use SQL placeholder for video_id"
    assert "WHERE manual_play = 0" in source, "Must filter manual_play in WHERE clause"
    assert (
        "WHERE grace_play = 0" in source or "AND grace_play = 0" in source
    ), "Must filter grace_play in WHERE clause"

    # Verify NO string formatting used (SQL injection vectors)
    sql_injection_patterns = [
        'f"DELETE FROM',  # f-strings
        "f'DELETE FROM",  # f-strings
        '% "DELETE FROM',  # % formatting
        "% 'DELETE FROM",  # % formatting
        ".format(",  # .format() method
    ]

    for pattern in sql_injection_patterns:
        assert pattern not in source, f"SQL injection risk: Found '{pattern}' in source code"

    # Verify placeholder parameters are passed
    assert (
        "conn.execute(query, params)" in source
        or "conn.execute(query, params) if params else" in source
    ), "Must pass parameters tuple to execute()"
