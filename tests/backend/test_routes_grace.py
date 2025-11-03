"""
Integration tests for grace video routes and API (Story 4.3, Task 16).

Tests grace state transitions, video filtering, logging, and mid-video
interruption logic via API endpoints.

Target: 90% coverage of grace-related code
"""

from datetime import datetime, timezone

from tests.backend.conftest import (
    setup_content_source,
    create_test_video,
    setup_test_videos,
)


def test_grace_state_when_limit_reached_no_grace_consumed(test_client, test_db):
    """
    AC 1, 4: Grace screen appears when limit reached, one grace per day.

    Verifies that when daily limit is reached and no grace consumed,
    the API returns currentState="grace" and graceAvailable=true.
    """
    # Arrange: Set up videos and watch history to reach limit
    source_id = setup_content_source(test_db)
    videos = [
        create_test_video(
            video_id="video1",
            title="Test Video 1",
            content_source_id=source_id,
            duration_seconds=1800,  # 30 minutes
        ),
    ]
    setup_test_videos(test_db, videos)

    # Insert watch history: 30 minutes watched (exactly at limit)
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "video1",
            "Test Video 1",
            "Test Channel",
            datetime.now(timezone.utc).isoformat(),
            1,  # completed
            0,  # manual_play
            0,  # grace_play
            1800,  # 30 minutes
        ),
    )
    test_db.commit()

    # Act: Get limit status
    response = test_client.get("/api/limit/status")

    # Assert: Response is successful
    assert response.status_code == 200
    data = response.json()

    # Assert: State is grace, grace available
    assert data["currentState"] == "grace", f"Expected 'grace' state, got {data['currentState']}"
    assert data["graceAvailable"] is True, "Grace should be available when not consumed"
    assert (
        data["minutesWatched"] == 30
    ), f"Expected 30 minutes watched, got {data['minutesWatched']}"
    assert (
        data["minutesRemaining"] == 0
    ), f"Expected 0 minutes remaining, got {data['minutesRemaining']}"


def test_locked_state_after_grace_consumed(test_client, test_db):
    """
    AC 6: After grace video, only goodbye screen shown (locked state).

    Verifies that after grace video is consumed, API returns
    currentState="locked" and graceAvailable=false.
    """
    # Arrange: Reach limit
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "video1",
            "Test Video",
            "Test Channel",
            datetime.now(timezone.utc).isoformat(),
            1,
            0,
            0,
            1800,  # 30 minutes - at limit
        ),
    )

    # Consume grace video
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "video2",
            "Grace Video",
            "Test Channel",
            datetime.now(timezone.utc).isoformat(),
            1,
            0,
            1,  # grace_play=true
            300,  # 5 minutes
        ),
    )
    test_db.commit()

    # Act: Get limit status
    response = test_client.get("/api/limit/status")

    # Assert: Response is successful
    assert response.status_code == 200
    data = response.json()

    # Assert: State is locked, grace NOT available
    assert data["currentState"] == "locked", f"Expected 'locked' state, got {data['currentState']}"
    assert data["graceAvailable"] is False, "Grace should NOT be available after consumption"
    assert data["minutesWatched"] == 30, "Grace videos should not count toward limit"


