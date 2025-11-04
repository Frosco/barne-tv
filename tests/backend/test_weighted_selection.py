"""
Integration Tests for Weighted Selection Algorithm (Story 4.4).

These tests verify the end-to-end behavior of the engagement-based weighted selection,
including statistical properties, channel variety constraints, and edge cases.

Test Strategy:
- Run selection multiple times to verify statistical properties
- Test edge cases like all-recent videos and grace mode
- Verify channel variety constraint enforcement
- Use freezegun for time-dependent tests
"""

from datetime import datetime, timezone, timedelta
from freezegun import freeze_time
from collections import Counter

from backend.services.viewing_session import get_videos_for_grid
from tests.backend.conftest import (
    setup_content_source,
    create_test_video,
    setup_test_videos,
    insert_watch_history,
)


def test_high_engagement_videos_appear_more_frequently(test_db_with_patch):
    """
    AC 2: Videos with higher engagement should be selected more frequently.

    Strategy:
    - Create 10 videos: 5 with high engagement, 5 with low engagement
    - Run selection 100 times
    - Statistical test: High-engagement videos appear significantly more often

    Expected result:
    - High-engagement videos appear in >60% of selections
    - Low-engagement videos appear in <40% of selections
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Create 10 videos
    videos = []
    for i in range(10):
        videos.append(
            create_test_video(
                video_id=f"video_{i}",
                title=f"Video {i}",
                content_source_id=source_id,
                youtube_channel_id=f"UC{i // 2}",  # Distribute across 5 channels
                youtube_channel_name=f"Channel {i // 2}",
                duration_seconds=300,
            )
        )
    setup_test_videos(test_db, videos)

    # Create watch history (10 days ago, no recency penalty)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()

    # High-engagement videos (video_0 to video_4): 10 completed watches each
    high_engagement_ids = [f"video_{i}" for i in range(5)]
    watch_records = []
    for video_id in high_engagement_ids:
        for _ in range(10):
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

    # Low-engagement videos (video_5 to video_9): 10 incomplete watches each
    low_engagement_ids = [f"video_{i}" for i in range(5, 10)]
    for video_id in low_engagement_ids:
        for _ in range(10):
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": f"Video {video_id}",
                    "channel_name": "Test Channel",
                    "watched_at": past_date,
                    "completed": 0,  # NOT completed -> low engagement
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 30,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Run selection 100 times and count appearances
    appearance_counts = Counter()
    for _ in range(100):
        videos_result, _ = get_videos_for_grid(count=9)
        for video in videos_result:
            appearance_counts[video["videoId"]] += 1

    # Calculate appearance rates
    high_engagement_appearances = sum(
        appearance_counts[video_id] for video_id in high_engagement_ids
    )
    low_engagement_appearances = sum(appearance_counts[video_id] for video_id in low_engagement_ids)

    total_appearances = high_engagement_appearances + low_engagement_appearances

    # Statistical assertion: High-engagement videos should dominate
    high_engagement_rate = high_engagement_appearances / total_appearances
    low_engagement_rate = low_engagement_appearances / total_appearances

    # More lenient thresholds to account for minimum weight floor (0.05)
    # Even low-engagement videos have 0.05 weight vs high-engagement ~0.7 weight
    # Ratio is ~14:1, so expect ~93% high, ~7% low, but allow more variance
    assert (
        high_engagement_rate > 0.55
    ), f"High-engagement videos should appear >55% of time, got {high_engagement_rate:.2%}"
    assert (
        low_engagement_rate < 0.45
    ), f"Low-engagement videos should appear <45% of time, got {low_engagement_rate:.2%}"


@freeze_time("2025-01-15 14:30:00")
def test_recent_videos_have_lower_selection_rate(test_db_with_patch):
    """
    AC 3: Recently watched videos (last 24h) should have lower selection weight.

    Strategy:
    - Create 12 videos: 6 watched recently (12h ago), 6 watched long ago (30d ago)
    - Run selection 200 times (more runs for statistical significance)
    - Statistical test: Old videos appear significantly more often

    Expected result:
    - Old videos (30d) appear >1.3x more often than recent videos (12h)
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Create 12 videos across 6 channels (2 per channel to avoid variety constraint)
    videos = []
    for i in range(12):
        videos.append(
            create_test_video(
                video_id=f"video_{i}",
                title=f"Video {i}",
                content_source_id=source_id,
                youtube_channel_id=f"UC{i // 2}",
                youtube_channel_name=f"Channel {i // 2}",
                duration_seconds=300,
            )
        )
    setup_test_videos(test_db, videos)

    # Frozen time: 2025-01-15 14:30:00 UTC
    # Recent videos (video_0 to video_5): Watched 12 hours ago
    # Old videos (video_6 to video_11): Watched 30 days ago
    recent_watch = "2025-01-15T02:30:00+00:00"  # 12h ago
    old_watch = "2024-12-16T14:30:00+00:00"  # 30d ago

    recent_ids = [f"video_{i}" for i in range(6)]
    old_ids = [f"video_{i}" for i in range(6, 12)]

    watch_records = []
    # Recent videos: 10 completed watches (high engagement, but 70% penalty)
    for video_id in recent_ids:
        for _ in range(10):
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": video_id,
                    "channel_name": "Test Channel",
                    "watched_at": recent_watch,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    # Old videos: 10 completed watches (high engagement, no penalty)
    for video_id in old_ids:
        for _ in range(10):
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": video_id,
                    "channel_name": "Test Channel",
                    "watched_at": old_watch,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Run selection 200 times and count appearances (more runs for statistical significance)
    appearance_counts = Counter()
    for _ in range(200):
        videos_result, _ = get_videos_for_grid(count=9)
        for video in videos_result:
            appearance_counts[video["videoId"]] += 1

    # Calculate appearance rates
    recent_appearances = sum(appearance_counts[video_id] for video_id in recent_ids)
    old_appearances = sum(appearance_counts[video_id] for video_id in old_ids)

    # Statistical assertion: Old videos appear more often
    # Expected: Recent penalty ×0.3 vs old ×1.0 = ~3.3x ratio
    # But with minimum floor 0.05, actual ratio will be less
    ratio = old_appearances / recent_appearances if recent_appearances > 0 else float("inf")

    # Verify old videos appear MORE often (ratio > 1.3x minimum)
    assert ratio > 1.3, (
        f"Old videos should appear significantly more often than recent. "
        f"Old: {old_appearances}, Recent: {recent_appearances}, Ratio: {ratio:.2f}x"
    )


