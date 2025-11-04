"""
TIER 1 Safety Tests for Engagement Scoring (Story 4.4).

These tests verify CRITICAL child safety rules in the engagement-based video selection algorithm:
- Rule 1: Banned videos NEVER selected despite high engagement
- Rule 2: Manual/grace plays excluded from engagement calculation
- Rule 3: UTC time used for all date operations
- Rule 6: SQL placeholders prevent injection attacks
- AC 4: Minimum weight floor ensures all videos selectable

Coverage Target: 100% for calculate_engagement_scores() and get_videos_for_grid()
"""

import pytest
from datetime import datetime, timezone, timedelta
from freezegun import freeze_time

from backend.services.viewing_session import calculate_engagement_scores, get_videos_for_grid
from tests.backend.conftest import (
    setup_content_source,
    create_test_video,
    setup_test_videos,
    ban_video,
    insert_watch_history,
)


# =============================================================================
# TIER 1 SAFETY TESTS (Child Safety Critical)
# =============================================================================


@pytest.mark.tier1
def test_banned_videos_excluded_despite_high_engagement(test_db_with_patch):
    """
    TIER 1 Rule 1: Banned videos NEVER appear in selection, even with high engagement.

    Verifies:
    - Videos in banned_videos table are excluded from grid
    - High engagement does NOT override ban
    - Child safety maintained

    Scenario:
    - video_1: High engagement (0.9), NOT banned
    - video_2: High engagement (0.9), BANNED
    - Result: Only video_1 appears in grid
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Set up videos
    setup_test_videos(
        test_db,
        [
            create_test_video(
                video_id="video_1",
                title="Video 1",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
            create_test_video(
                video_id="video_2",
                title="Video 2 BANNED",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
        ],
    )

    # Ban video_2
    ban_video(test_db, "video_2")

    # Create high engagement for BOTH videos (10 days ago, so no recency penalty)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []
    for video_id in ["video_1", "video_2"]:
        for _ in range(5):  # 5 watches each, all completed
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": f"Video {video_id}",
                    "channel_name": "Test Channel",
                    "watched_at": past_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )
    insert_watch_history(test_db, watch_records)

    # Get videos for grid
    videos, _ = get_videos_for_grid(count=9)

    # TIER 1 ASSERTION: Banned video NEVER appears
    video_ids = [v["videoId"] for v in videos]
    assert "video_2" not in video_ids, "TIER 1 VIOLATION: Banned video appeared in grid"
    assert "video_1" in video_ids, "Non-banned video should appear"


@pytest.mark.tier1
def test_manual_play_excluded_from_engagement_calculation(test_db_with_patch):
    """
    TIER 1 Rule 2: manual_play watches NOT counted in engagement scores.

    Verifies:
    - Parent's "Play Again" button (manual_play=1) excluded
    - Only child-initiated watches count toward engagement
    - Time limit integrity maintained

    Scenario:
    - video_1: 5 normal watches (completed) - HIGH engagement
    - video_2: 5 manual_play watches (completed) - Should have BASELINE engagement (0.5)
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Set up videos
    setup_test_videos(
        test_db,
        [
            create_test_video(
                video_id="video_1",
                title="Normal Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
            create_test_video(
                video_id="video_2",
                title="Manual Play Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
        ],
    )

    # Create watch history
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

    watch_records = []
    # video_1: 5 normal completed watches (HIGH engagement)
    for _ in range(5):
        watch_records.append(
            {
                "video_id": "video_1",
                "video_title": "Normal Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    # video_2: 5 manual_play watches (should NOT count)
    for _ in range(5):
        watch_records.append(
            {
                "video_id": "video_2",
                "video_title": "Manual Play Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 1,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_1", "video_2"])

    # TIER 1 ASSERTIONS
    assert scores["video_1"] > 0.5, "Normal watches should create high engagement"
    assert (
        scores["video_2"] == 0.5
    ), f"TIER 1 VIOLATION: manual_play watches counted in engagement (score={scores['video_2']}). Should be baseline 0.5."


@pytest.mark.tier1
def test_grace_play_excluded_from_engagement_calculation(test_db_with_patch):
    """
    TIER 1 Rule 2: grace_play watches NOT counted in engagement scores.

    Verifies:
    - Grace videos (watched after daily limit) excluded
    - Only countable watches affect engagement
    - Time limit integrity maintained

    Scenario:
    - video_1: 5 normal watches (completed) - HIGH engagement
    - video_2: 5 grace_play watches (completed) - Should have BASELINE engagement (0.5)
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Set up videos
    setup_test_videos(
        test_db,
        [
            create_test_video(
                video_id="video_1",
                title="Normal Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
            create_test_video(
                video_id="video_2",
                title="Grace Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
        ],
    )

    # Create watch history
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

    watch_records = []
    # video_1: 5 normal completed watches (HIGH engagement)
    for _ in range(5):
        watch_records.append(
            {
                "video_id": "video_1",
                "video_title": "Normal Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    # video_2: 5 grace_play watches (should NOT count)
    for _ in range(5):
        watch_records.append(
            {
                "video_id": "video_2",
                "video_title": "Grace Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 1,
                "duration_watched_seconds": 300,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_1", "video_2"])

    # TIER 1 ASSERTIONS
    assert scores["video_1"] > 0.5, "Normal watches should create high engagement"
    assert (
        scores["video_2"] == 0.5
    ), f"TIER 1 VIOLATION: grace_play watches counted in engagement (score={scores['video_2']}). Should be baseline 0.5."


@pytest.mark.tier1
@freeze_time("2025-01-15 14:30:00")  # Freeze at 2:30 PM UTC
def test_engagement_uses_utc_time_for_recency(test_db_with_patch):
    """
    TIER 1 Rule 3: All time calculations use UTC timezone.

    Verifies:
    - Recency penalty calculated using UTC, not local time
    - 24-hour window correct at timezone boundaries
    - Time limit resets work correctly across timezones

    Scenario:
    - Current time: 2025-01-15 14:30:00 UTC (frozen)
    - video_1: Watched 12 hours ago (within 24h) - Should have recency penalty (×0.3)
    - video_2: Watched 30 hours ago (beyond 24h, within 7d) - Should have medium penalty (×0.7)
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Set up videos
    setup_test_videos(
        test_db,
        [
            create_test_video(
                video_id="video_1",
                title="Recent Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
            create_test_video(
                video_id="video_2",
                title="Medium Recent Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
        ],
    )

    # Current frozen time: 2025-01-15 14:30:00 UTC
    # video_1: Watched 12 hours ago (2025-01-15 02:30:00 UTC) - within 24h
    # video_2: Watched 30 hours ago (2025-01-14 08:30:00 UTC) - beyond 24h, within 7d

    watch_12h_ago = "2025-01-15T02:30:00+00:00"  # 12 hours ago
    watch_30h_ago = "2025-01-14T08:30:00+00:00"  # 30 hours ago

    # Both videos: 5 completed watches to create engagement
    # But different recency should apply different penalties
    watch_records = []
    for _ in range(5):
        watch_records.append(
            {
                "video_id": "video_1",
                "video_title": "Recent Video",
                "channel_name": "Test Channel",
                "watched_at": watch_12h_ago,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )
        watch_records.append(
            {
                "video_id": "video_2",
                "video_title": "Medium Recent Video",
                "channel_name": "Test Channel",
                "watched_at": watch_30h_ago,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_1", "video_2"])

    # TIER 1 ASSERTIONS
    # video_1: Recent (< 24h) should have lower score due to 0.3 multiplier
    # video_2: Medium recent (24h-7d) should have higher score due to 0.7 multiplier
    assert scores["video_2"] > scores["video_1"], (
        f"TIER 1 VIOLATION: UTC time not used correctly. "
        f"video_1 (12h ago, penalty ×0.3) score={scores['video_1']}, "
        f"video_2 (30h ago, penalty ×0.7) score={scores['video_2']}. "
        f"Expected video_2 > video_1."
    )

    # Verify penalty multipliers are approximately correct
    # Base engagement same for both (5 completed out of 5 = 1.0 completion rate)
    # Replay frequency same (watched on 1 unique day each = log(2) ≈ 0.69)
    # So base_engagement ≈ 1.0 * 0.69 = 0.69
    # video_1: 0.69 * 0.3 = 0.207, but minimum floor 0.05 doesn't apply here
    # video_2: 0.69 * 0.7 = 0.483
    assert (
        0.15 < scores["video_1"] < 0.35
    ), f"video_1 score {scores['video_1']} not in expected range for ×0.3 penalty"
    assert (
        0.40 < scores["video_2"] < 0.60
    ), f"video_2 score {scores['video_2']} not in expected range for ×0.7 penalty"


@pytest.mark.tier1
def test_engagement_minimum_weight_floor(test_db_with_patch):
    """
    AC 4 / TIER 1: All videos have minimum weight floor (never completely hidden).

    Verifies:
    - Videos with very low engagement still selectable
    - Minimum weight floor of 0.05 enforced
    - Child always has variety, even for "disliked" videos

    Scenario:
    - video_1: 10 watches, 0 completed (0% completion rate) - Should have floor 0.05
    - video_2: No watch history - Should have baseline 0.5
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Set up videos
    setup_test_videos(
        test_db,
        [
            create_test_video(
                video_id="video_1",
                title="Low Engagement Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
            create_test_video(
                video_id="video_2",
                title="New Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            ),
        ],
    )

    # video_1: 10 watches, NONE completed (0% completion rate = very low engagement)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []
    for _ in range(10):
        watch_records.append(
            {
                "video_id": "video_1",
                "video_title": "Low Engagement Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 0,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 30,
            }
        )

    insert_watch_history(test_db, watch_records)

    # video_2: No watch history

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_1", "video_2"])

    # TIER 1 ASSERTIONS
    # video_1: 0% completion * log(1+days) * recency = very low, but floor should apply
    assert (
        scores["video_1"] >= 0.05
    ), f"TIER 1 VIOLATION: Minimum weight floor not enforced (score={scores['video_1']}). Must be >= 0.05."
    assert scores["video_2"] == 0.5, "New video should have baseline weight 0.5"


@pytest.mark.tier1
def test_engagement_uses_sql_placeholders(test_db_with_patch):
    """
    TIER 1 Rule 6: SQL queries use placeholders (prevent injection attacks).

    Verifies:
    - No string formatting in SQL queries
    - Parameterized queries used throughout
    - Security maintained

    Scenario:
    - Attempt to use SQL injection pattern as video_id
    - Function should safely handle it with placeholders
    - No syntax errors or unexpected behavior
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Normal video ID (NOT an injection attempt in real use)
    normal_video_id = "video_1"
    setup_test_videos(
        test_db,
        [
            create_test_video(
                video_id=normal_video_id,
                title="Normal Video",
                content_source_id=source_id,
                youtube_channel_id="UCtest",
                youtube_channel_name="Test Channel",
            )
        ],
    )

    # TIER 1 TEST: Pass potentially malicious video_id
    # If SQL uses placeholders correctly, this will safely return 0.5 (no history)
    # If SQL uses f-strings, this could cause syntax errors or unexpected behavior
    malicious_video_id = "video' OR '1'='1"

    try:
        scores = calculate_engagement_scores([normal_video_id, malicious_video_id])

        # Verify normal video scored correctly
        assert normal_video_id in scores, "Normal video should have score"
        assert scores[normal_video_id] == 0.5, "Video with no history should have baseline 0.5"

        # Verify malicious input treated as string (not executed as SQL)
        assert malicious_video_id in scores, "Malicious input should be treated as string"
        assert scores[malicious_video_id] == 0.5, "Non-existent video should have baseline 0.5"

    except Exception as e:
        pytest.fail(f"TIER 1 VIOLATION: SQL injection vulnerability detected. Exception: {e}")