def test_grace_videos_max_5_minutes(test_client, test_db):
    """
    AC 12: Grace videos max 5 minutes duration.

    Verifies that when in grace state, GET /api/videos returns only
    videos with duration ≤ 300 seconds (5 minutes).
    """
    # Arrange: Create videos with various durations
    source_id = setup_content_source(test_db)
    videos = [
        create_test_video(
            video_id="short1",
            title="Short Video 1",
            content_source_id=source_id,
            duration_seconds=180,  # 3 minutes - should appear
        ),
        create_test_video(
            video_id="short2",
            title="Short Video 2",
            content_source_id=source_id,
            duration_seconds=300,  # 5 minutes exactly - should appear
        ),
        create_test_video(
            video_id="long1",
            title="Long Video 1",
            content_source_id=source_id,
            duration_seconds=420,  # 7 minutes - should NOT appear
        ),
        create_test_video(
            video_id="long2",
            title="Long Video 2",
            content_source_id=source_id,
            duration_seconds=600,  # 10 minutes - should NOT appear
        ),
    ]
    setup_test_videos(test_db, videos)

    # Reach limit
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("video1", "Test", "Test", datetime.now(timezone.utc).isoformat(), 1, 0, 0, 1800),
    )
    test_db.commit()

    # Act: Get videos for grace mode
    response = test_client.get("/api/videos?count=6")

    # Assert: Response is successful
    assert response.status_code == 200
    data = response.json()

    # Assert: Only videos ≤ 5 minutes returned
    assert len(data["videos"]) == 2, f"Expected 2 short videos, got {len(data['videos'])}"

    video_ids = [v["videoId"] for v in data["videos"]]
    assert "short1" in video_ids, "Short video 1 (3 min) should be available"
    assert "short2" in video_ids, "Short video 2 (5 min) should be available"
    assert "long1" not in video_ids, "Long video 1 (7 min) should NOT be available"
    assert "long2" not in video_ids, "Long video 2 (10 min) should NOT be available"

    # Assert: All returned videos are ≤ 300 seconds
    for video in data["videos"]:
        assert video["durationSeconds"] <= 300, (
            f"Video {video['videoId']} has duration {video['durationSeconds']}s, "
            f"exceeds 300s grace limit"
        )


def test_grace_grid_returns_4_to_6_videos(test_client, test_db):
    """
    AC 11: Grace screen shows 4-6 videos (smaller grid).
    INT-006 (P0): Verify GET /api/videos returns correct count in grace mode.

    Verifies that when in grace state, the API returns between 4-6 videos
    instead of the normal 9, for easier selection by children.
    """
    # Arrange: Create 10+ videos (all short enough for grace)
    source_id = setup_content_source(test_db)
    videos = [
        create_test_video(
            video_id=f"short{i}",
            title=f"Short Video {i}",
            content_source_id=source_id,
            duration_seconds=180 + (i * 10),  # 3-5 minutes
        )
        for i in range(10)
    ]
    setup_test_videos(test_db, videos)

    # Reach limit to enter grace state
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("video1", "Test", "Test", datetime.now(timezone.utc).isoformat(), 1, 0, 0, 1800),
    )
    test_db.commit()

    # Act: Get videos in grace mode with default count (should be 4-6, not 9)
    response = test_client.get("/api/videos")

    # Assert: Response is successful
    assert response.status_code == 200
    data = response.json()

    # Assert: Returns 4-6 videos (grace grid size), not 9 (normal grid)
    video_count = len(data["videos"])
    assert 4 <= video_count <= 6, (
        f"Grace mode should return 4-6 videos for easier selection, " f"got {video_count} videos"
    )

    # Assert: State confirms we're in grace mode
    assert (
        data["dailyLimit"]["currentState"] == "grace"
    ), f"Expected grace state, got {data['dailyLimit']['currentState']}"

    # Act: Explicitly request 6 videos (grace mode maximum)
    response_6 = test_client.get("/api/videos?count=6")
    data_6 = response_6.json()

    # Assert: Returns 6 videos when explicitly requested
    assert len(data_6["videos"]) == 6, (
        f"Should return 6 videos when count=6 in grace mode, " f"got {len(data_6['videos'])}"
    )


def test_grace_video_fallback_to_shortest(test_client, test_db):
    """
    AC 13: Fallback to shortest videos if none under 5 minutes.

    Verifies that if no videos are ≤ 5 minutes, grace mode returns
    the 6 shortest videos sorted by duration.
    """
    # Arrange: Create only long videos
    source_id = setup_content_source(test_db)
    videos = [
        create_test_video(
            video_id="long1",
            title="Long Video 1",
            content_source_id=source_id,
            duration_seconds=420,  # 7 minutes - shortest
        ),
        create_test_video(
            video_id="long2",
            title="Long Video 2",
            content_source_id=source_id,
            duration_seconds=480,  # 8 minutes
        ),
        create_test_video(
            video_id="long3",
            title="Long Video 3",
            content_source_id=source_id,
            duration_seconds=540,  # 9 minutes
        ),
        create_test_video(
            video_id="long4",
            title="Long Video 4",
            content_source_id=source_id,
            duration_seconds=600,  # 10 minutes
        ),
    ]
    setup_test_videos(test_db, videos)

    # Reach limit
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("video1", "Test", "Test", datetime.now(timezone.utc).isoformat(), 1, 0, 0, 1800),
    )
    test_db.commit()

    # Act: Get videos for grace mode
    response = test_client.get("/api/videos?count=6")

    # Assert: Response is successful
    assert response.status_code == 200
    data = response.json()

    # Assert: Returns all 4 long videos (less than 6 available)
    assert len(data["videos"]) == 4, f"Expected 4 videos (fallback), got {len(data['videos'])}"

    # Assert: Videos are sorted by duration (shortest first)
    durations = [v["durationSeconds"] for v in data["videos"]]
    assert durations == sorted(durations), f"Videos should be sorted by duration, got {durations}"
    assert durations[0] == 420, "Shortest video (7 min) should be first"


