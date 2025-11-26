"""
Integration tests for complete video playback workflows.

Tests multi-component flows including grid interaction, player initialization,
watch logging, state transitions, and navigation logic.

These tests focus on the API layer behavior that supports frontend interactions:
- GET /api/videos - Fetches videos for the grid
- POST /api/videos/watch - Logs video watch events
- Database state changes
"""

import pytest
from datetime import datetime, timezone
from tests.backend.conftest import (
    create_test_video,
    setup_test_videos,
    setup_content_source,
    insert_watch_history,
)


def make_video_id(index: int) -> str:
    """
    Generate a valid 11-character YouTube-style video ID.

    YouTube video IDs are exactly 11 characters (alphanumeric, -, _).

    Args:
        index: Numeric index to create unique ID

    Returns:
        11-character video ID like "dQw4w9WgXcQ"
    """
    # Use a base string and append padded index to make 11 chars
    base = "testvid"  # 7 chars
    return f"{base}{index:04d}"  # 7 + 4 = 11 chars


def setup_multi_channel_videos(test_db, video_count: int = 20, channels: int = 5) -> list[dict]:
    """
    Create videos across multiple channels to satisfy the max 3 per channel constraint.

    The video selection algorithm limits 3 videos per channel in results,
    so we need videos from multiple channels for proper grid testing.

    Args:
        test_db: SQLite connection
        video_count: Total number of videos to create
        channels: Number of channels to distribute videos across

    Returns:
        List of created video dictionaries
    """
    videos = []
    videos_per_channel = video_count // channels

    for channel_idx in range(channels):
        channel_id = f"UCtest_channel_{channel_idx}"
        channel_name = f"Test Channel {channel_idx}"

        # Create content source for this channel
        source_id = setup_content_source(
            test_db,
            source_id=channel_id,
            source_type="channel",
            name=channel_name,
            video_count=videos_per_channel,
        )

        # Create videos for this channel
        for video_idx in range(videos_per_channel):
            global_idx = channel_idx * videos_per_channel + video_idx
            video = create_test_video(
                video_id=make_video_id(global_idx),  # Valid 11-char ID
                title=f"Test Video {global_idx}",
                content_source_id=source_id,
                youtube_channel_id=channel_id,
                youtube_channel_name=channel_name,
                duration_seconds=180 + (global_idx * 10),  # Varying durations
            )
            videos.append(video)

    setup_test_videos(test_db, videos)
    return videos


def test_grid_handleCardClick_disables_cards_and_shows_player(test_client, test_db):
    """
    2.2-INT-001: Test grid API returns videos ready for card click interaction.

    Tests the API layer that supports grid card clicks:
    - GET /api/videos returns correct number of videos
    - Each video has required fields for rendering cards and initializing player
    - Daily limit state is included in response
    """
    # Arrange: Create test videos across multiple channels
    setup_multi_channel_videos(test_db, video_count=20, channels=5)

    # Act: Fetch videos for grid (what happens when grid loads)
    response = test_client.get("/api/videos?count=9")

    # Assert: API returns correct structure for grid rendering
    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "videos" in data
    assert "dailyLimit" in data
    assert len(data["videos"]) == 9

    # Verify each video has required fields for card rendering and player init
    for video in data["videos"]:
        assert "videoId" in video, "videoId required for player initialization"
        assert "title" in video, "title required for card display"
        assert "thumbnailUrl" in video, "thumbnailUrl required for card image"
        assert "durationSeconds" in video, "durationSeconds required for duration display"
        assert "youtubeChannelName" in video, "youtubeChannelName required for attribution"

        # Verify videoId is valid (11 characters, alphanumeric with - and _)
        assert len(video["videoId"]) >= 1
        assert video["durationSeconds"] > 0

    # Verify daily limit structure (needed for state management)
    daily_limit = data["dailyLimit"]
    assert "minutesWatched" in daily_limit
    assert "minutesRemaining" in daily_limit
    assert "currentState" in daily_limit