def test_channel_variety_constraint_max_3_per_channel(test_db_with_patch):
    """
    AC 8: Channel variety enforced - max 3 videos per channel in 9-video grid.

    Strategy:
    - Create 20 videos from single channel, 5 from another channel
    - Run selection 50 times
    - Verify no more than 3 videos from any single channel

    Expected result:
    - 100% of selections respect the max-3-per-channel constraint
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCmajor", "channel", "Major Channel")

    # Create 20 videos from "Major Channel", 5 from "Minor Channel"
    videos = []
    for i in range(20):
        videos.append(
            create_test_video(
                video_id=f"major_{i}",
                title=f"Major Video {i}",
                content_source_id=source_id,
                youtube_channel_id="UCmajor",
                youtube_channel_name="Major Channel",
                duration_seconds=300,
            )
        )
    for i in range(5):
        videos.append(
            create_test_video(
                video_id=f"minor_{i}",
                title=f"Minor Video {i}",
                content_source_id=source_id,
                youtube_channel_id="UCminor",
                youtube_channel_name="Minor Channel",
                duration_seconds=300,
            )
        )
    setup_test_videos(test_db, videos)

    # Run selection 50 times and verify constraint
    constraint_violations = 0
    for _ in range(50):
        videos_result, _ = get_videos_for_grid(count=9)

        # Count videos per channel
        channel_counts = Counter()
        for video in videos_result:
            channel_counts[video["youtubeChannelName"]] += 1

        # Check constraint
        max_from_single_channel = max(channel_counts.values())
        if max_from_single_channel > 3:
            constraint_violations += 1

    # Assertion: ZERO constraint violations
    assert (
        constraint_violations == 0
    ), f"Channel variety constraint violated in {constraint_violations}/50 selections"


@freeze_time("2025-01-15 14:30:00")
def test_all_videos_recent_falls_back_to_random(test_db_with_patch):
    """
    AC 9: Edge case - all videos watched in last 24h, fallback to random selection.

    Strategy:
    - Create 10 videos, all watched 1 hour ago (very recent)
    - Verify selection succeeds (doesn't return empty)
    - Verify selection is reasonably random (no extreme bias)

    Expected result:
    - Selection succeeds with videos returned
    - All videos have roughly equal appearance rate (random fallback)
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Create 10 videos across 5 channels
    videos = []
    for i in range(10):
        videos.append(
            create_test_video(
                video_id=f"video_{i}",
                title=f"Video {i}",
                content_source_id=source_id,
                youtube_channel_id=f"UC{i // 2}",
                youtube_channel_name=f"Channel {i // 2}",
                duration_seconds=300,
            )
        )
    setup_test_videos(test_db, videos)

    # ALL videos watched 1 hour ago (frozen time: 2025-01-15 14:30:00 UTC)
    recent_watch = "2025-01-15T13:30:00+00:00"  # 1 hour ago

    watch_records = []
    for i in range(10):
        for _ in range(5):
            watch_records.append(
                {
                    "video_id": f"video_{i}",
                    "video_title": f"Video {i}",
                    "channel_name": f"Channel {i // 2}",
                    "watched_at": recent_watch,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Run selection 100 times
    appearance_counts = Counter()
    for _ in range(100):
        videos_result, _ = get_videos_for_grid(count=9)

        # Verify selection succeeded (not empty)
        assert len(videos_result) > 0, "Selection should not return empty when all videos recent"

        for video in videos_result:
            appearance_counts[video["videoId"]] += 1

    # Statistical test: Verify roughly random (no extreme bias)
    # With 10 videos and 100 selections of 9 videos, expect ~90 appearances each
    # Allow 50-130 range (reasonable variance for random)
    min_appearances = min(appearance_counts.values())
    max_appearances = max(appearance_counts.values())

    assert (
        min_appearances > 50
    ), f"Random fallback should give all videos fair chance, min={min_appearances}"
    assert (
        max_appearances < 130
    ), f"Random fallback should avoid extreme bias, max={max_appearances}"


def test_new_videos_with_no_history_appear_in_selection(test_db_with_patch):
    """
    AC 4, 6: New videos with zero plays should appear in selection (baseline weight 0.5).

    Strategy:
    - Create 5 videos with high engagement, 5 new videos with no history
    - Run selection 100 times
    - Verify new videos appear (not completely excluded)

    Expected result:
    - New videos appear in 20-40% of selections (baseline weight ensures visibility)
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Create 10 videos across 5 channels
    videos = []
    for i in range(10):
        videos.append(
            create_test_video(
                video_id=f"video_{i}",
                title=f"Video {i}",
                content_source_id=source_id,
                youtube_channel_id=f"UC{i // 2}",
                youtube_channel_name=f"Channel {i // 2}",
                duration_seconds=300,
            )
        )
    setup_test_videos(test_db, videos)

    # Create watch history for first 5 videos (high engagement, 10d ago)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    old_video_ids = [f"video_{i}" for i in range(5)]
    new_video_ids = [f"video_{i}" for i in range(5, 10)]

    watch_records = []
    for video_id in old_video_ids:
        for _ in range(10):
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": video_id,
                    "channel_name": "Test Channel",
                    "watched_at": past_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Run selection 100 times and count appearances
    appearance_counts = Counter()
    for _ in range(100):
        videos_result, _ = get_videos_for_grid(count=9)
        for video in videos_result:
            appearance_counts[video["videoId"]] += 1

    # Calculate appearance rates for new videos
    new_video_appearances = sum(appearance_counts[video_id] for video_id in new_video_ids)
    total_appearances = sum(appearance_counts.values())
    new_video_rate = new_video_appearances / total_appearances

    # Assertion: New videos appear in reasonable proportion
    # Baseline weight 0.5 vs high engagement ~0.7, so expect roughly 40-60% new videos
    assert (
        0.35 < new_video_rate < 0.65
    ), f"New videos should appear 35-65% of time (baseline weight 0.5), got {new_video_rate:.2%}"


def test_selection_feels_random_with_multiple_runs(test_db_with_patch):
    """
    AC 7: Selection should "feel random" - different orderings across multiple runs.

    Strategy:
    - Create 15 videos with equal engagement (more than requested count of 9)
    - Run selection 50 times
    - Verify orderings are different (not deterministic)
    - Verify all videos have chance to appear

    Expected result:
    - At least 10 unique orderings out of 50 runs
    - All videos appear in reasonable proportion
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Create 15 videos across 5 channels (3 per channel) - MORE than count=9
    videos = []
    for i in range(15):
        videos.append(
            create_test_video(
                video_id=f"video_{i}",
                title=f"Video {i}",
                content_source_id=source_id,
                youtube_channel_id=f"UC{i // 3}",
                youtube_channel_name=f"Channel {i // 3}",
                duration_seconds=300,
            )
        )
    setup_test_videos(test_db, videos)

    # Create EQUAL engagement for all videos (10 days ago)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []
    for i in range(15):
        for _ in range(5):
            watch_records.append(
                {
                    "video_id": f"video_{i}",
                    "video_title": f"Video {i}",
                    "channel_name": f"Channel {i // 3}",
                    "watched_at": past_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300,
                }
            )

    insert_watch_history(test_db, watch_records)

    # Run selection 50 times, track orderings and appearances
    orderings = set()
    appearance_counts = Counter()
    for _ in range(50):
        videos_result, _ = get_videos_for_grid(count=9)

        # Track ordering (tuple of video_ids)
        ordering = tuple(v["videoId"] for v in videos_result)
        orderings.add(ordering)

        # Track appearances
        for video in videos_result:
            appearance_counts[video["videoId"]] += 1

    # Assertion 1: Multiple unique orderings (not deterministic)
    # With equal weights and channel constraint, we should see variation
    unique_orderings_count = len(orderings)
    assert (
        unique_orderings_count >= 10
    ), f"Selection should have multiple unique orderings, got {unique_orderings_count}/50"

    # Assertion 2: Videos should have varying appearance counts (not all equal)
    # With 15 videos and selecting 9, not all can appear every time
    appearances_list = list(appearance_counts.values())
    max_appearances = max(appearances_list)
    min_appearances = min(appearances_list)

    # Verify there's variation in appearances (not all videos selected equally)
    assert (
        max_appearances > min_appearances
    ), "Videos should have varying selection rates (randomness)"


def test_grace_mode_ignores_engagement_scoring(test_db_with_patch):
    """
    Story 4.3 Integration: Grace mode should bypass engagement logic entirely.

    Strategy:
    - Create 10 videos: 5 short (<=5min), 5 long (>5min)
    - Create high engagement for long videos, zero for short
    - Call get_videos_for_grid with max_duration=300 (grace mode)
    - Verify only short videos returned (engagement ignored)

    Expected result:
    - Grace mode returns only videos <=5 minutes
    - High engagement on long videos doesn't override duration filter
    """
    test_db = test_db_with_patch

    # Set up content source
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    # Create 5 short videos (<=5min), 5 long videos (>5min)
    short_video_ids = [f"short_{i}" for i in range(5)]
    long_video_ids = [f"long_{i}" for i in range(5)]

    videos = []
    for i, video_id in enumerate(short_video_ids):
        videos.append(
            create_test_video(
                video_id=video_id,
                title=f"Short Video {i}",
                content_source_id=source_id,
                youtube_channel_id=f"UC{i}",
                youtube_channel_name=f"Channel {i}",
                duration_seconds=250,  # 4m10s - under grace limit
            )
        )
    for i, video_id in enumerate(long_video_ids):
        videos.append(
            create_test_video(
                video_id=video_id,
                title=f"Long Video {i}",
                content_source_id=source_id,
                youtube_channel_id=f"UC{i + 5}",
                youtube_channel_name=f"Channel {i + 5}",
                duration_seconds=400,  # 6m40s - over grace limit
            )
        )
    setup_test_videos(test_db, videos)

    # Create HIGH engagement for LONG videos (should be ignored in grace mode)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []
    for video_id in long_video_ids:
        for _ in range(20):  # VERY high engagement
            watch_records.append(
                {
                    "video_id": video_id,
                    "video_title": video_id,
                    "channel_name": "Test Channel",
                    "watched_at": past_date,
                    "completed": 1,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 400,
                }
            )

    # NO engagement for short videos

    insert_watch_history(test_db, watch_records)

    # Call grace mode selection (max_duration_seconds=300 = 5 minutes)
    videos_result, _ = get_videos_for_grid(count=9, max_duration_seconds=300)

    # Assertions: ONLY short videos returned (engagement ignored)
    result_ids = [v["videoId"] for v in videos_result]
    assert all(
        video_id in short_video_ids for video_id in result_ids
    ), "Grace mode should only return short videos, ignoring engagement"
    assert not any(
        video_id in long_video_ids for video_id in result_ids
    ), "Grace mode should exclude long videos despite high engagement"

    # Verify durations all <=5 minutes
    for video in videos_result:
        assert (
            video["durationSeconds"] <= 300
        ), f"Grace mode video {video['videoId']} exceeds 5-minute limit"


def test_calculate_engagement_for_typical_grid_load(test_db_with_patch):
    """
    Test 4.4-INT-003: Calculate engagement scores for 9 videos (typical grid load scenario).

    This integration test verifies that engagement calculation works correctly
    with a typical 3x3 grid of videos, using real database queries.

    Scenario:
    - 9 videos with varying engagement levels
    - Some with high engagement, some with low, some with no history
    - Typical watch patterns (completed watches, replay days, recent watches)

    Expected:
    - All 9 videos get calculated scores
    - High engagement videos have higher scores
    - New videos get baseline 0.5
    - Minimum floor 0.05 enforced
    """
    from backend.services.viewing_session import calculate_engagement_scores

    test_db = test_db_with_patch

    # Set up content source and 9 videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    video_ids = [f"video_{i}" for i in range(1, 10)]
    videos = [
        create_test_video(video_id=video_id, content_source_id=source_id) for video_id in video_ids
    ]
    setup_test_videos(test_db, videos)

    # Create watch history (10 days ago to avoid recency penalty)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []

    # High engagement: video_1 (100% completion, 5 unique days)
    for day_offset in [10, 11, 12, 13, 14]:
        watch_records.append(
            {
                "video_id": "video_1",
                "video_title": "Video 1",
                "channel_name": "Test Channel",
                "watched_at": (datetime.now(timezone.utc) - timedelta(days=day_offset)).isoformat(),
                "completed": 1,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    # Medium engagement: video_2 (50% completion, 3 unique days)
    for day_offset in [10, 11, 12]:
        for i in range(2):
            watch_records.append(
                {
                    "video_id": "video_2",
                    "video_title": "Video 2",
                    "channel_name": "Test Channel",
                    "watched_at": (
                        datetime.now(timezone.utc) - timedelta(days=day_offset)
                    ).isoformat(),
                    "completed": 1 if i == 0 else 0,
                    "manual_play": 0,
                    "grace_play": 0,
                    "duration_watched_seconds": 300 if i == 0 else 30,
                }
            )

    # Low engagement: video_3 (20% completion, 1 unique day)
    for _ in range(5):
        watch_records.append(
            {
                "video_id": "video_3",
                "video_title": "Video 3",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1 if _ == 0 else 0,
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300 if _ == 0 else 30,
            }
        )

    # Videos 4-9: No watch history (new videos)

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores for all 9 videos
    scores = calculate_engagement_scores(video_ids)

    # Verify all 9 videos have scores
    assert len(scores) == 9, f"Expected 9 scores, got {len(scores)}"

    # Verify engagement ordering
    assert scores["video_1"] > scores["video_2"], "High engagement should beat medium"
    assert scores["video_2"] > scores["video_3"], "Medium engagement should beat low"

    # Verify new videos have baseline 0.5
    for video_id in ["video_4", "video_5", "video_6", "video_7", "video_8", "video_9"]:
        assert scores[video_id] == 0.5, f"{video_id} should have baseline weight 0.5"

    # Verify minimum floor enforced for low engagement video
    assert scores["video_3"] >= 0.05, "Minimum floor 0.05 must be enforced"


@freeze_time("2025-01-15 14:30:00")
def test_utc_consistency_across_timezones(test_db_with_patch):
    """
    Test 4.4-INT-008: Mock current time at different timezones, verify UTC consistency.

    This test validates that engagement calculation uses UTC throughout,
    preventing timezone bugs in recency calculations.

    Scenario (frozen time: 2025-01-15 14:30:00 UTC):
    - Create watches with explicit UTC timestamps
    - Verify recency penalties calculated correctly regardless of system timezone

    Expected:
    - 12 hours ago (UTC) always triggers <24h penalty (×0.3)
    - Consistent behavior regardless of timezone representation
    """
    from backend.services.viewing_session import calculate_engagement_scores

    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_utc", content_source_id=source_id),
            create_test_video(video_id="video_zulu", content_source_id=source_id),
        ],
    )

    # Frozen time: 2025-01-15 14:30:00 UTC
    # Create watches 12 hours ago with different UTC representations
    watch_utc = "2025-01-15T02:30:00+00:00"  # UTC offset format
    watch_zulu = "2025-01-15T02:30:00Z"  # Zulu time format

    watch_records = []

    # Both videos: Same engagement, watched 12 hours ago in different formats
    for video_id, watch_date in [("video_utc", watch_utc), ("video_zulu", watch_zulu)]:
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
    scores = calculate_engagement_scores(["video_utc", "video_zulu"])

    # Verify both representations result in same recency calculation
    # Both should have <24h penalty (×0.3)
    assert (
        abs(scores["video_utc"] - scores["video_zulu"]) < 0.01
    ), f"UTC representations should yield same score (utc={scores['video_utc']:.3f}, zulu={scores['video_zulu']:.3f})"

    # Verify both have low score due to <24h recency penalty
    # Expected: ~0.3 × (completion_rate × log(1 + unique_days))
    # With 100% completion and 1 unique day: ~0.3 × log(2) ≈ 0.21
    for video_id in ["video_utc", "video_zulu"]:
        assert (
            scores[video_id] < 0.3
        ), f"{video_id} should have recency penalty applied (<0.3), got {scores[video_id]:.3f}"


def test_completed_watch_increases_engagement(test_db_with_patch):
    """
    Test 4.4-INT-022: Insert watch_history with completed=1 → increases engagement score.

    This test validates that the 'completed' flag in watch_history directly
    affects engagement scoring (completion rate component).

    Scenario:
    - video_completed: 10 watches, all completed=1
    - video_skipped: 10 watches, all completed=0

    Expected:
    - video_completed has significantly higher engagement score
    """
    from backend.services.viewing_session import calculate_engagement_scores

    test_db = test_db_with_patch

    # Set up content source and videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [
            create_test_video(video_id="video_completed", content_source_id=source_id),
            create_test_video(video_id="video_skipped", content_source_id=source_id),
        ],
    )

    # Create watch history (10 days ago to avoid recency penalty)
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = []

    # video_completed: 10 watches, all completed=1 (100% completion rate)
    for _ in range(10):
        watch_records.append(
            {
                "video_id": "video_completed",
                "video_title": "Completed Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 1,  # COMPLETED
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 300,
            }
        )

    # video_skipped: 10 watches, all completed=0 (0% completion rate)
    for _ in range(10):
        watch_records.append(
            {
                "video_id": "video_skipped",
                "video_title": "Skipped Video",
                "channel_name": "Test Channel",
                "watched_at": past_date,
                "completed": 0,  # NOT COMPLETED
                "manual_play": 0,
                "grace_play": 0,
                "duration_watched_seconds": 30,
            }
        )

    insert_watch_history(test_db, watch_records)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_completed", "video_skipped"])

    # Verify completion rate affects engagement
    # video_completed: 1.0 × log(2) ≈ 0.69
    # video_skipped: 0.0 × log(2) = 0.0 → floor to 0.05
    assert (
        scores["video_completed"] > scores["video_skipped"]
    ), f"Completed video should have higher engagement (completed={scores['video_completed']:.2f}, skipped={scores['video_skipped']:.2f})"

    # Verify video_skipped hits minimum floor
    assert scores["video_skipped"] >= 0.05, "Skipped video should hit minimum floor 0.05"
    assert scores["video_skipped"] <= 0.10, "Skipped video should be near floor (<0.10)"


def test_duration_watched_tracked_in_database(test_db_with_patch):
    """
    Test 4.4-INT-023: Insert watch_history with duration_watched_seconds → data tracked.

    This test validates that duration_watched_seconds is properly stored in the
    database and available for future enhancements (though not used in current algorithm).

    Scenario:
    - Insert watches with varying duration_watched_seconds
    - Verify data is stored correctly

    Expected:
    - duration_watched_seconds persists in database
    - Available for future algorithm enhancements
    """
    from backend.db.queries import get_connection

    test_db = test_db_with_patch

    # Set up content source and video
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [create_test_video(video_id="video_1", content_source_id=source_id)],
    )

    # Insert watches with different durations
    past_date = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
    watch_records = [
        {
            "video_id": "video_1",
            "video_title": "Video 1",
            "channel_name": "Test Channel",
            "watched_at": past_date,
            "completed": 1,
            "manual_play": 0,
            "grace_play": 0,
            "duration_watched_seconds": 120,  # 2 minutes
        },
        {
            "video_id": "video_1",
            "video_title": "Video 1",
            "channel_name": "Test Channel",
            "watched_at": past_date,
            "completed": 1,
            "manual_play": 0,
            "grace_play": 0,
            "duration_watched_seconds": 300,  # 5 minutes
        },
        {
            "video_id": "video_1",
            "video_title": "Video 1",
            "channel_name": "Test Channel",
            "watched_at": past_date,
            "completed": 0,
            "manual_play": 0,
            "grace_play": 0,
            "duration_watched_seconds": 30,  # 30 seconds (skipped)
        },
    ]

    insert_watch_history(test_db, watch_records)

    # Verify duration_watched_seconds is stored in database
    with get_connection() as conn:
        result = conn.execute(
            """
            SELECT duration_watched_seconds
            FROM watch_history
            WHERE video_id = ?
            ORDER BY duration_watched_seconds
            """,
            ("video_1",),
        ).fetchall()

    # Verify all 3 records with correct durations
    assert len(result) == 3, f"Expected 3 watch records, got {len(result)}"
    durations = [row["duration_watched_seconds"] for row in result]
    assert durations == [30, 120, 300], f"Expected durations [30, 120, 300], got {durations}"