def test_grace_video_logging_with_flags(test_client, test_db):
    """
    AC 5, 7: Grace video logged with grace_play=true and includes flags/duration.

    Verifies that POST /api/videos/watch with gracePlay=true correctly
    logs the watch history with proper flags.
    """
    # Arrange: Set up video and reach limit
    source_id = setup_content_source(test_db)
    videos = [
        create_test_video(
            video_id="grace_video",
            title="Grace Video",
            content_source_id=source_id,
            duration_seconds=240,  # 4 minutes
        ),
    ]
    setup_test_videos(test_db, videos)

    # Reach limit
    test_db.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, completed,
            manual_play, grace_play, duration_watched_seconds)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        ("video1", "Test", "Test", datetime.now(timezone.utc).isoformat(), 1, 0, 0, 1800),
    )
    test_db.commit()

    # Act: Watch grace video
    response = test_client.post(
        "/api/videos/watch",
        json={
            "videoId": "grace_video",
            "completed": True,
            "durationWatchedSeconds": 240,
            "gracePlay": True,  # Grace video flag
        },
    )

    # Assert: Response is successful
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Assert: Watch history logged correctly
    cursor = test_db.execute(
        """SELECT * FROM watch_history
           WHERE video_id = ? AND grace_play = 1""",
        ("grace_video",),
    )
    grace_history = cursor.fetchone()

    assert grace_history is not None, "Grace video should be in watch history"
    assert grace_history["video_id"] == "grace_video"
    assert grace_history["grace_play"] == 1, "grace_play should be 1"
    assert grace_history["manual_play"] == 0, "manual_play should be 0"
    assert grace_history["completed"] == 1, "Video should be marked completed"
    assert grace_history["duration_watched_seconds"] == 240, "Duration should be 240 seconds"

    # Assert: Grace video does NOT count toward limit
    response = test_client.get("/api/limit/status")
    data = response.json()
    assert data["minutesWatched"] == 30, "Grace video should not add to minutes watched"


def test_mid_video_interrupt_logic(test_client, test_db):
    """
    AC 14: Mid-video limit handling (5 minute grace period).

    Tests should_interrupt_video() logic:
    - If video finishes within 5 minutes after limit: let it finish
    - If video exceeds 5 minutes: interrupt immediately

    Note: This is a backend service test, not a full API test, as the
    interrupt logic is internal to viewing_session.py
    """
    from backend.services.viewing_session import should_interrupt_video

    # Scenario 1: Video within grace period
    # Remaining: 2 minutes, Video: 5 minutes
    # Formula: 5 > (2 + 5)? → 5 > 7? → False
    # Video extends 3 minutes past limit (within 5 min grace)
    # Result: Let it finish (False)
    should_interrupt = should_interrupt_video(
        minutes_remaining=2,
        video_duration_minutes=5,
    )
    assert (
        should_interrupt is False
    ), "Should NOT interrupt: video within 5 min grace (extends 3 min)"

    # Scenario 2: Video exceeds grace period
    # Remaining: 2 minutes, Video: 10 minutes
    # Formula: 10 > (2 + 5)? → 10 > 7? → True
    # Video extends 8 minutes past limit (exceeds 5 min grace)
    # Result: Interrupt (True)
    should_interrupt = should_interrupt_video(
        minutes_remaining=2,
        video_duration_minutes=10,
    )
    assert should_interrupt is True, "Should interrupt: video exceeds 5 min grace (extends 8 min)"

    # Scenario 3: Video at exact grace boundary
    # Remaining: 0 minutes, Video: 5 minutes
    # Formula: 5 > (0 + 5)? → 5 > 5? → False
    # Video extends exactly 5 minutes past limit (at grace boundary)
    # Result: Let it finish (False)
    should_interrupt = should_interrupt_video(
        minutes_remaining=0,
        video_duration_minutes=5,
    )
    assert should_interrupt is False, "Should NOT interrupt: video exactly at 5 min grace boundary"

    # Scenario 4: Video just over grace boundary
    # Remaining: 0 minutes, Video: 6 minutes
    # Formula: 6 > (0 + 5)? → 6 > 5? → True
    # Video extends 6 minutes past limit (exceeds 5 min grace by 1)
    # Result: Interrupt (True)
    should_interrupt = should_interrupt_video(
        minutes_remaining=0,
        video_duration_minutes=6,
    )
    assert should_interrupt is True, "Should interrupt: video exceeds 5 min grace by 1 minute"

    # Scenario 5: Video with plenty of time remaining
    # Remaining: 10 minutes, Video: 3 minutes
    # Formula: 3 > (10 + 5)? → 3 > 15? → False
    # Video finishes before limit even reached
    # Result: Let it finish (False)
    should_interrupt = should_interrupt_video(
        minutes_remaining=10,
        video_duration_minutes=3,
    )
    assert should_interrupt is False, "Should NOT interrupt: video finishes before limit"