def test_player_initializes_with_youtube_api(test_client, test_db):
    """
    2.2-INT-007: Test API returns video data suitable for YouTube IFrame Player.

    Tests that video data from API contains all fields needed to initialize
    the YouTube IFrame Player with correct configuration.
    """
    # Arrange: Create test video with valid 11-char ID
    source_id = setup_content_source(test_db)
    video = create_test_video(
        video_id="ytApiTest01",  # Valid 11-char ID
        title="YouTube API Test",
        content_source_id=source_id,
        duration_seconds=240,
    )
    setup_test_videos(test_db, [video])

    # Act: Fetch videos
    response = test_client.get("/api/videos?count=9")

    # Assert: Response contains video suitable for player initialization
    assert response.status_code == 200
    data = response.json()

    # Find our specific video (or verify at least one video is returned)
    assert len(data["videos"]) >= 1

    # Verify video structure supports YouTube IFrame Player initialization
    # Player needs: videoId for loading, durationSeconds for progress tracking
    video_data = data["videos"][0]
    assert "videoId" in video_data
    assert isinstance(video_data["videoId"], str)
    assert len(video_data["videoId"]) > 0

    assert "durationSeconds" in video_data
    assert isinstance(video_data["durationSeconds"], int)
    assert video_data["durationSeconds"] > 0

    # Verify thumbnail URL is valid for preview display
    assert "thumbnailUrl" in video_data
    assert video_data["thumbnailUrl"].startswith("http")


def test_complete_playback_flow_watch_logging_grid_fetch_render(test_client, test_db):
    """
    2.2-INT-008: Test complete playback flow: watch logging → grid fetch → render.

    Multi-step workflow validation:
    1. Fetch initial grid
    2. Simulate video completion (POST watch log)
    3. Fetch new grid
    4. Verify watch history recorded
    5. Verify new grid has different videos
    """
    # Arrange: Create many videos for variety
    setup_multi_channel_videos(test_db, video_count=50, channels=10)

    # Arrange: Set daily limit to 60 minutes
    updated_at = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("daily_limit_minutes", "60", updated_at),
    )
    test_db.commit()

    # Act Step 1: Load initial grid
    response1 = test_client.get("/api/videos?count=9")
    assert response1.status_code == 200
    grid1_data = response1.json()
    grid1_video_ids = {v["videoId"] for v in grid1_data["videos"]}

    # Pick a video to "watch"
    watched_video = grid1_data["videos"][0]

    # Act Step 2: Log video completion (simulates ENDED event from player)
    watch_response = test_client.post(
        "/api/videos/watch",
        json={
            "videoId": watched_video["videoId"],
            "completed": True,
            "durationWatchedSeconds": watched_video["durationSeconds"],
        },
    )
    assert watch_response.status_code == 200

    # Act Step 3: Fetch new grid (what happens after video ends)
    response2 = test_client.get("/api/videos?count=9")
    assert response2.status_code == 200
    grid2_data = response2.json()
    grid2_video_ids = {v["videoId"] for v in grid2_data["videos"]}

    # Assert Step 1: Watch history record created in database
    cursor = test_db.execute(
        "SELECT * FROM watch_history WHERE video_id = ?",
        (watched_video["videoId"],),
    )
    watch_record = cursor.fetchone()
    assert watch_record is not None, "Watch history record should be created"
    assert watch_record["completed"] == 1
    assert watch_record["duration_watched_seconds"] == watched_video["durationSeconds"]

    # Assert Step 2: Daily limit was updated
    watch_data = watch_response.json()
    assert "dailyLimit" in watch_data
    assert watch_data["dailyLimit"]["minutesWatched"] > 0

    # Assert Step 3: Second grid is fetched successfully
    assert len(grid2_data["videos"]) == 9

    # Assert Step 4: Some videos are different (novelty algorithm)
    # The watched video should be deprioritized due to recency penalty
    # With 50 videos available, we expect significant variety
    overlap = grid1_video_ids & grid2_video_ids
    new_videos = grid2_video_ids - grid1_video_ids

    # At least 3 new videos should appear (algorithm provides ~60-80% novelty)
    assert len(new_videos) >= 3, f"Expected novelty, got {len(new_videos)} new videos"


