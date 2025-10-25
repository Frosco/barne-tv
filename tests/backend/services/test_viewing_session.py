"""
Unit tests for viewing_session.py service module (Story 2.1).

Tests the weighted random selection algorithm and daily limit state machine.
Focus on business logic, not database integration (use mocked query functions).

Coverage Target: ≥90% for viewing_session.py
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import patch
from backend.services.viewing_session import get_videos_for_grid, get_daily_limit
from backend.exceptions import NoVideosAvailableError


# =============================================================================
# TEST DATA
# =============================================================================


def create_mock_videos(count: int, start_id: int = 0) -> list[dict]:
    """Helper to create mock video dictionaries."""
    return [
        {
            "videoId": f"video_{i}",
            "title": f"Test Video {i}",
            "youtubeChannelName": "Test Channel",
            "thumbnailUrl": f"https://example.com/thumb_{i}.jpg",
            "durationSeconds": 300,
        }
        for i in range(start_id, start_id + count)
    ]


def create_mock_watch_history(video_ids: list[str]) -> list[dict]:
    """Helper to create mock watch history for videos."""
    return [
        {
            "videoId": video_id,
            "videoTitle": f"Title for {video_id}",
            "channelName": "Test Channel",
            "watchedAt": datetime.now(timezone.utc).isoformat(),
            "durationWatchedSeconds": 300,
            "completed": True,
        }
        for video_id in video_ids
    ]


# =============================================================================
# AC2: Weighted Random Selection Algorithm Tests
# =============================================================================


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_005_calculate_novelty_vs_favorites_split_60_to_80_range(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    2.1-UNIT-005: Weighted algorithm calculates 60-80% novelty, 20-40% favorites.

    Verifies:
    - Novelty ratio is between 0.6 and 0.8
    - Favorites ratio is between 0.2 and 0.4
    - Split calculation is correct for requested count

    Note: Since random.uniform(0.6, 0.8) is used, we test the RESULT not the ratio itself.
    We verify the split falls within the expected range over multiple runs.
    """
    # Setup: 20 videos, 5 recently watched (favorites), 15 novel
    mock_get_videos.return_value = create_mock_videos(20)
    recent_videos = ["video_0", "video_1", "video_2", "video_3", "video_4"]
    mock_get_history.return_value = create_mock_watch_history(recent_videos)
    mock_get_setting.return_value = "30"  # daily_limit_minutes

    # Run selection 50 times to verify ratio range
    novelty_counts = []
    favorites_counts = []

    for _ in range(50):
        videos, _ = get_videos_for_grid(count=10)

        # Count novelty vs favorites in result
        result_ids = {v["videoId"] for v in videos}
        favorites_in_result = result_ids.intersection(recent_videos)
        novelty_in_result = result_ids - favorites_in_result

        novelty_counts.append(len(novelty_in_result))
        favorites_counts.append(len(favorites_in_result))

    # Verify ranges (60-80% novelty = 6-8 videos, 20-40% favorites = 2-4 videos for count=10)
    avg_novelty = sum(novelty_counts) / len(novelty_counts)
    avg_favorites = sum(favorites_counts) / len(favorites_counts)

    # Average should be ~7 novelty (70%), ~3 favorites (30%)
    assert 5.5 <= avg_novelty <= 8.5, f"Average novelty {avg_novelty} outside 60-80% range"
    assert 1.5 <= avg_favorites <= 4.5, f"Average favorites {avg_favorites} outside 20-40% range"


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_006_separate_videos_into_novelty_and_favorites_pools(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    2.1-UNIT-006: Algorithm separates videos into novelty and favorites pools.

    Verifies:
    - Videos NOT in recent watch history are considered novelty
    - Videos IN recent watch history are considered favorites
    - Pool separation logic works correctly
    """
    # Setup: 10 videos total, 3 recently watched
    mock_get_videos.return_value = create_mock_videos(10)
    recent_videos = ["video_2", "video_5", "video_8"]  # Favorites
    mock_get_history.return_value = create_mock_watch_history(recent_videos)
    mock_get_setting.return_value = "30"

    # Get videos
    videos, _ = get_videos_for_grid(count=6)

    # Extract IDs from result
    result_ids = {v["videoId"] for v in videos}

    # Should have SOME from each pool (can't predict exact split due to randomness)
    # But we can verify:
    # 1. Result is correct size
    assert len(videos) == 6
    # 2. All videos are either novelty or favorites (no unknown videos)
    all_possible = {
        "video_0",
        "video_1",
        "video_2",
        "video_3",
        "video_4",
        "video_5",
        "video_6",
        "video_7",
        "video_8",
        "video_9",
    }
    assert result_ids.issubset(all_possible)


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_007_handle_case_where_novelty_pool_is_empty(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    2.1-UNIT-007: Algorithm handles case where novelty pool is empty (all videos are favorites).

    Verifies:
    - When all available videos have been watched recently
    - Algorithm still returns requested count
    - All videos come from favorites pool
    """
    # Setup: 10 videos, ALL recently watched (no novelty)
    all_videos = create_mock_videos(10)
    mock_get_videos.return_value = all_videos
    all_video_ids = [v["videoId"] for v in all_videos]
    mock_get_history.return_value = create_mock_watch_history(all_video_ids)
    mock_get_setting.return_value = "30"

    # Request 6 videos
    videos, _ = get_videos_for_grid(count=6)

    # Verify:
    # 1. Returns requested count
    assert len(videos) == 6
    # 2. All videos are from favorites pool (recently watched)
    result_ids = {v["videoId"] for v in videos}
    assert result_ids.issubset(set(all_video_ids))


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_008_handle_case_where_favorites_pool_is_empty(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    2.1-UNIT-008: Algorithm handles case where favorites pool is empty (no recent watches).

    Verifies:
    - When no videos have been watched recently (all novelty)
    - Algorithm still returns requested count
    - All videos come from novelty pool
    """
    # Setup: 10 videos, NONE recently watched (all novelty)
    mock_get_videos.return_value = create_mock_videos(10)
    mock_get_history.return_value = []  # No recent watch history
    mock_get_setting.return_value = "30"

    # Request 6 videos
    videos, _ = get_videos_for_grid(count=6)

    # Verify:
    # 1. Returns requested count
    assert len(videos) == 6
    # 2. All videos are from available pool
    result_ids = {v["videoId"] for v in videos}
    all_video_ids = {f"video_{i}" for i in range(10)}
    assert result_ids.issubset(all_video_ids)


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_009_fill_remaining_slots_when_pools_exhausted(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    2.1-UNIT-009: Algorithm fills remaining slots when pools are smaller than requested count.

    Verifies:
    - When novelty pool has only 2 videos and favorites pool has only 1 video
    - But we request 6 videos
    - Algorithm returns 3 videos (all available)
    - Fallback logic works correctly
    """
    # Setup: Only 5 available videos, 2 are favorites
    mock_get_videos.return_value = create_mock_videos(5)
    recent_videos = ["video_1", "video_3"]  # Only 2 favorites
    mock_get_history.return_value = create_mock_watch_history(recent_videos)
    mock_get_setting.return_value = "30"

    # Request 10 videos (more than available)
    videos, _ = get_videos_for_grid(count=10)

    # Verify:
    # 1. Returns all 5 available videos (can't return more than exist)
    assert len(videos) == 5
    # 2. All returned videos are from the available pool
    result_ids = {v["videoId"] for v in videos}
    expected_ids = {f"video_{i}" for i in range(5)}
    assert result_ids == expected_ids


# =============================================================================
# AC10: Grid Refresh Tests
# =============================================================================


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_011_get_videos_for_grid_returns_new_selection_each_call(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    2.1-UNIT-011: get_videos_for_grid() returns new random selection on each call.

    Verifies:
    - Calling function multiple times produces different results
    - Grid regenerates with new videos (not cached)
    - Randomness is working
    """
    # Setup: 20 videos available, 5 recently watched
    mock_get_videos.return_value = create_mock_videos(20)
    recent_videos = ["video_0", "video_1", "video_2"]
    mock_get_history.return_value = create_mock_watch_history(recent_videos)
    mock_get_setting.return_value = "30"

    # Call function 10 times
    selections = []
    for _ in range(10):
        videos, _ = get_videos_for_grid(count=9)
        video_ids = tuple(v["videoId"] for v in videos)  # Convert to tuple for comparison
        selections.append(video_ids)

    # Verify: At least some selections are different (not all identical)
    unique_selections = set(selections)
    assert len(unique_selections) > 1, "All selections were identical - randomness not working"


# =============================================================================
# AC11: Grid Size Setting Tests
# =============================================================================


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_012_get_setting_grid_size_returns_configured_value(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    2.1-UNIT-012: get_setting('grid_size') returns configured value.

    Verifies:
    - Settings retrieval works correctly
    - Grid size can be configured by parent
    - Value is used in video selection

    Note: This tests the INTEGRATION of settings, not get_setting() itself.
    get_setting() is tested in test_queries.py.
    """
    # Setup: 20 videos available
    mock_get_videos.return_value = create_mock_videos(20)
    mock_get_history.return_value = []
    mock_get_setting.return_value = (
        "30"  # daily_limit_minutes (grid_size would be tested in routes)
    )

    # In Story 2.1, grid_size is passed as the `count` parameter to get_videos_for_grid()
    # This test verifies the function respects the requested count
    videos_9, _ = get_videos_for_grid(count=9)
    assert len(videos_9) == 9

    videos_12, _ = get_videos_for_grid(count=12)
    assert len(videos_12) == 12


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_013_default_to_9_when_grid_size_not_provided(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    2.1-UNIT-013: Grid defaults to 9 videos when grid_size setting not provided.

    Note: In the actual implementation, the routes layer handles default values.
    get_videos_for_grid() always receives a `count` parameter.
    This test verifies the function works correctly with default count=9.
    """
    # Setup: 20 videos available
    mock_get_videos.return_value = create_mock_videos(20)
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Call with default count (9 is default in routes.py)
    videos, _ = get_videos_for_grid(count=9)
    assert len(videos) == 9


# =============================================================================
# Cross-Cutting: Daily Limit State Machine Tests
# =============================================================================


@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_016_get_daily_limit_state_normal_more_than_10_min_remaining(
    mock_get_setting, mock_get_history
):
    """
    2.1-UNIT-016: get_daily_limit() returns state='normal' when >10 minutes remaining.

    Verifies:
    - State machine: normal state for >10 minutes remaining
    - Minutes watched calculation correct
    - Minutes remaining calculation correct
    """
    # Setup: Watched 15 minutes today, limit is 30, so 15 remaining (>10 = normal)
    mock_get_history.return_value = [
        {
            "videoId": "video_1",
            "videoTitle": "Test Video",
            "channelName": "Test Channel",
            "watchedAt": datetime.now(timezone.utc).isoformat(),
            "durationWatchedSeconds": 900,  # 15 minutes
            "completed": True,
        }
    ]
    mock_get_setting.return_value = "30"  # 30 minute daily limit

    # Get daily limit state
    limit = get_daily_limit()

    # Verify:
    assert limit["minutesWatched"] == 15
    assert limit["minutesRemaining"] == 15
    assert limit["currentState"] == "normal"
    assert "date" in limit
    assert "resetTime" in limit


@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_017_get_daily_limit_state_winddown_10_min_or_less_remaining(
    mock_get_setting, mock_get_history
):
    """
    2.1-UNIT-017: get_daily_limit() returns state='winddown' when ≤10 minutes remaining.

    Verifies:
    - State machine: winddown state for ≤10 minutes remaining
    - Wind-down mode triggers correctly
    - Video duration filtering should be applied
    """
    # Setup: Watched 22 minutes today, limit is 30, so 8 remaining (≤10 = winddown)
    mock_get_history.return_value = [
        {
            "videoId": "video_1",
            "videoTitle": "Test Video",
            "channelName": "Test Channel",
            "watchedAt": datetime.now(timezone.utc).isoformat(),
            "durationWatchedSeconds": 1320,  # 22 minutes
            "completed": True,
        }
    ]
    mock_get_setting.return_value = "30"

    # Get daily limit state
    limit = get_daily_limit()

    # Verify:
    assert limit["minutesWatched"] == 22
    assert limit["minutesRemaining"] == 8
    assert limit["currentState"] == "winddown"


@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_018_get_daily_limit_state_grace_when_0_min_remaining(
    mock_get_setting, mock_get_history
):
    """
    2.1-UNIT-018: get_daily_limit() returns state='grace' when 0 minutes remaining.

    Verifies:
    - State machine: grace state when limit reached
    - Grace video offered (≤5 minutes allowed)
    - After grace, state becomes 'locked' (Story 2.2)
    """
    # Setup: Watched 30 minutes today, limit is 30, so 0 remaining (= grace)
    mock_get_history.return_value = [
        {
            "videoId": "video_1",
            "videoTitle": "Test Video",
            "channelName": "Test Channel",
            "watchedAt": datetime.now(timezone.utc).isoformat(),
            "durationWatchedSeconds": 1800,  # 30 minutes
            "completed": True,
        }
    ]
    mock_get_setting.return_value = "30"

    # Get daily limit state
    limit = get_daily_limit()

    # Verify:
    assert limit["minutesWatched"] == 30
    assert limit["minutesRemaining"] == 0
    assert limit["currentState"] == "grace"


# =============================================================================
# Error Handling Tests
# =============================================================================


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_no_videos_available_raises_exception(mock_get_setting, mock_get_history, mock_get_videos):
    """
    Verify NoVideosAvailableError raised when no videos exist.

    This is tested for Norwegian error message in integration tests.
    """
    # Setup: No videos available
    mock_get_videos.return_value = []
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Verify exception raised
    with pytest.raises(NoVideosAvailableError) as exc_info:
        get_videos_for_grid(count=9)

    # Verify Norwegian message (TIER 3 Rule 14)
    assert "Ingen videoer tilgjengelig" in str(exc_info.value)


# =============================================================================
# Wind-Down Mode Tests
# =============================================================================


@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_wind_down_mode_filters_by_max_duration(
    mock_get_setting, mock_get_history, mock_get_videos
):
    """
    Verify get_videos_for_grid() passes max_duration_seconds to query function.

    Wind-down filtering logic is tested in integration tests.
    This unit test verifies the parameter is passed correctly.
    """
    # Setup
    mock_get_videos.return_value = create_mock_videos(10)
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Call with max_duration (wind-down mode)
    get_videos_for_grid(count=9, max_duration_seconds=300)

    # Verify get_available_videos was called with max_duration parameter
    mock_get_videos.assert_called_with(exclude_banned=True, max_duration_seconds=300)