def test_state_resets_to_normal_after_midnight_utc(test_client, test_db, monkeypatch):
    """
    4.3-INT-003 (P1): State resets to "normal" after midnight UTC.

    Even if grace was consumed yesterday, the state should reset to "normal"
    at midnight UTC (new day begins).
    """
    from freezegun import freeze_time
    from tests.backend.conftest import insert_watch_history

    # Arrange: Set up content source and videos
    source_id = setup_content_source(test_db)
    videos = [
        create_test_video(
            video_id="video1",
            title="Test Video",
            content_source_id=source_id,
            duration_seconds=1800,
        ),
    ]
    setup_test_videos(test_db, videos)

    # Freeze time at YESTERDAY (2025-11-02 23:00:00 UTC)
    with freeze_time("2025-11-02 23:00:00", tz_offset=0):
        # Yesterday: Insert watch history reaching limit + grace consumed
        yesterday = datetime.now(timezone.utc).isoformat()
        insert_watch_history(
            test_db,
            [
                {
                    "video_id": "video1",
                    "video_title": "Yesterday Video",
                    "channel_name": "Test Channel",
                    "watched_at": yesterday,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 1800,  # 30 minutes (reached limit)
                },
                {
                    "video_id": "grace1",
                    "video_title": "Yesterday Grace",
                    "channel_name": "Test Channel",
                    "watched_at": yesterday,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 1,  # Grace consumed
                    "duration_watched_seconds": 300,
                },
            ],
        )

        # Verify yesterday was in "locked" state
        response_yesterday = test_client.get("/api/videos?count=9")
        assert response_yesterday.status_code == 200
        data_yesterday = response_yesterday.json()
        assert (
            data_yesterday["dailyLimit"]["currentState"] == "locked"
        ), "Yesterday should be locked after grace consumed"

    # Act: Fast-forward to TODAY (2025-11-03 10:00:00 UTC) - new day
    with freeze_time("2025-11-03 10:00:00", tz_offset=0):
        # Get videos API response (today, no watch history yet)
        response_today = test_client.get("/api/videos?count=9")

        # Assert: State should reset to "normal" on new day
        assert response_today.status_code == 200
        data_today = response_today.json()

        assert (
            data_today["dailyLimit"]["currentState"] == "normal"
        ), f"Expected 'normal' state on new day, got '{data_today['dailyLimit']['currentState']}'"
        assert (
            data_today["dailyLimit"]["minutesWatched"] == 0
        ), f"Expected 0 minutes watched today, got {data_today['dailyLimit']['minutesWatched']}"
        assert (
            data_today["dailyLimit"]["minutesRemaining"] == 30
        ), f"Expected 30 minutes remaining, got {data_today['dailyLimit']['minutesRemaining']}"
        assert (
            data_today["dailyLimit"]["graceAvailable"] is False
        ), "graceAvailable should be False in normal state"
        assert (
            data_today["dailyLimit"]["date"] == "2025-11-03"
        ), f"Expected today's date '2025-11-03', got {data_today['dailyLimit']['date']}"


