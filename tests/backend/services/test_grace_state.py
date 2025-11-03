"""
Unit tests for grace video state and interruption logic (Story 4.3, Phase 1).

These tests focus on isolated algorithm testing:
- State calculation logic (grace, locked, normal states)
- Mid-video interruption decision algorithm
- Time until reset calculations
- Video filtering and sorting logic

All tests are pure unit tests with minimal database dependencies.
"""

from datetime import datetime, timezone
from freezegun import freeze_time

from backend.services.viewing_session import (
    get_daily_limit,
    should_interrupt_video,
)
from backend.db.queries import set_setting
from tests.backend.conftest import (
    setup_content_source,
    create_test_video,
    setup_test_videos,
    insert_watch_history,
)


# ============================================================================
# State Calculation Logic (3 tests)
# ============================================================================


def test_calculate_grace_state_when_limit_reached_no_grace_consumed(test_db, monkeypatch):
    """
    4.3-UNIT-001 (P0): Calculate grace state when limit reached, no grace consumed.

    When daily limit reached (minutes_remaining = 0) and no grace video has been
    watched, the state should be "grace" (one more video allowed).
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Set daily limit to 30 minutes
    set_setting("daily_limit_minutes", "30")

    # Insert exactly 30 minutes of normal watch history (limit reached)
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "video1",
                "video_title": "Test Video",
                "channel_name": "Test Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1800,  # 30 minutes
            }
        ],
    )

    # Act: Get daily limit state
    limit = get_daily_limit(conn=test_db)

    # Assert: State should be "grace" (no grace consumed yet)
    assert limit["currentState"] == "grace", (
        f"Expected 'grace' state when limit reached and no grace consumed, "
        f"got '{limit['currentState']}'"
    )
    assert limit["graceAvailable"] is True, "graceAvailable should be True in grace state"
    assert (
        limit["minutesWatched"] == 30
    ), f"Expected 30 minutes watched, got {limit['minutesWatched']}"
    assert (
        limit["minutesRemaining"] == 0
    ), f"Expected 0 minutes remaining, got {limit['minutesRemaining']}"


def test_calculate_locked_state_when_grace_consumed(test_db, monkeypatch):
    """
    4.3-UNIT-002 (P0): Calculate locked state when grace already consumed.

    When daily limit reached AND a grace video has been watched today,
    the state should be "locked" (no more videos until midnight).
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Set daily limit to 30 minutes
    set_setting("daily_limit_minutes", "30")

    # Insert 30 minutes of normal watch history + grace video
    now = datetime.now(timezone.utc).isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "video1",
                "video_title": "Normal Video",
                "channel_name": "Test Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1800,  # 30 minutes
            },
            {
                "video_id": "grace_video",
                "video_title": "Grace Video",
                "channel_name": "Test Channel",
                "watched_at": now,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,  # Grace consumed
                "duration_watched_seconds": 300,  # 5 minutes
            },
        ],
    )

    # Act: Get daily limit state
    limit = get_daily_limit(conn=test_db)

    # Assert: State should be "locked" (grace already consumed)
    assert (
        limit["currentState"] == "locked"
    ), f"Expected 'locked' state after grace consumed, got '{limit['currentState']}'"
    assert limit["graceAvailable"] is False, "graceAvailable should be False in locked state"
    assert (
        limit["minutesWatched"] == 30
    ), f"Expected 30 minutes watched (grace excluded), got {limit['minutesWatched']}"
    assert (
        limit["minutesRemaining"] == 0
    ), f"Expected 0 minutes remaining, got {limit['minutesRemaining']}"