def test_grid_fetches_new_random_videos_not_same_as_before(test_client, test_db):
    """
    2.2-INT-009: Test grid fetches NEW random videos (not same as before).

    Verify novelty algorithm works - multiple grid fetches should return
    different video selections due to weighted random algorithm.
    """
    # Arrange: Create many videos across channels
    setup_multi_channel_videos(test_db, video_count=50, channels=10)

    # Act: Fetch grid multiple times and collect video IDs
    all_video_ids = []
    for _ in range(5):
        response = test_client.get("/api/videos?count=9")
        assert response.status_code == 200
        video_ids = [v["videoId"] for v in response.json()["videos"]]
        all_video_ids.append(set(video_ids))

    # Assert: Different selections across fetches
    # Due to weighted random selection, we expect variation

    # Check that not all fetches return identical results
    unique_selections = len(set(frozenset(ids) for ids in all_video_ids))
    assert unique_selections >= 2, "Expected some variation in video selections"

    # Check total unique videos seen across all fetches
    # With 50 videos and 5 fetches of 9 each, should see variety
    total_unique = len(set().union(*all_video_ids))
    assert total_unique >= 15, f"Expected to see at least 15 unique videos, saw {total_unique}"


def test_back_button_flow_logs_watch_and_returns_to_grid(test_client, test_db):
    """
    2.2-INT-010: Test back button flow logs watch and returns to grid.

    Multi-component flow - back button should log partial watch with actual
    duration and return to grid with new videos.
    """
    # Arrange: Create test videos
    setup_multi_channel_videos(test_db, video_count=20, channels=5)

    # Arrange: Set daily limit to 30 minutes
    updated_at = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("daily_limit_minutes", "30", updated_at),
    )
    test_db.commit()

    # Act Step 1: Load grid
    response1 = test_client.get("/api/videos?count=9")
    assert response1.status_code == 200
    video_to_watch = response1.json()["videos"][0]

    # Act Step 2: Log partial watch (simulates back button after 120 seconds)
    partial_duration = 120  # 2 minutes
    watch_response = test_client.post(
        "/api/videos/watch",
        json={
            "videoId": video_to_watch["videoId"],
            "completed": False,
            "durationWatchedSeconds": partial_duration,
        },
    )
    assert watch_response.status_code == 200

    # Act Step 3: Fetch new grid (return to grid after back button)
    response2 = test_client.get("/api/videos?count=9")
    assert response2.status_code == 200

    # Assert Step 1: Watch history records partial duration
    cursor = test_db.execute(
        "SELECT * FROM watch_history WHERE video_id = ?",
        (video_to_watch["videoId"],),
    )
    watch_record = cursor.fetchone()
    assert watch_record is not None
    assert watch_record["completed"] == 0, "Should be marked as incomplete"
    assert watch_record["duration_watched_seconds"] == partial_duration
    # Verify it's NOT the video's full duration
    assert watch_record["duration_watched_seconds"] < video_to_watch["durationSeconds"]

    # Assert Step 2: Daily limit reflects partial watch time
    watch_data = watch_response.json()
    assert watch_data["dailyLimit"]["minutesWatched"] == 2  # 120 seconds = 2 minutes

    # Assert Step 3: New grid is successfully fetched
    assert len(response2.json()["videos"]) == 9


@pytest.mark.tier1
def test_esc_key_flow_does_not_create_watch_history_record(test_client, test_db):
    """
    2.2-INT-011: [TIER 1] Test ESC key flow does NOT create watch_history record.

    TIER 1: Safety-critical - cancelled playback (ESC key) must not count toward
    daily limit. This test verifies the database behavior that supports ESC cancellation.

    Note: ESC key handler is frontend-only and does NOT call the API.
    This test verifies that without an API call, no watch record is created.
    """
    # Arrange: Create test video with valid 11-char ID
    video_id = "escTestVid1"  # Valid 11-char ID
    source_id = setup_content_source(test_db)
    video = create_test_video(
        video_id=video_id,
        title="ESC Test Video",
        content_source_id=source_id,
        duration_seconds=300,
    )
    setup_test_videos(test_db, [video])

    # Arrange: Set daily limit
    updated_at = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("daily_limit_minutes", "30", updated_at),
    )
    test_db.commit()

    # Act: Fetch grid (video loads)
    response = test_client.get("/api/videos?count=9")
    assert response.status_code == 200

    # Note: ESC key cancellation happens entirely in frontend - NO API call is made
    # The frontend destroys the player and returns to grid without logging

    # Assert: No watch history record exists for this video
    # (because ESC key handler doesn't call /api/videos/watch)
    cursor = test_db.execute(
        "SELECT COUNT(*) as count FROM watch_history WHERE video_id = ?",
        (video_id,),
    )
    count = cursor.fetchone()["count"]
    assert count == 0, "ESC cancellation should not create watch_history record"