def test_get_grace_route_renders_grace_html_template(test_client, test_db):
    """
    4.3-INT-014 (P1): GET /grace renders grace.html template.

    Verifies that the /grace route successfully renders the grace screen template.
    """
    # Arrange: Set up to reach grace state
    source_id = setup_content_source(test_db)
    videos = [
        create_test_video(
            video_id="video1",
            title="Test Video",
            content_source_id=source_id,
            duration_seconds=300,
        ),
    ]
    setup_test_videos(test_db, videos)

    # Insert watch history to reach limit
    from tests.backend.conftest import insert_watch_history

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
                "duration_watched_seconds": 1800,  # 30 minutes (at limit)
            }
        ],
    )

    # Act: Request /grace route
    response = test_client.get("/grace")

    # Assert: Should render successfully
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    assert "text/html" in response.headers.get("content-type", ""), "Expected HTML content type"

    # Assert: Should contain grace screen elements
    html_content = response.text
    assert "grace" in html_content.lower(), "Should contain 'grace' in HTML"
    # Note: More specific assertions about content would require parsing HTML
    # For now, verify it renders without error and returns HTML


def test_get_goodbye_route_renders_goodbye_html_template(test_client, test_db):
    """
    4.3-INT-015 (P1): GET /goodbye renders goodbye.html template.

    Verifies that the /goodbye route successfully renders the goodbye screen template.
    """
    # Arrange: Set up videos (goodbye route doesn't require specific state)
    source_id = setup_content_source(test_db)
    videos = [
        create_test_video(
            video_id="video1",
            title="Test Video",
            content_source_id=source_id,
            duration_seconds=300,
        ),
    ]
    setup_test_videos(test_db, videos)

    # Act: Request /goodbye route
    response = test_client.get("/goodbye")

    # Assert: Should render successfully
    assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
    assert "text/html" in response.headers.get("content-type", ""), "Expected HTML content type"

    # Assert: Should contain goodbye screen elements
    html_content = response.text
    assert (
        "goodbye" in html_content.lower() or "ha det" in html_content.lower()
    ), "Should contain 'goodbye' or 'ha det' in HTML"
    # Note: More specific assertions about content would require parsing HTML
    # For now, verify it renders without error and returns HTML


def test_should_interrupt_video_input_validation(test_client, test_db):
    """
    CODE-001 (P1): Input validation for should_interrupt_video().

    Verifies that the function validates inputs and handles edge cases:
    - Negative video duration raises ValueError
    - Zero video duration raises ValueError
    - Negative minutes_remaining is treated as zero (defensive)
    """
    import pytest
    from backend.services.viewing_session import should_interrupt_video

    # Test 1: Negative video duration should raise ValueError
    with pytest.raises(ValueError, match="video_duration_minutes must be positive"):
        should_interrupt_video(
            minutes_remaining=10,
            video_duration_minutes=-5,
        )

    # Test 2: Zero video duration should raise ValueError
    with pytest.raises(ValueError, match="video_duration_minutes must be positive"):
        should_interrupt_video(
            minutes_remaining=10,
            video_duration_minutes=0,
        )

    # Test 3: Negative minutes_remaining should be treated as zero (defensive)
    # With -5 minutes remaining (already past limit) and 3-minute video
    # Treated as: 3 > (0 + 5)? → False, let it finish
    should_interrupt = should_interrupt_video(
        minutes_remaining=-5,
        video_duration_minutes=3,
    )
    assert should_interrupt is False, "Short video with negative remaining should not interrupt"

    # Test 4: Negative minutes_remaining with long video
    # With -5 minutes remaining (already past limit) and 10-minute video
    # Treated as: 10 > (0 + 5)? → True, interrupt
    should_interrupt = should_interrupt_video(
        minutes_remaining=-5,
        video_duration_minutes=10,
    )
    assert should_interrupt is True, "Long video with negative remaining should interrupt"

    # Test 5: Valid normal case still works
    should_interrupt = should_interrupt_video(
        minutes_remaining=8,
        video_duration_minutes=12,
    )
    assert should_interrupt is False, "Valid inputs should work normally"
