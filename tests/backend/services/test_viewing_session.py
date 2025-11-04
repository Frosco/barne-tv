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


def create_mock_videos(count: int, start_id: int = 0, vary_channels: bool = True) -> list[dict]:
    """
    Helper to create mock video dictionaries.

    Args:
        count: Number of videos to create
        start_id: Starting ID for videos
        vary_channels: If True, distribute videos across multiple channels (Story 4.4 channel variety constraint).
                      If False, all videos from same channel (legacy behavior).
    """
    return [
        {
            "videoId": f"video_{i}",
            "title": f"Test Video {i}",
            "youtubeChannelName": (
                f"Channel {i % 5}" if vary_channels else "Test Channel"
            ),  # Distribute across 5 channels
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


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_005_engagement_based_selection_uses_weights(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_engagement
):
    """
    4.4-UNIT-005: Engagement-based algorithm uses weighted selection.

    Verifies:
    - Videos with higher engagement scores are selected more frequently
    - Weighted random selection is working (not deterministic)
    - Selection feels random despite weighting (AC 7)

    Note: Replaces old Story 2.1 novelty/favorites test.
    Story 4.4 uses engagement-based weighted selection instead.
    """
    # Setup: 10 videos with varying engagement scores
    mock_get_videos.return_value = create_mock_videos(10)
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Mock engagement scores: video_0 has high engagement, video_9 has low engagement
    mock_calc_engagement.return_value = {
        "video_0": 0.9,  # High engagement
        "video_1": 0.8,
        "video_2": 0.7,
        "video_3": 0.6,
        "video_4": 0.5,
        "video_5": 0.4,
        "video_6": 0.3,
        "video_7": 0.2,
        "video_8": 0.1,
        "video_9": 0.05,  # Low engagement (minimum floor)
    }

    # Run selection 100 times
    selection_counts = {f"video_{i}": 0 for i in range(10)}

    for _ in range(100):
        videos, _ = get_videos_for_grid(count=5)
        for video in videos:
            selection_counts[video["videoId"]] += 1

    # Verify: High-engagement videos selected more frequently than low-engagement
    # video_0 (0.9 weight) should be selected more often than video_9 (0.05 weight)
    assert (
        selection_counts["video_0"] > selection_counts["video_9"]
    ), f"High engagement video_0 ({selection_counts['video_0']}) should be selected more than low engagement video_9 ({selection_counts['video_9']})"

    # Verify: Even low-engagement videos get selected sometimes (AC 4: never completely hidden)
    assert (
        selection_counts["video_9"] > 0
    ), "Even lowest engagement video should be selected at least once in 100 runs"


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_006_channel_variety_constraint_max_3_per_channel(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_engagement
):
    """
    4.4-UNIT-006: Channel variety constraint limits max 3 videos per channel.

    Verifies:
    - No more than 3 videos from any single channel in result (AC 8)
    - Constraint enforced even when one channel has high engagement
    - Multiple channels represented in grid

    Note: Replaces old Story 2.1 novelty/favorites pool test.
    Story 4.4 uses channel variety constraint instead.
    """
    # Setup: 15 videos, 10 from "Channel A", 5 from "Channel B"
    videos_channel_a = [
        {
            "videoId": f"video_a{i}",
            "title": f"Video A{i}",
            "youtubeChannelName": "Channel A",
            "thumbnailUrl": f"https://example.com/thumb_a{i}.jpg",
            "durationSeconds": 300,
        }
        for i in range(10)
    ]
    videos_channel_b = [
        {
            "videoId": f"video_b{i}",
            "title": f"Video B{i}",
            "youtubeChannelName": "Channel B",
            "thumbnailUrl": f"https://example.com/thumb_b{i}.jpg",
            "durationSeconds": 300,
        }
        for i in range(5)
    ]
    mock_get_videos.return_value = videos_channel_a + videos_channel_b
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # All videos have equal engagement
    mock_calc_engagement.return_value = {f"video_a{i}": 0.7 for i in range(10)} | {
        f"video_b{i}": 0.7 for i in range(5)
    }

    # Get 9 videos (typical grid size)
    videos, _ = get_videos_for_grid(count=9)

    # Count videos per channel
    channel_counts = {}
    for video in videos:
        channel = video["youtubeChannelName"]
        channel_counts[channel] = channel_counts.get(channel, 0) + 1

    # Verify: No channel has more than 3 videos
    for channel, count in channel_counts.items():
        assert count <= 3, f"Channel {channel} has {count} videos (max 3 allowed)"

    # Verify: Both channels represented (variety)
    assert "Channel A" in channel_counts, "Channel A should be represented"
    assert "Channel B" in channel_counts, "Channel B should be represented"


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_007_handle_all_videos_watched_recently_fallback(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_engagement
):
    """
    4.4-UNIT-007: Algorithm falls back to random when all videos watched recently (AC 9).

    Verifies:
    - When all videos have very low engagement scores (< 0.15)
    - Algorithm falls back to random selection
    - Still returns requested count (no empty grid)

    Note: Replaces old Story 2.1 novelty pool empty test.
    Story 4.4 handles this as edge case with random fallback.
    """
    # Setup: 10 videos, all with very low engagement (all recently watched)
    mock_get_videos.return_value = create_mock_videos(10)
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # All videos have very low engagement scores (< 0.15) due to recency penalty
    # This triggers the fallback to random selection
    mock_calc_engagement.return_value = {
        f"video_{i}": 0.08 for i in range(10)  # All below 0.15 threshold
    }

    # Request 6 videos
    videos, _ = get_videos_for_grid(count=6)

    # Verify:
    # 1. Returns requested count
    assert len(videos) == 6
    # 2. All returned videos are from available pool
    result_ids = {v["videoId"] for v in videos}
    all_video_ids = {f"video_{i}" for i in range(10)}
    assert result_ids.issubset(all_video_ids)


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_008_handle_no_watch_history_baseline_weights(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_engagement
):
    """
    4.4-UNIT-008: Algorithm handles no watch history with baseline weights.

    Verifies:
    - When no videos have been watched (brand new deployment)
    - All videos get baseline weight 0.5
    - Selection becomes effectively random (equal weights)
    - Still returns requested count

    Note: Replaces old Story 2.1 favorites pool empty test.
    Story 4.4 handles this with baseline weights for new videos.
    """
    # Setup: 10 videos, no watch history (all new)
    mock_get_videos.return_value = create_mock_videos(10)
    mock_get_history.return_value = []  # No watch history
    mock_get_setting.return_value = "30"

    # All videos have baseline weight 0.5 (no history)
    mock_calc_engagement.return_value = {
        f"video_{i}": 0.5 for i in range(10)  # Baseline weight for new videos
    }

    # Request 6 videos
    videos, _ = get_videos_for_grid(count=6)

    # Verify:
    # 1. Returns requested count
    assert len(videos) == 6
    # 2. All videos are from available pool
    result_ids = {v["videoId"] for v in videos}
    all_video_ids = {f"video_{i}" for i in range(10)}
    assert result_ids.issubset(all_video_ids)


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_009_returns_all_videos_when_fewer_than_requested(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_engagement
):
    """
    4.4-UNIT-009: Algorithm returns all videos when fewer available than requested count.

    Verifies:
    - When only 5 videos available but we request 10
    - Algorithm returns all 5 available videos (can't return more than exist)
    - No errors or empty results

    Note: Updated for Story 4.4 engagement algorithm.
    """
    # Setup: Only 5 available videos
    mock_get_videos.return_value = create_mock_videos(5)
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Mock engagement scores (not used since len(available) <= count)
    mock_calc_engagement.return_value = {f"video_{i}": 0.5 for i in range(5)}

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


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_011_get_videos_for_grid_returns_new_selection_each_call(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_engagement
):
    """
    4.4-UNIT-011: get_videos_for_grid() returns new selection on each call (AC 7: feels random).

    Verifies:
    - Calling function multiple times produces different results
    - Grid regenerates with new videos (not cached)
    - Weighted randomness is working
    - Selection feels random despite engagement weighting

    Note: Updated for Story 4.4 engagement algorithm.
    """
    # Setup: 20 videos available with varying engagement
    mock_get_videos.return_value = create_mock_videos(20)
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Mock engagement scores - varying weights to test weighted randomness
    mock_calc_engagement.return_value = {
        f"video_{i}": 0.3 + (i * 0.03) for i in range(20)  # Weights from 0.3 to 0.87
    }

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


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_012_respects_requested_count_parameter(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_engagement
):
    """
    4.4-UNIT-012: get_videos_for_grid() respects requested count parameter.

    Verifies:
    - Grid size can be configured by parent
    - Function returns requested number of videos
    - Count parameter works correctly with engagement algorithm

    Note: Updated for Story 4.4 engagement algorithm.
    """
    # Setup: 20 videos available
    mock_get_videos.return_value = create_mock_videos(20)
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"  # daily_limit_minutes

    # Mock engagement scores
    mock_calc_engagement.return_value = {f"video_{i}": 0.5 for i in range(20)}

    # Verify function respects the requested count
    videos_9, _ = get_videos_for_grid(count=9)
    assert len(videos_9) == 9

    videos_12, _ = get_videos_for_grid(count=12)
    assert len(videos_12) == 12


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_013_works_with_default_count_9(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_engagement
):
    """
    4.4-UNIT-013: Function works correctly with default count of 9.

    Note: In the actual implementation, the routes layer handles default values.
    get_videos_for_grid() always receives a `count` parameter.
    This test verifies the function works correctly with default count=9.

    Note: Updated for Story 4.4 engagement algorithm.
    """
    # Setup: 20 videos available
    mock_get_videos.return_value = create_mock_videos(20)
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Mock engagement scores
    mock_calc_engagement.return_value = {f"video_{i}": 0.5 for i in range(20)}

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


# =============================================================================
# Edge Case Tests (Story 4.4 Phase 3)
# =============================================================================


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_014_channel_constraint_sets_weight_zero(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_scores
):
    """
    Test 4.4-UNIT-014: Track channel counts during selection, set weight=0 when channel has 3 videos.

    This test verifies the channel variety constraint (AC 8):
    - Max 3 videos per channel in result set
    - Weight set to 0 when channel already has 3 videos selected

    Scenario:
    - 10 videos from same channel (all high engagement)
    - Request 9 videos

    Expected:
    - Only 3 videos from that channel selected
    - Channel constraint enforced despite high engagement
    """
    # Setup: 10 videos from same channel
    mock_videos = [
        {
            "videoId": f"video_{i}",
            "title": f"Video {i}",
            "youtubeChannelName": "Single Channel",
            "durationSeconds": 300,
        }
        for i in range(1, 11)
    ]
    mock_get_videos.return_value = mock_videos
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # All videos have high engagement (should favor selection, but channel constraint wins)
    mock_calc_scores.return_value = {f"video_{i}": 0.9 for i in range(1, 11)}

    # Call get_videos_for_grid
    videos, _ = get_videos_for_grid(count=9)

    # Verify only 3 videos selected (channel constraint enforced)
    assert len(videos) == 3, f"Expected 3 videos (channel constraint), got {len(videos)}"

    # Verify all from same channel
    assert all(
        v["youtubeChannelName"] == "Single Channel" for v in videos
    ), "All videos should be from Single Channel"


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_015_single_channel_all_eligible(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_scores
):
    """
    Test 4.4-UNIT-015: Edge case: Single channel with 20 videos → max 3 selected.

    This test verifies that the channel constraint applies even when there's only
    one channel available (prevents monotony in single-channel setup).

    Scenario:
    - 20 videos from single channel
    - Request 9 videos

    Expected:
    - Only 3 videos selected (channel constraint enforced even for single channel)
    """
    # Setup: 20 videos from single channel
    mock_videos = [
        {
            "videoId": f"video_{i}",
            "title": f"Video {i}",
            "youtubeChannelName": "Only Channel",
            "durationSeconds": 300,
        }
        for i in range(1, 21)
    ]
    mock_get_videos.return_value = mock_videos
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Varying engagement scores
    mock_calc_scores.return_value = {f"video_{i}": 0.5 + (i * 0.02) for i in range(1, 21)}

    # Call get_videos_for_grid
    videos, _ = get_videos_for_grid(count=9)

    # Verify max 3 videos selected (channel constraint)
    assert len(videos) == 3, f"Expected 3 videos max from single channel, got {len(videos)}"


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_016_low_weights_trigger_random_fallback(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_scores
):
    """
    Test 4.4-UNIT-016: Detect all weights <0.15 threshold → trigger random fallback.

    This test verifies AC 9 edge case handling:
    - When all videos recently watched (all engagement scores < 0.15)
    - Algorithm falls back to random selection
    - Ensures child always gets videos (prevents empty grid)

    Scenario:
    - All videos have very low engagement scores (<0.15)
    - This happens when all videos watched in last 24h (recency penalty)

    Expected:
    - Random fallback triggered (not weighted selection)
    - All videos returned successfully
    """
    # Setup: 15 videos
    mock_videos = create_mock_videos(15)
    mock_get_videos.return_value = mock_videos
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # ALL engagement scores < 0.15 (triggers fallback)
    mock_calc_scores.return_value = {f"video_{i}": 0.10 for i in range(1, 16)}

    # Call get_videos_for_grid
    videos, _ = get_videos_for_grid(count=9)

    # Verify 9 videos returned (fallback successful)
    assert len(videos) == 9, f"Expected 9 videos from random fallback, got {len(videos)}"

    # Verify engagement scoring was called (before fallback detected)
    mock_calc_scores.assert_called_once()


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_017_small_channel_no_constraint(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_scores
):
    """
    Test 4.4-UNIT-017: Edge case: Channel has <3 videos → no constraint applied.

    This test verifies that the channel constraint doesn't prevent selection
    when a channel has fewer than 3 videos (constraint applies naturally).

    Scenario:
    - Channel A: 2 videos (high engagement)
    - Channel B: 2 videos (high engagement)
    - Channel C: 2 videos (high engagement)
    - Request 6 videos

    Expected:
    - All 6 videos selected (2 per channel)
    - Constraint doesn't block selection when channel has <3 videos
    """
    # Setup: 3 channels with 2 videos each
    mock_videos = []
    for channel_idx in ["A", "B", "C"]:
        for video_idx in [1, 2]:
            mock_videos.append(
                {
                    "videoId": f"video_{channel_idx}{video_idx}",
                    "title": f"Channel {channel_idx} Video {video_idx}",
                    "youtubeChannelName": f"Channel {channel_idx}",
                    "durationSeconds": 300,
                }
            )

    mock_get_videos.return_value = mock_videos
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # All videos have high engagement
    mock_calc_scores.return_value = {
        f"video_{ch}{v}": 0.8 for ch in ["A", "B", "C"] for v in [1, 2]
    }

    # Call get_videos_for_grid
    videos, _ = get_videos_for_grid(count=6)

    # Verify all 6 videos selected (no constraint blocking)
    assert len(videos) == 6, f"Expected all 6 videos, got {len(videos)}"

    # Verify 2 videos per channel
    channel_counts = {}
    for video in videos:
        channel = video["youtubeChannelName"]
        channel_counts[channel] = channel_counts.get(channel, 0) + 1

    assert all(
        count == 2 for count in channel_counts.values()
    ), f"Expected 2 per channel, got {channel_counts}"


@patch("backend.services.viewing_session.calculate_engagement_scores")
@patch("backend.services.viewing_session.get_available_videos")
@patch("backend.services.viewing_session.get_watch_history_for_date")
@patch("backend.services.viewing_session.get_setting")
def test_unit_019_grace_mode_bypasses_engagement(
    mock_get_setting, mock_get_history, mock_get_videos, mock_calc_scores
):
    """
    Test 4.4-UNIT-019: If max_duration == 300: return random.sample() immediately (grace bypass).

    This test verifies Story 4.3 compatibility:
    - Grace mode (max_duration_seconds=300) bypasses engagement logic
    - Uses simple random selection instead
    - Engagement scoring NOT called

    Scenario:
    - 15 videos available
    - max_duration_seconds=300 (grace mode indicator)

    Expected:
    - Engagement scoring NOT called (bypassed)
    - Random selection used
    - Videos returned successfully
    """
    # Setup: 15 videos (all short enough for grace mode)
    mock_videos = create_mock_videos(15)
    mock_get_videos.return_value = mock_videos
    mock_get_history.return_value = []
    mock_get_setting.return_value = "30"

    # Call get_videos_for_grid with grace mode indicator
    videos, _ = get_videos_for_grid(count=6, max_duration_seconds=300)

    # Verify videos returned
    assert len(videos) == 6, f"Expected 6 grace videos, got {len(videos)}"

    # Verify engagement scoring was NOT called (bypassed)
    mock_calc_scores.assert_not_called()
