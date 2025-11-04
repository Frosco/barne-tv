"""
Video selection and daily limit tracking for child viewing sessions.

This module handles:
- Engagement-based weighted video selection
- Calculating time watched today
- Wind-down mode filtering
- Grace video selection

Engagement-Based Selection Algorithm (Story 4.4):
    Videos are selected using a sophisticated engagement scoring system that balances
    personalization with variety. Each video receives an engagement weight based on:

    1. Completion Rate: (completed watches / total watches)
       - Videos the child watches to completion score higher
       - Excludes manual_play and grace_play (TIER 1 Rule 2)

    2. Replay Frequency: log(1 + unique_days_watched)
       - Logarithmic scaling prevents domination by heavily replayed videos
       - Encourages discovering new favorites

    3. Recency Penalty (Variety Enforcement):
       - Last 24 hours: Weight × 0.3 (70% reduction - strong penalty)
       - 24h-7 days: Weight × 0.7 (30% reduction - medium penalty)
       - >7 days: Weight × 1.0 (no penalty)

    4. Minimum Weight Floor: max(calculated_weight, 0.05)
       - All videos always have small chance of selection (AC 4)
       - Prevents "hidden" videos

    5. Channel Variety Constraint: Max 3 videos per channel in 9-video grid
       - Hard constraint: Videos from channels with 3+ selections get weight=0
       - Guarantees variety across channels

    Formula:
        base_engagement = completion_rate × log(1 + replay_days)
        weight = max(base_engagement × recency_multiplier, 0.05)

    Edge Cases:
        - No watch history: All videos get baseline weight 0.5 → random selection
        - All videos watched in last 24h: Fallback to equal weights → random selection
        - New videos: Baseline weight 0.5 ensures visibility
        - Grace mode: Bypasses engagement logic (uses simple 5-min duration filter)

TIER 1 Rules:
- Rule 1: Always filter banned and unavailable videos
- Rule 2: Time limits must exclude manual_play and grace_play
- Rule 3: All date operations use UTC timezone
"""

import math
import random
from datetime import datetime, timezone, timedelta

from backend.db.queries import (
    check_grace_consumed,
    delete_todays_countable_history,
    get_available_videos,
    get_setting,
    get_watch_history_for_date,
)
from backend.exceptions import NoVideosAvailableError


def get_daily_limit(conn=None) -> dict:
    """
    Get current daily limit state including minutes watched and current state.

    TIER 1 Rules Applied:
    - Rule 2: Excludes manual_play and grace_play from time calculations
    - Rule 3: Uses UTC for all date/time operations

    Args:
        conn: Optional database connection (for testing). If None, creates new connection.

    Returns:
        Dict with daily limit information:
        {
            "date": "2025-01-03",
            "minutesWatched": 15,
            "minutesRemaining": 15,
            "currentState": "normal|winddown|grace|locked",
            "graceAvailable": True,  # Only True when currentState == "grace"
            "resetTime": "2025-01-04T00:00:00Z"
        }

    State transitions:
    - normal: More than 10 minutes remaining
    - winddown: 10 minutes or less remaining (filter videos by duration)
    - grace: Limit reached (0 min remaining), one more video allowed (≤5 min)
    - locked: Grace video consumed or declined, locked until midnight UTC

    Example:
        limit = get_daily_limit()
        if limit['currentState'] == 'winddown':
            max_duration = limit['minutesRemaining'] * 60
            videos = get_videos_for_grid(9, max_duration_seconds=max_duration)
    """
    # TIER 1 Rule 3: Always use UTC for date operations
    current_time = datetime.now(timezone.utc)
    today = current_time.date().isoformat()

    # Fetch watch history for today (excludes manual_play and grace_play per TIER 1 Rule 2)
    history = get_watch_history_for_date(today, conn=conn)

    # Calculate minutes watched today
    total_seconds = sum(h["durationWatchedSeconds"] for h in history)
    minutes_watched = int(total_seconds / 60)

    # Fetch daily limit setting (stored as JSON string, defaults to 30)
    daily_limit_json = get_setting("daily_limit_minutes", conn=conn)
    daily_limit_minutes = int(daily_limit_json)  # Already a plain int string

    # Calculate minutes remaining
    minutes_remaining = max(0, daily_limit_minutes - minutes_watched)

    # Determine current state
    if minutes_remaining > 10:
        current_state = "normal"
    elif minutes_remaining > 0:
        current_state = "winddown"
    else:
        # TIER 1 Rule: Check if grace video has been consumed
        # If grace video already watched today, system is locked until midnight
        grace_consumed = check_grace_consumed(today, conn=conn)
        if grace_consumed:
            current_state = "locked"
        else:
            current_state = "grace"

    # Calculate reset time (midnight UTC tonight/tomorrow)
    tomorrow = current_time.date() + timedelta(days=1)
    reset_time = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)

    return {
        "date": today,
        "minutesWatched": minutes_watched,
        "minutesRemaining": minutes_remaining,
        "currentState": current_state,
        "graceAvailable": current_state == "grace",
        "resetTime": reset_time.isoformat().replace("+00:00", "Z"),
    }