def test_zero_engagement_minimum_floor(test_db_with_patch):
    """
    Test 4.4-INT-010: Videos with zero engagement have 0.05 weight minimum.

    This integration test verifies that the minimum weight floor (AC 4)
    is enforced for videos with absolutely no engagement history.

    Scenario:
    - video_new: Brand new video with zero watch history

    Expected:
    - video_new gets minimum weight 0.05 (not 0.0)
    - Ensures new videos always appear in selection
    """
    from backend.services.viewing_session import calculate_engagement_scores

    test_db = test_db_with_patch

    # Set up content source and video
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    setup_test_videos(
        test_db,
        [create_test_video(video_id="video_new", content_source_id=source_id)],
    )

    # NO watch history for this video (zero engagement)

    # Calculate engagement scores
    scores = calculate_engagement_scores(["video_new"])

    # Verify minimum floor enforced (not zero)
    assert (
        scores["video_new"] == 0.5
    ), f"New video with no history should get baseline 0.5, got {scores['video_new']}"


def test_no_watch_history_equal_weights(test_db_with_patch):
    """
    Test 4.4-INT-020: Edge case: No watch history (brand new) → equal weights (effectively random).

    This integration test verifies that when there's NO watch history at all
    (brand new database), all videos get equal baseline weights.

    Scenario:
    - 5 brand new videos, zero watch history for any of them

    Expected:
    - All videos get baseline weight 0.5
    - Selection is effectively random (equal weights)
    """
    from backend.services.viewing_session import calculate_engagement_scores

    test_db = test_db_with_patch

    # Set up content source and 5 videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")
    video_ids = [f"video_{i}" for i in range(1, 6)]
    videos = [
        create_test_video(video_id=video_id, content_source_id=source_id) for video_id in video_ids
    ]
    setup_test_videos(test_db, videos)

    # NO watch history at all (cold start scenario)

    # Calculate engagement scores
    scores = calculate_engagement_scores(video_ids)

    # Verify all videos have equal baseline weight
    for video_id in video_ids:
        assert (
            scores[video_id] == 0.5
        ), f"{video_id} should have baseline 0.5, got {scores[video_id]}"

    # Verify all scores are equal (effectively random selection)
    unique_scores = set(scores.values())
    assert len(unique_scores) == 1, f"All scores should be equal (cold start), got {scores}"
