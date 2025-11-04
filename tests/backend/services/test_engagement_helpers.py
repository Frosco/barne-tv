"""
Unit Tests for Engagement Calculation Helpers (Story 4.4).

These tests verify the individual calculation components of the engagement scoring algorithm:
- Completion rate calculation
- Replay frequency weighting
- Recency decay penalties (24h, 7d, >7d)
- Baseline weight for new videos
- Minimum weight floor enforcement

These are focused unit tests on the mathematical functions underlying the algorithm.
"""

import math
from datetime import datetime, timezone, timedelta
from freezegun import freeze_time

from backend.services.viewing_session import calculate_engagement_scores
from tests.backend.conftest import (
    setup_content_source,
    create_test_video,
    setup_test_videos,
    insert_watch_history,
)


def test_calculate_completion_rate(test_db_with_patch):
    """
    Test completion rate calculation: (completed_watches / total_watches).

    Scenario:
    - video_1: 5 watches, 3 completed → 60% completion rate
    - video_2: 10 watches, 8 completed → 80% completion rate
    - video_3: 5 watches, 0 completed → 0% completion rate (hits minimum floor)

    Expected:
    - video_2 has highest engagement (80% completion)
    - video_1 has medium engagement (60% completion)
    - video_3 has minimum floor weight (0% completion but >0.05 weight)
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id=f"video_{i}", content_source_id=source_id)
            for i in range(1, 4)
        ],
    )

    # Create watch history (10 days ago to avoid recency penalty)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []

    # video_1: 5 watches, 3 completed (60%)
    for i in range(5):
        watch_records.append(
            {
                "video_id": "video_1",
                "video_title": "Video 1",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1 if i < 3 else 0,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300 if i < 3 else 30,
            }
        )

    # video_2: 10 watches, 8 completed (80%)
    for i in range(10):
        watch_records.append(
            {
                "video_id": "video_2",
                "video_title": "Video 2",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1 if i < 8 else 0,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300 if i < 8 else 30,
            }
        )

    # video_3: 5 watches, 0 completed (0%)
    for i in range(5):
        watch_records.append(
            {
                "video_id": "video_3",
                "video_title": "Video 3",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 0,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 30,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_1", "video_2", "video_3"])

    # Assertions: Higher completion rate = higher engagement
    assert scores["video_2"] > scores["video_1"], "80% completion should beat 60%"
    assert scores["video_1"] > scores["video_3"], "60% completion should beat 0%"
    assert scores["video_3"] >= 0.05, "0% completion should still have minimum floor weight"


def test_replay_frequency_weight(test_db_with_patch):
    """
    Test replay frequency weighting: log(1 + unique_days_watched).

    Scenario:
    - video_1: Watched on 2 different days (5 watches each day)
    - video_2: Watched on 8 different days (2 watches each day)

    Expected:
    - video_2 has higher engagement (more days = more replay interest)
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id=f"video_{i}", content_source_id=source_id)
            for i in range(1, 3)
        ],
    )

    watch_records = []

    # video_1: Watched on 2 different days (10 watches total, 5 per day)
    for day_offset in [10, 11]:
        watch_date = (datetime.now(timezone.utc) - timedelta(days=day_offset)).isoformat()
        for _ in range(5):
            watch_records.append(
                {
                    "video_id": "video_1",
                    "video_title": "Video 1",
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    # video_2: Watched on 8 different days (16 watches total, 2 per day)
    for day_offset in [10, 11, 12, 13, 14, 15, 16, 17]:
        watch_date = (datetime.now(timezone.utc) - timedelta(days=day_offset)).isoformat()
        for _ in range(2):
            watch_records.append(
                {
                    "video_id": "video_2",
                    "video_title": "Video 2",
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_1", "video_2"])

    # Assertion: More unique days watched = higher engagement
    assert (
        scores["video_2"] > scores["video_1"]
    ), f"8 unique days should beat 2 unique days (scores: {scores})"


@freeze_time("2025-01-15 14:30:00")
def test_recency_decay_24h_penalty(test_db_with_patch):
    """
    Test recency decay for videos watched within last 24 hours.

    Scenario (frozen time: 2025-01-15 14:30:00 UTC):
    - video_recent: Watched 12 hours ago → 70% penalty (×0.3)
    - video_old: Watched 10 days ago → No penalty (×1.0)

    Expected:
    - video_old has ~3.3x higher engagement score than video_recent
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_recent", content_source_id=source_id),
            create_test_video(video_id="video_old", content_source_id=source_id),
        ],
    )

    # Frozen time: 2025-01-15 14:30:00 UTC
    recent_watch = "2025-01-15T02:30:00+00:00"  # 12 hours ago (< 24h)
    old_watch = "2025-01-05T14:30:00+00:00"  # 10 days ago (> 7d)

    watch_records = []

    # Both videos: Same engagement (5 completed watches)
    for video_id, watch_date in [("video_recent", recent_watch), ("video_old", old_watch)]:
        for _ in range(5):
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": video_id,
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_recent", "video_old"])

    # Assertion: Recent penalty should make old video ~3x more weighted
    # (×0.3 vs ×1.0 = 3.33x ratio)
    ratio = scores["video_old"] / scores["video_recent"]
    assert ratio > 2.5, f"Old video should have ~3x weight vs recent (ratio: {ratio:.2f}x)"


@freeze_time("2025-01-15 14:30:00")
def test_recency_decay_week_penalty(test_db_with_patch):
    """
    Test recency decay for videos watched 24h-7d ago.

    Scenario (frozen time: 2025-01-15 14:30:00 UTC):
    - video_medium: Watched 3 days ago → 30% penalty (×0.7)
    - video_old: Watched 10 days ago → No penalty (×1.0)

    Expected:
    - video_old has ~1.4x higher engagement than video_medium
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_medium", content_source_id=source_id),
            create_test_video(video_id="video_old", content_source_id=source_id),
        ],
    )

    # Frozen time: 2025-01-15 14:30:00 UTC
    medium_watch = "2025-01-12T14:30:00+00:00"  # 3 days ago (24h < x < 7d)
    old_watch = "2025-01-05T14:30:00+00:00"  # 10 days ago (> 7d)

    watch_records = []

    # Both videos: Same engagement (5 completed watches)
    for video_id, watch_date in [("video_medium", medium_watch), ("video_old", old_watch)]:
        for _ in range(5):
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": video_id,
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_medium", "video_old"])

    # Assertion: Medium recency penalty should make old video ~1.4x more weighted
    # (×0.7 vs ×1.0 = 1.43x ratio)
    ratio = scores["video_old"] / scores["video_medium"]
    assert ratio > 1.2, f"Old video should have ~1.4x weight vs medium recent (ratio: {ratio:.2f}x)"


@freeze_time("2025-01-15 14:30:00")
def test_recency_decay_no_penalty_old_watches(test_db_with_patch):
    """
    Test that old watches (>7 days ago) have NO recency penalty.

    Scenario (frozen time: 2025-01-15 14:30:00 UTC):
    - video_8d: Watched 8 days ago
    - video_30d: Watched 30 days ago

    Expected:
    - Both have similar engagement scores (no recency penalty difference)
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_8d", content_source_id=source_id),
            create_test_video(video_id="video_30d", content_source_id=source_id),
        ],
    )

    # Frozen time: 2025-01-15 14:30:00 UTC
    watch_8d = "2025-01-07T14:30:00+00:00"  # 8 days ago (> 7d)
    watch_30d = "2024-12-16T14:30:00+00:00"  # 30 days ago (> 7d)

    watch_records = []

    # Both videos: Same engagement (5 completed watches)
    for video_id, watch_date in [("video_8d", watch_8d), ("video_30d", watch_30d)]:
        for _ in range(5):
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": video_id,
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_8d", "video_30d"])

    # Assertion: Both should have similar scores (no penalty for either)
    ratio = max(scores["video_8d"], scores["video_30d"]) / min(
        scores["video_8d"], scores["video_30d"]
    )
    assert ratio < 1.1, f"Old videos should have similar weights (ratio: {ratio:.2f}x, max 1.1x)"


def test_baseline_weight_for_new_videos(test_db_with_patch):
    """
    Test that videos with no watch history get baseline weight 0.5.

    Scenario:
    - video_new: No watch history at all
    - video_watched: Has watch history

    Expected:
    - video_new has exactly 0.5 weight (baseline)
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_new", content_source_id=source_id),
            create_test_video(video_id="video_watched", content_source_id=source_id),
        ],
    )

    # Only add watch history for video_watched (not video_new)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []
    for _ in range(5):
        watch_records.append(
            {
                "video_id": "video_watched",
                "video_title": "Watched Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_new", "video_watched"])

    # Assertion: New video with no history has baseline weight 0.5
    assert (
        scores["video_new"] == 0.5
    ), f"New video should have baseline weight 0.5, got {scores['video_new']}"
    assert (
        scores["video_watched"] != 0.5
    ), "Watched video should have different weight from baseline"