def should_interrupt_video(minutes_remaining: int, video_duration_minutes: int) -> bool:
    """
    Determine if a video should be interrupted when daily limit is about to be reached.

    Grace Period Logic (Story 4.3 AC 14):
    - If video will finish within 5 minutes AFTER limit reached, let it play
    - Otherwise, interrupt immediately and show grace screen

    Args:
        minutes_remaining: Minutes remaining in daily limit (can be negative)
        video_duration_minutes: Total duration of video in minutes (rounded up)

    Returns:
        True if video should be interrupted, False if it should be allowed to finish

    Examples:
        # Video is 3 minutes, 8 minutes remaining → let it finish
        should_interrupt_video(8, 3)  # False

        # Video is 12 minutes, 8 minutes remaining → would extend 4 min past limit → let it finish
        should_interrupt_video(8, 12)  # False (12 <= 8 + 5)

        # Video is 15 minutes, 8 minutes remaining → would extend 7 min past limit → interrupt
        should_interrupt_video(8, 15)  # True (15 > 8 + 5)

        # Video is 6 minutes, 0 minutes remaining → within grace period → let it finish
        should_interrupt_video(0, 6)  # False (6 <= 0 + 5)
    """
    # TIER 1 Rule 6: Validate inputs to prevent crashes with malformed data
    if video_duration_minutes <= 0:
        raise ValueError(f"video_duration_minutes must be positive, got {video_duration_minutes}")

    # Defensive: Treat negative remaining time as zero (already past limit)
    # This handles edge cases where calculation timing causes negative values
    safe_minutes_remaining = max(0, minutes_remaining)

    # Allow video to finish if it will complete within 5 minutes after limit
    # This prevents abrupt interruptions for videos close to finishing
    return video_duration_minutes > (safe_minutes_remaining + 5)