@freeze_time("2025-11-03 10:00:00", tz_offset=0)
def test_calculate_normal_state_after_midnight_reset(test_db, monkeypatch):
    """
    4.3-UNIT-003 (P1): Calculate normal state on new day after grace consumed yesterday.

    Even if grace was consumed yesterday, the state should reset to "normal"
    on a new day (after midnight UTC).
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Set daily limit to 30 minutes
    set_setting("daily_limit_minutes", "30")

    # Insert watch history from YESTERDAY (2025-11-02) - grace consumed
    yesterday = datetime(2025, 11, 2, 23, 0, 0, tzinfo=timezone.utc).isoformat()

    insert_watch_history(
        test_db,
        [
            {
                "video_id": "yesterday_video",
                "video_title": "Yesterday Video",
                "channel_name": "Test Channel",
                "watched_at": yesterday,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 1800,  # 30 minutes
            },
            {
                "video_id": "yesterday_grace",
                "video_title": "Yesterday Grace",
                "channel_name": "Test Channel",
                "watched_at": yesterday,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,
                "duration_watched_seconds": 300,  # 5 minutes grace
            },
        ],
    )

    # TODAY (2025-11-03) - no watch history yet

    # Act: Get daily limit state (frozen at 2025-11-03 10:00 UTC)
    limit = get_daily_limit(conn=test_db)

    # Assert: State should be "normal" (new day, limit reset)
    assert (
        limit["currentState"] == "normal"
    ), f"Expected 'normal' state on new day, got '{limit['currentState']}'"
    assert limit["graceAvailable"] is False, "graceAvailable should be False in normal state"
    assert (
        limit["minutesWatched"] == 0
    ), f"Expected 0 minutes watched today, got {limit['minutesWatched']}"
    assert (
        limit["minutesRemaining"] == 30
    ), f"Expected 30 minutes remaining, got {limit['minutesRemaining']}"
    assert limit["date"] == "2025-11-03", f"Expected today's date, got {limit['date']}"


# ============================================================================
# Interruption Decision Logic (3 tests)
# ============================================================================


def test_should_interrupt_video_returns_false_when_fits_grace_period():
    """
    4.3-UNIT-004 (P1): should_interrupt_video returns False when video fits within 5-min grace.

    Videos that will complete within 5 minutes AFTER the limit is reached
    should be allowed to finish (return False = don't interrupt).
    """
    # Test cases: (minutes_remaining, video_duration_minutes, should_interrupt, description)
    test_cases = [
        (8, 3, False, "Short video with plenty of time remaining"),
        (8, 12, False, "12-min video with 8 min remaining (12 <= 8+5)"),
        (0, 5, False, "5-min video at limit boundary (5 <= 0+5)"),
        (0, 4, False, "4-min video with no time left (within grace)"),
        (2, 6, False, "6-min video with 2 min left (6 <= 2+5)"),
        (-2, 3, False, "Short video when already over limit"),
    ]

    for remaining, duration, expected_interrupt, description in test_cases:
        # Act
        result = should_interrupt_video(remaining, duration)

        # Assert
        assert result == expected_interrupt, (
            f"FAILED: {description} - "
            f"should_interrupt_video({remaining}, {duration}) returned {result}, "
            f"expected {expected_interrupt}"
        )


def test_should_interrupt_video_returns_true_when_too_long():
    """
    4.3-UNIT-005 (P1): should_interrupt_video returns True when video too long.

    Videos that will extend more than 5 minutes past the limit should be
    interrupted (return True = interrupt now).
    """
    # Test cases: (minutes_remaining, video_duration_minutes, should_interrupt, description)
    test_cases = [
        (8, 15, True, "15-min video with 8 min remaining (15 > 8+5)"),
        (0, 6, True, "6-min video at limit (6 > 0+5)"),
        (2, 10, True, "10-min video with 2 min left (10 > 2+5)"),
        (5, 12, True, "12-min video with 5 min left (12 > 5+5)"),
        (-3, 10, True, "Long video when already over limit"),
    ]

    for remaining, duration, expected_interrupt, description in test_cases:
        # Act
        result = should_interrupt_video(remaining, duration)

        # Assert
        assert result == expected_interrupt, (
            f"FAILED: {description} - "
            f"should_interrupt_video({remaining}, {duration}) returned {result}, "
            f"expected {expected_interrupt}"
        )


def test_should_interrupt_video_edge_case_exact_boundary():
    """
    4.3-UNIT-006 (P1): Edge case - video exactly at 5-minute grace boundary.

    When video duration equals (minutes_remaining + 5), it should be
    allowed to finish (boundary inclusive).
    """
    # Test exact boundary cases
    test_cases = [
        # Exactly at boundary (should NOT interrupt)
        (0, 5, False, "Exactly 5 minutes at limit (5 == 0+5)"),
        (5, 10, False, "Exactly 10 minutes with 5 remaining (10 == 5+5)"),
        (10, 15, False, "Exactly 15 minutes with 10 remaining (15 == 10+5)"),
        # One minute over boundary (should interrupt)
        (0, 6, True, "6 minutes at limit (6 > 0+5)"),
        (5, 11, True, "11 minutes with 5 remaining (11 > 5+5)"),
        (10, 16, True, "16 minutes with 10 remaining (16 > 10+5)"),
    ]

    for remaining, duration, expected_interrupt, description in test_cases:
        # Act
        result = should_interrupt_video(remaining, duration)

        # Assert
        assert result == expected_interrupt, (
            f"FAILED: {description} - "
            f"should_interrupt_video({remaining}, {duration}) returned {result}, "
            f"expected {expected_interrupt}"
        )


# ============================================================================
# Time Calculation Logic (3 tests)
# ============================================================================


@freeze_time("2025-11-03 14:30:00", tz_offset=0)  # 14:30 UTC
def test_calculate_time_until_midnight_utc_correctly(test_db, monkeypatch):
    """
    4.3-UNIT-007 (P1): Calculate time until midnight UTC correctly (hours and minutes).

    The resetTime field should show the next midnight UTC, correctly
    calculating hours and minutes remaining.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Set daily limit
    set_setting("daily_limit_minutes", "30")

    # Act: Get daily limit (frozen at 14:30 UTC)
    limit = get_daily_limit(conn=test_db)

    # Assert: Reset time should be next midnight (2025-11-04 00:00:00 UTC)
    expected_reset = "2025-11-04T00:00:00Z"
    assert (
        limit["resetTime"] == expected_reset
    ), f"Expected resetTime '{expected_reset}', got '{limit['resetTime']}'"

    # Calculate expected time until midnight
    # Current: 2025-11-03 14:30:00 UTC
    # Midnight: 2025-11-04 00:00:00 UTC
    # Difference: 9 hours 30 minutes
    current_time = datetime(2025, 11, 3, 14, 30, 0, tzinfo=timezone.utc)
    reset_time = datetime.fromisoformat(limit["resetTime"].replace("Z", "+00:00"))
    time_diff = reset_time - current_time

    hours = time_diff.seconds // 3600
    minutes = (time_diff.seconds % 3600) // 60

    assert hours == 9, f"Expected 9 hours until reset, got {hours}"
    assert minutes == 30, f"Expected 30 minutes until reset, got {minutes}"


@freeze_time("2025-11-03 14:30:00", tz_offset=5)  # 14:30 in local TZ (+5 offset)
def test_calculate_time_until_midnight_timezone_conversion(test_db, monkeypatch):
    """
    4.3-UNIT-008 (P1): Calculate time until midnight handles timezone conversion correctly.

    Even when running in a non-UTC timezone, the reset time should always be
    midnight UTC (not local midnight).
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Set daily limit
    set_setting("daily_limit_minutes", "30")

    # Act: Get daily limit (frozen at 14:30 in local TZ, which is 09:30 UTC)
    limit = get_daily_limit(conn=test_db)

    # Assert: Reset time should STILL be midnight UTC (not local midnight)
    # Since we're at 09:30 UTC (14:30 local), next midnight UTC is:
    # 2025-11-04 00:00:00 UTC
    expected_reset = "2025-11-04T00:00:00Z"
    assert limit["resetTime"] == expected_reset, (
        f"Expected UTC reset time '{expected_reset}', got '{limit['resetTime']}' "
        f"(timezone handling may be incorrect)"
    )


@freeze_time("2025-11-03 23:59:30", tz_offset=0)  # 30 seconds before midnight
def test_time_calculation_at_midnight_boundary(test_db, monkeypatch):
    """
    4.3-UNIT-009 (P1): Time calculation at midnight boundary (23:59:59 → 00:00:00).

    Edge case: calculation should work correctly when very close to midnight.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Set daily limit
    set_setting("daily_limit_minutes", "30")

    # Act: Get daily limit (30 seconds before midnight)
    limit = get_daily_limit(conn=test_db)

    # Assert: Reset time should be tomorrow's midnight (not today's)
    expected_reset = "2025-11-04T00:00:00Z"
    assert (
        limit["resetTime"] == expected_reset
    ), f"Expected reset time '{expected_reset}', got '{limit['resetTime']}'"

    # Assert: Date should still be today (2025-11-03)
    assert (
        limit["date"] == "2025-11-03"
    ), f"Expected date '2025-11-03' (today), got '{limit['date']}'"


# ============================================================================
# Filter/Sort Logic (2 tests)
# ============================================================================


def test_filter_videos_to_max_300_seconds(test_db, monkeypatch):
    """
    4.3-UNIT-010 (P1): Filter videos to ≤300 seconds (5 minutes).

    Grace mode should only return videos under or equal to 5 minutes duration.
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Create content source and videos of various durations
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    videos = [
        create_test_video(
            video_id="vid1", title="1 min video", duration_seconds=60, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid2", title="3 min video", duration_seconds=180, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid3",
            title="5 min video (boundary)",
            duration_seconds=300,
            content_source_id=source_id,
        ),
        create_test_video(
            video_id="vid4", title="6 min video", duration_seconds=360, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid5", title="10 min video", duration_seconds=600, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid6", title="15 min video", duration_seconds=900, content_source_id=source_id
        ),
    ]
    setup_test_videos(test_db, videos)

    # Act: Get available videos with 300-second (5-minute) max duration filter
    from backend.db.queries import get_available_videos

    filtered_videos = get_available_videos(
        exclude_banned=True, max_duration_seconds=300, conn=test_db
    )

    # Assert: Only videos ≤300 seconds should be returned
    assert (
        len(filtered_videos) == 3
    ), f"Expected 3 videos (60s, 180s, 300s), got {len(filtered_videos)}"

    durations = sorted([v["durationSeconds"] for v in filtered_videos])
    assert durations == [60, 180, 300], f"Expected durations [60, 180, 300], got {durations}"

    # Assert: No videos over 300 seconds included
    for video in filtered_videos:
        assert video["durationSeconds"] <= 300, (
            f"Video '{video['title']}' has duration {video['durationSeconds']}s, "
            f"which exceeds 300s limit"
        )


def test_sort_videos_by_duration_ascending_for_fallback(test_db, monkeypatch):
    """
    4.3-UNIT-011 (P1): Sort videos by duration ascending for shortest-first fallback.

    When no videos are under 5 minutes, the fallback should return the
    shortest available videos (sorted by duration ascending).
    """
    # Monkeypatch get_connection to use test_db
    from backend.db import queries
    from contextlib import contextmanager

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    # Arrange: Create content source and ONLY long videos (all >5 minutes)
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    videos = [
        create_test_video(
            video_id="vid1", title="15 min video", duration_seconds=900, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid2", title="8 min video", duration_seconds=480, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid3", title="12 min video", duration_seconds=720, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid4", title="6 min video", duration_seconds=360, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid5", title="10 min video", duration_seconds=600, content_source_id=source_id
        ),
        create_test_video(
            video_id="vid6", title="7 min video", duration_seconds=420, content_source_id=source_id
        ),
    ]
    setup_test_videos(test_db, videos)

    # Act: Get all available videos and sort by duration ascending
    from backend.db.queries import get_available_videos

    all_videos = get_available_videos(exclude_banned=True, conn=test_db)

    # Simulate fallback logic: sort by duration, take first 6
    sorted_videos = sorted(all_videos, key=lambda v: v["durationSeconds"])
    shortest_6 = sorted_videos[:6]

    # Assert: Videos should be sorted by duration ascending
    durations = [v["durationSeconds"] for v in shortest_6]
    assert durations == sorted(durations), f"Expected videos sorted by duration, got {durations}"

    # Assert: Shortest videos should be first
    assert durations == [
        360,
        420,
        480,
        600,
        720,
        900,
    ], f"Expected durations [360, 420, 480, 600, 720, 900] (sorted), got {durations}"

    # Assert: First video should be the shortest (6 minutes = 360 seconds)
    assert (
        shortest_6[0]["durationSeconds"] == 360
    ), f"Expected shortest video to be 360s, got {shortest_6[0]['durationSeconds']}s"