def test_minimum_weight_floor_enforcement(test_db_with_patch):
    """
    Test that minimum weight floor (0.05) is enforced for very low engagement.

    Scenario:
    - video_terrible: 20 watches, 0 completed, very recent → Calculated weight would be ~0.0
    - Minimum floor: 0.05 must be enforced

    Expected:
    - video_terrible has weight >= 0.05 (floor enforced)
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [create_test_video(video_id="video_terrible", content_source_id=source_id)],
    )

    # Create worst-case scenario: Many watches, 0% completion, very recent
    recent_watch = (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat()
    watch_records = []
    for _ in range(20):
        watch_records.append(
            {
                "video_id": "video_terrible",
                "video_title": "Terrible Video",
                "channel_name": "Test Channel",
                "watched_at": recent_watch,
                "completed": 0,  # NEVER completed
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 10,  # Always skipped quickly
            }
        )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_terrible"])

    # Assertion: Floor of 0.05 enforced
    assert (
        scores["video_terrible"] >= 0.05
    ), f"Minimum floor 0.05 not enforced, got {scores['video_terrible']}"
    assert (
        scores["video_terrible"] <= 0.10
    ), f"Weight should be near floor for terrible engagement, got {scores['video_terrible']}"


def test_database_context_manager_used():
    """
    Test 4.4-UNIT-018: Verify database context manager is used for watch_history queries.

    TIER 2 Rule 7: Database operations must use context manager (with get_connection() as conn:)

    This test verifies code quality by inspecting the calculate_engagement_scores
    function source code to ensure proper database connection management.

    Expected:
    - calculate_engagement_scores uses 'with get_connection() as conn:' pattern
    - No raw connection.execute() calls without context manager
    """
    import inspect

    # Get source code of calculate_engagement_scores
    source = inspect.getsource(calculate_engagement_scores)

    # Verify context manager pattern is used
    assert (
        "with get_connection() as conn:" in source
    ), "calculate_engagement_scores must use 'with get_connection() as conn:' pattern (TIER 2 Rule 7)"

    # Verify no raw get_connection() calls without 'with' statement
    lines = source.split("\n")
    for i, line in enumerate(lines):
        if "get_connection()" in line and "with" not in line and "import" not in line:
            raise AssertionError(
                f"Line {i+1} uses get_connection() without context manager: {line.strip()}"
            )


def test_base_engagement_formula(test_db_with_patch):
    """
    Test 4.4-UNIT-003: Verify base engagement formula = completion_rate × log(1 + unique_days).

    This test validates that the core engagement calculation correctly combines
    completion rate and replay frequency using logarithmic scaling.

    Scenario:
    - video_1: 100% completion (5/5), 3 unique days
      → base_engagement = 1.0 × log(1 + 3) = 1.0 × log(4) ≈ 1.39
    - video_2: 50% completion (5/10), 7 unique days
      → base_engagement = 0.5 × log(1 + 7) = 0.5 × log(8) ≈ 1.04

    Expected:
    - video_1 has higher engagement (better completion outweighs fewer days)
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_1", content_source_id=source_id),
            create_test_video(video_id="video_2", content_source_id=source_id),
        ],
    )

    watch_records = []

    # video_1: 100% completion (5/5), 3 unique days (old watches to avoid recency penalty)
    for day_offset in [10, 11, 12]:  # 3 unique days
        watch_date = (datetime.now(timezone.utc) - timedelta(days=day_offset)).isoformat()
        for _ in range(2 if day_offset == 10 else 2 if day_offset == 11 else 1):
            watch_records.append(
                {
                    "video_id": "video_1",
                    "video_title": "Video 1",
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1,  # 100% completion
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    # video_2: 50% completion (5/10), 7 unique days (old watches to avoid recency penalty)
    for day_offset in [10, 11, 12, 13, 14, 15, 16]:  # 7 unique days
        watch_date = (datetime.now(timezone.utc) - timedelta(days=day_offset)).isoformat()
        for i in range(2 if day_offset < 14 else 1):
            watch_records.append(
                {
                    "video_id": "video_2",
                    "video_title": "Video 2",
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1 if i == 0 else 0,  # 50% completion
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300 if i == 0 else 30,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_1", "video_2"])

    # Verify formula: completion_rate × log(1 + unique_days)
    # video_1: 1.0 × log(4) ≈ 1.39
    # video_2: 0.5 × log(8) ≈ 1.04
    expected_v1 = 1.0 * math.log(1 + 3)  # ≈ 1.39
    expected_v2 = 0.5 * math.log(1 + 7)  # ≈ 1.04

    # Both should have similar engagement but video_1 slightly higher
    assert (
        scores["video_1"] > scores["video_2"]
    ), f"video_1 (completion={expected_v1:.2f}) should beat video_2 (completion={expected_v2:.2f})"


@freeze_time("2025-01-15 14:30:00")
def test_hours_since_last_watch_calculation(test_db_with_patch):
    """
    Test 4.4-UNIT-020: Verify hours since last watch calculation with freezegun.

    This test validates that the time delta calculation correctly determines
    hours elapsed since most recent watch, using UTC time throughout.

    Scenario (frozen time: 2025-01-15 14:30:00 UTC):
    - video_1h: Watched 1 hour ago → 1 hour since
    - video_12h: Watched 12 hours ago → 12 hours since
    - video_25h: Watched 25 hours ago → 25 hours since

    Expected:
    - Different recency penalties based on hours: <24h = ×0.3, >24h but <168h = ×0.7
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_1h", content_source_id=source_id),
            create_test_video(video_id="video_12h", content_source_id=source_id),
            create_test_video(video_id="video_25h", content_source_id=source_id),
        ],
    )

    # Frozen time: 2025-01-15 14:30:00 UTC
    watch_1h = "2025-01-15T13:30:00+00:00"  # 1 hour ago
    watch_12h = "2025-01-15T02:30:00+00:00"  # 12 hours ago
    watch_25h = "2025-01-14T13:30:00+00:00"  # 25 hours ago

    watch_records = []

    # All videos: Same base engagement (5 completed watches, 1 unique day)
    for video_id, watch_date in [
        ("video_1h", watch_1h),
        ("video_12h", watch_12h),
        ("video_25h", watch_25h),
    ]:
        for _ in range(5):
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": video_id,
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_1h", "video_12h", "video_25h"])

    # Verify recency penalties based on hours since last watch
    # video_1h and video_12h: <24h → ×0.3 penalty (should have similar scores)
    # video_25h: >24h but <168h → ×0.7 penalty (higher score)
    assert (
        abs(scores["video_1h"] - scores["video_12h"]) < 0.01
    ), "Both videos watched <24h ago should have same ×0.3 penalty"
    assert (
        scores["video_25h"] > scores["video_12h"]
    ), "Video watched >24h ago should have higher score (×0.7 vs ×0.3)"


def test_unique_watch_days_parsing(test_db_with_patch):
    """
    Test 4.4-UNIT-021: Verify unique watch days parsing from watch_history.

    This test validates that the SQL query correctly extracts COUNT(DISTINCT DATE(watched_at))
    to determine how many different days a video was watched.

    Scenario:
    - video_varied: Watched 10 times across 5 different days
    - video_binge: Watched 10 times all on the same day

    Expected:
    - video_varied has higher engagement (more unique days = higher replay weight)
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_varied", content_source_id=source_id),
            create_test_video(video_id="video_binge", content_source_id=source_id),
        ],
    )

    watch_records = []

    # video_varied: 10 watches across 5 different days (2 watches per day)
    for day_offset in [10, 11, 12, 13, 14]:  # 5 unique days
        watch_date = (datetime.now(timezone.utc) - timedelta(days=day_offset)).isoformat()
        for _ in range(2):  # 2 watches per day
            watch_records.append(
                {
                    "video_id": "video_varied",
                    "video_title": "Varied Video",
                    "channel_name": "Test Channel",
                    "watched_at": watch_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    # video_binge: 10 watches all on the same day
    watch_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    for _ in range(10):
        watch_records.append(
            {
                "video_id": "video_binge",
                "video_title": "Binge Video",
                "channel_name": "Test Channel",
                "watched_at": watch_date,
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_varied", "video_binge"])

    # Verify: 5 unique days should beat 1 unique day
    # Expected: log(1+5)=log(6)≈1.79 vs log(1+1)=log(2)≈0.69 (2.6x difference)
    assert (
        scores["video_varied"] > scores["video_binge"]
    ), f"5 unique days should beat 1 unique day (scores: varied={scores['video_varied']:.2f}, binge={scores['video_binge']:.2f})"
    ratio = scores["video_varied"] / scores["video_binge"]
    assert ratio > 2.0, f"Ratio should be >2x (log(6)/log(2) ≈ 2.6), got {ratio:.2f}x"


def test_logarithmic_scaling_correctness(test_db_with_patch):
    """
    Test 4.4-UNIT-022: Verify logarithmic scaling formula correctness.

    This test validates that replay frequency uses log(1 + unique_days) correctly:
    - log(1 + 0) = log(1) = 0 (no watches)
    - log(1 + 10) = log(11) ≈ 2.4

    Scenario:
    - video_10d: Watched on 10 different days, 100% completion
    - video_0d: No watch history (baseline)

    Expected:
    - video_10d has score = 1.0 × log(11) × 1.0 (no recency penalty) ≈ 2.4
    - video_0d has baseline score = 0.5
    """
    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_10d", content_source_id=source_id),
            create_test_video(video_id="video_0d", content_source_id=source_id),
        ],
    )

    watch_records = []

    # video_10d: Watched on 10 different days (old watches to avoid recency penalty)
    for day_offset in range(10, 20):  # 10 unique days (10-19 days ago)
        watch_date = (datetime.now(timezone.utc) - timedelta(days=day_offset)).isoformat()
        watch_records.append(
            {
                "video_id": "video_10d",
                "video_title": "10 Days Video",
                "channel_name": "Test Channel",
                "watched_at": watch_date,
                "completed": 1,  # 100% completion
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    # video_0d: No watch history (will get baseline)

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_10d", "video_0d"])

    # Verify logarithmic scaling
    # video_10d: 1.0 × log(1 + 10) = log(11) ≈ 2.398
    expected_log_11 = math.log(1 + 10)
    assert (
        abs(expected_log_11 - 2.398) < 0.01
    ), f"log(11) should be ≈2.398, got {expected_log_11:.3f}"

    # video_0d should have baseline weight 0.5
    assert scores["video_0d"] == 0.5, f"video_0d should have baseline 0.5, got {scores['video_0d']}"

    # video_10d should have score ≈ 2.4 (log(11) with 100% completion, no recency penalty)
    assert (
        scores["video_10d"] > 2.0
    ), f"video_10d should have score >2.0, got {scores['video_10d']:.2f}"
    assert (
        scores["video_10d"] < 2.5
    ), f"video_10d should have score <2.5, got {scores['video_10d']:.2f}"