def calculate_engagement_scores(video_ids: list[str]) -> dict[str, float]:
    """
    Calculate engagement weight for each video based on watch history.

    Uses sophisticated time-weighted algorithm:
        1. Completion rate: completed_watches / total_watches
        2. Replay frequency: log(1 + unique_days_watched)
        3. Recency penalty: 24h=×0.3, 7d=×0.7, >7d=×1.0
        4. Minimum floor: max(calculated_weight, 0.05)

    TIER 1 Rules Applied:
    - Rule 2: Excludes manual_play and grace_play from engagement calculation
    - Rule 3: Uses UTC for all time calculations
    - Rule 6: Uses SQL placeholders (never string formatting)

    TIER 2 Rule 7: Uses context manager for database access.

    Args:
        video_ids: List of YouTube video IDs to calculate scores for

    Returns:
        Dict mapping video_id → engagement_weight (0.05 to 1.0 range)
        - 0.05 = minimum floor (never completely hidden, AC 4)
        - 0.5 = baseline for new videos with no history
        - 1.0 = maximum engagement (high completion + replays + not recent)

    Edge Cases:
        - No watch history for video: Returns baseline weight 0.5
        - Video watched recently (24h): Strong recency penalty (×0.3)
        - All manual_play/grace_play watches: Treated as no history (weight 0.5)

    Example:
        video_ids = ['abc123', 'def456', 'ghi789']
        scores = calculate_engagement_scores(video_ids)
        # Returns: {'abc123': 0.85, 'def456': 0.12, 'ghi789': 0.5}
    """
    if not video_ids:
        return {}

    # TIER 1 Rule 3: Always use UTC for time calculations
    current_time = datetime.now(timezone.utc)

    scores = {}

    # TIER 2 Rule 7: Use context manager for database access
    from backend.db.queries import get_connection

    with get_connection() as conn:
        for video_id in video_ids:
            # TIER 1 Rule 2: Exclude manual_play and grace_play from engagement calculation
            # TIER 1 Rule 6: Always use SQL placeholders
            query = """
                SELECT
                    COUNT(*) as total_watches,
                    SUM(CASE WHEN completed = 1 THEN 1 ELSE 0 END) as completed_watches,
                    COUNT(DISTINCT DATE(watched_at)) as unique_days,
                    MAX(watched_at) as most_recent_watch
                FROM watch_history
                WHERE video_id = ?
                AND manual_play = 0
                AND grace_play = 0
            """

            result = conn.execute(query, (video_id,)).fetchone()

            total_watches = result["total_watches"]
            completed_watches = result["completed_watches"]
            unique_days = result["unique_days"]
            most_recent_watch = result["most_recent_watch"]

            # Edge case: No watch history (new video or all watches were manual/grace)
            if total_watches == 0:
                scores[video_id] = 0.5  # Baseline weight for new videos
                continue

            # Calculate base engagement score

            # 1. Completion rate (0.0 to 1.0)
            completion_rate = completed_watches / total_watches

            # 2. Replay frequency weight (logarithmic scaling)
            # log(1 + unique_days) ensures:
            #   - 1 day: log(2) ≈ 0.69
            #   - 3 days: log(4) ≈ 1.39
            #   - 7 days: log(8) ≈ 2.08
            replay_weight = math.log(1 + unique_days)

            # Base engagement (before recency penalty)
            base_engagement = completion_rate * replay_weight

            # 3. Apply recency penalty (encourage variety)
            if most_recent_watch:
                # Parse ISO 8601 timestamp
                most_recent = datetime.fromisoformat(most_recent_watch.replace("Z", "+00:00"))
                hours_since = (current_time - most_recent).total_seconds() / 3600

                if hours_since < 24:
                    # Last 24 hours: Strong penalty (70% reduction)
                    recency_multiplier = 0.3
                elif hours_since < 168:  # 7 days = 168 hours
                    # 24h-7d: Medium penalty (30% reduction)
                    recency_multiplier = 0.7
                else:
                    # >7 days: No penalty
                    recency_multiplier = 1.0
            else:
                # No recency data (shouldn't happen if total_watches > 0, but defensive)
                recency_multiplier = 1.0

            # Calculate final weight
            weight = base_engagement * recency_multiplier

            # 4. Apply minimum weight floor (AC 4: never completely hide videos)
            weight = max(weight, 0.05)

            scores[video_id] = weight

    return scores