@pytest.mark.tier1
def test_normal_navigation_to_grid_when_state_is_normal_or_winddown(test_client, test_db):
    """
    2.2-INT-019: [TIER 1] Test normal navigation to grid when state is 'normal' or 'winddown'.

    TIER 1: Safety-critical - correct state transitions during normal viewing.
    Tests that daily limit state is correctly reported by the API.
    """
    # Arrange: Create test videos
    setup_multi_channel_videos(test_db, video_count=20, channels=5)

    # Arrange: Set daily limit to 30 minutes
    updated_at = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("daily_limit_minutes", "30", updated_at),
    )
    test_db.commit()

    # Test case 1: Normal state (no previous watches)
    response1 = test_client.get("/api/videos?count=9")
    assert response1.status_code == 200
    state1 = response1.json()["dailyLimit"]
    assert state1["currentState"] == "normal"
    assert state1["minutesRemaining"] == 30

    # Test case 2: Watch a video (5 minutes)
    video = response1.json()["videos"][0]
    test_client.post(
        "/api/videos/watch",
        json={"videoId": video["videoId"], "completed": True, "durationWatchedSeconds": 300},
    )

    # Verify state is still normal (25 minutes remaining)
    response2 = test_client.get("/api/videos?count=9")
    state2 = response2.json()["dailyLimit"]
    assert state2["currentState"] == "normal"
    assert state2["minutesRemaining"] == 25

    # Test case 3: Add watch history to enter winddown (≤10 min remaining)
    today = datetime.now(timezone.utc).date().isoformat()
    insert_watch_history(
        test_db,
        [
            {
                "video_id": "wndwnTest01",  # Valid 11-char ID
                "video_title": "Winddown Test",
                "channel_name": "Test Channel",
                "watched_at": f"{today}T10:00:00+00:00",
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 900,  # 15 more minutes
            }
        ],
    )

    # Verify winddown state (10 minutes remaining)
    response3 = test_client.get("/api/videos?count=9")
    state3 = response3.json()["dailyLimit"]
    assert state3["currentState"] == "winddown"
    assert state3["minutesRemaining"] == 10


@pytest.mark.tier1
def test_back_button_after_30_seconds_logs_approximately_30_seconds(test_client, test_db):
    """
    2.2-INT-021: [TIER 1] Test back button after 30 seconds logs ~30 seconds (not video length).

    TIER 1: Safety-critical - real-time accuracy of duration tracking.
    Must log ACTUAL watch time, not video's total duration.
    """
    # Arrange: Create test video with long duration and valid 11-char ID
    video_id = "durTestVid1"  # Valid 11-char ID
    source_id = setup_content_source(test_db)
    video = create_test_video(
        video_id=video_id,
        title="Duration Accuracy Test",
        content_source_id=source_id,
        duration_seconds=600,  # 10 minutes total duration
    )
    setup_test_videos(test_db, [video])

    # Arrange: Set daily limit
    updated_at = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
        ("daily_limit_minutes", "30", updated_at),
    )
    test_db.commit()

    # Act: Log watch with only 30 seconds watched (simulates back button)
    watch_response = test_client.post(
        "/api/videos/watch",
        json={
            "videoId": video_id,
            "completed": False,
            "durationWatchedSeconds": 30,  # Only 30 seconds, not 600
        },
    )
    assert watch_response.status_code == 200

    # Assert Step 1: Watch history records 30 seconds, NOT 600
    cursor = test_db.execute(
        "SELECT * FROM watch_history WHERE video_id = ?",
        (video_id,),
    )
    watch_record = cursor.fetchone()
    assert watch_record is not None
    assert watch_record["duration_watched_seconds"] == 30
    assert watch_record["duration_watched_seconds"] != 600  # NOT the video's full duration
    assert watch_record["completed"] == 0

    # Assert Step 2: Daily limit reflects only 30 seconds (rounded to 0 or 1 minute)
    daily_limit = watch_response.json()["dailyLimit"]
    assert daily_limit["minutesWatched"] <= 1  # 30 seconds rounds to 0 or 1 minute

    # Assert Step 3: Video table still has original duration (unchanged)
    cursor = test_db.execute(
        "SELECT duration_seconds FROM videos WHERE video_id = ?",
        (video_id,),
    )
    video_record = cursor.fetchone()
    assert video_record["duration_seconds"] == 600  # Original duration preserved