def get_videos_for_grid(
    count: int, max_duration_seconds: int | None = None
) -> tuple[list[dict], dict]:
    """
    Fetch engagement-based weighted random videos for the child's grid.

    Uses engagement-based weighted selection (Story 4.4):
    - Videos weighted by engagement score (completion rate × replay frequency)
    - Recency penalty encourages variety (24h: ×0.3, 7d: ×0.7, >7d: ×1.0)
    - Channel variety constraint: Max 3 videos per channel in 9-video grid
    - Minimum weight floor (0.05) ensures all videos always selectable
    - Grace mode (max_duration=300) bypasses engagement logic (simple random)

    TIER 1 Rules Applied:
    - Rule 1: Must filter banned and unavailable videos (via get_available_videos)
    - Rule 2: Time limits exclude manual_play and grace_play (via get_daily_limit)
    - Rule 3: All date operations use UTC timezone

    TIER 2 Rule 7: Uses context manager via database query functions.

    Args:
        count: Number of videos to return (typically grid_size setting, usually 9)
        max_duration_seconds: Optional maximum duration for wind-down/grace mode filtering
            - For wind-down mode: Duration based on minutes remaining (e.g., 600 for 10 min)
            - For grace mode: 300 seconds (5 minutes) - bypasses engagement logic

    Returns:
        Tuple of (videos_list, daily_limit_dict)
        - videos_list: List of video dicts ready for frontend rendering
        - daily_limit_dict: Daily limit state from get_daily_limit()

    Raises:
        NoVideosAvailableError: If no videos are available after filtering

    Edge Cases:
        - No watch history: All videos get baseline weight 0.5 → feels random
        - All videos watched in last 24h: Falls back to random selection
        - Grace mode (max_duration=300): Bypasses engagement logic entirely
        - Channel has <3 videos: Constraint naturally doesn't apply

    Example:
        # Normal mode: Engagement-based weighted selection
        videos, daily_limit = get_videos_for_grid(9)

        # Wind-down mode: Duration filter + engagement weights
        max_dur = daily_limit['minutesRemaining'] * 60
        videos, daily_limit = get_videos_for_grid(9, max_duration_seconds=max_dur)

        # Grace mode: Simple random selection (no engagement)
        videos, daily_limit = get_videos_for_grid(6, max_duration_seconds=300)
    """
    # Get daily limit state first
    daily_limit = get_daily_limit()

    # TIER 1 Rule 1: Get available videos (excludes banned and unavailable)
    available_videos = get_available_videos(
        exclude_banned=True, max_duration_seconds=max_duration_seconds
    )

    if not available_videos:
        # TIER 3 Rule 14: Norwegian error message for users
        raise NoVideosAvailableError("Ingen videoer tilgjengelig. Be foreldrene legge til kanaler.")

    # If we don't have enough videos, return what we have
    if len(available_videos) <= count:
        return available_videos, daily_limit

    # Edge case: Grace mode bypasses engagement logic (Story 4.3 compatibility)
    # Grace videos use simple duration filter (max 5 min) without engagement scoring
    if max_duration_seconds == 300:  # 5 minutes = grace mode
        selected = random.sample(available_videos, min(count, len(available_videos)))
        return selected, daily_limit

    # Engagement-based weighted selection algorithm (Story 4.4)

    # Step 1: Calculate engagement scores for all available videos
    video_ids = [v["videoId"] for v in available_videos]
    engagement_scores = calculate_engagement_scores(video_ids)

    # Step 2: Edge case - All videos recently watched (AC 9)
    # If all engagement scores are very low (< 0.15), fall back to random selection
    # This happens when all videos were watched in last 24h (recency penalty makes all weights low)
    if engagement_scores and all(score < 0.15 for score in engagement_scores.values()):
        # Fallback to random selection to ensure child gets videos
        selected = random.sample(available_videos, min(count, len(available_videos)))
        return selected, daily_limit

    # Step 3: Weighted selection with channel variety constraint
    # Hard constraint: Max 3 videos per channel in result set (AC 8)
    selected = []
    channel_counts: dict[str, int] = {}  # Track how many videos selected per channel
    candidates = available_videos.copy()  # Make a copy to avoid mutating input

    while len(selected) < count and candidates:
        # Build weights list for remaining candidates, applying channel constraint
        weights = []
        for video in candidates:
            video_id = video["videoId"]
            channel = video["youtubeChannelName"]
            base_weight = engagement_scores.get(video_id, 0.5)  # Default 0.5 if missing

            # Channel variety constraint: Set weight to 0 if channel already has 3 videos
            if channel_counts.get(channel, 0) >= 3:
                weights.append(0.0)
            else:
                weights.append(base_weight)

        # If all weights are 0 (edge case: channel constraint exhausted all candidates)
        # This shouldn't happen with proper channel diversity, but defensive coding
        if sum(weights) == 0:
            break

        # Weighted random selection (AC 7: feels random despite weighting)
        # random.choices() uses weights to make high-engagement videos more likely
        chosen = random.choices(candidates, weights=weights, k=1)[0]

        # Add to results
        selected.append(chosen)

        # Update channel count
        channel = chosen["youtubeChannelName"]
        channel_counts[channel] = channel_counts.get(channel, 0) + 1

        # Remove chosen video from candidates to avoid duplicates
        candidates.remove(chosen)

    return selected, daily_limit


def reset_daily_limit(conn=None) -> dict:
    """
    Reset today's daily limit by deleting countable watch history entries.

    TIER 1 Rules Applied:
    - Rule 2: Only delete entries where manual_play=0 AND grace_play=0 (preserves parent history)
    - Rule 3: Always use UTC for date operations

    TIER 2 Rule 7: Uses context manager via database query functions.

    Args:
        conn: Optional database connection (for testing). If None, creates new connection.

    Returns:
        Dict with updated daily limit state from get_daily_limit()
        {
            "date": "2025-01-03",
            "minutesWatched": 0,
            "minutesRemaining": 30,
            "currentState": "normal",
            "resetTime": "2025-01-04T00:00:00Z"
        }

    Example:
        # Parent clicks "Reset Daily Limit" in admin interface
        new_limit = reset_daily_limit()
        print(f"Limit reset. Minutes remaining: {new_limit['minutesRemaining']}")
    """
    # TIER 1 Rule 3: Always use UTC for date operations
    today = datetime.now(timezone.utc).date().isoformat()

    # Delete countable watch history entries for today
    # TIER 1 Rule 2: Only deletes manual_play=0 AND grace_play=0 (preserves parent/grace history)
    delete_todays_countable_history(today, conn=conn)

    # Get updated daily limit state
    return get_daily_limit(conn=conn)
