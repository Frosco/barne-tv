"""
Video selection and daily limit tracking for child viewing sessions.

This module handles:
- Selecting random videos for the grid
- Calculating time watched today
- Wind-down mode filtering
- Grace video selection

TIER 1 Rules:
- Rule 1: Always filter banned and unavailable videos
- Rule 2: Time limits must exclude manual_play and grace_play
- Rule 3: All date operations use UTC timezone
"""

import random
from datetime import datetime, timezone, timedelta

from backend.db.queries import (
    get_available_videos,
    get_watch_history_for_date,
    get_setting,
    check_grace_consumed,
    delete_todays_countable_history,
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
        "resetTime": reset_time.isoformat().replace("+00:00", "Z"),
    }


def get_videos_for_grid(
    count: int, max_duration_seconds: int | None = None
) -> tuple[list[dict], dict]:
    """
    Fetch weighted-random videos for the child's grid.

    Uses weighted random selection:
    - 60-80% novelty (videos NOT in recent watch history or watched >7 days ago)
    - 20-40% favorites (videos watched recently within 7 days)

    TIER 1 Rules Applied:
    - Rule 1: Must filter banned and unavailable videos (via get_available_videos)
    - Rule 2: Time limits exclude manual_play and grace_play (via get_daily_limit)
    - Rule 3: All date operations use UTC timezone

    TIER 2 Rule 7: Uses context manager via database query functions.

    Args:
        count: Number of videos to return (typically grid_size setting, usually 9)
        max_duration_seconds: Optional maximum duration for wind-down mode filtering

    Returns:
        Tuple of (videos_list, daily_limit_dict)
        - videos_list: List of video dicts ready for frontend rendering
        - daily_limit_dict: Daily limit state from get_daily_limit()

    Raises:
        NoVideosAvailableError: If no videos are available after filtering

    Example:
        videos, daily_limit = get_videos_for_grid(9)
        if daily_limit['currentState'] == 'winddown':
            # Videos already filtered by max_duration
            pass
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

    # Weighted random selection algorithm
    # Get watch history for the last 7 days
    current_time = datetime.now(timezone.utc)
    recent_video_ids = set()

    for days_ago in range(7):
        date = (current_time.date() - timedelta(days=days_ago)).isoformat()
        history = get_watch_history_for_date(date)
        recent_video_ids.update(h["videoId"] for h in history)

    # Separate novelty vs favorites
    novelty_videos = [v for v in available_videos if v["videoId"] not in recent_video_ids]
    favorite_videos = [v for v in available_videos if v["videoId"] in recent_video_ids]

    # Calculate split (60-80% novelty)
    novelty_ratio = random.uniform(0.6, 0.8)
    novelty_count = int(count * novelty_ratio)
    favorites_count = count - novelty_count

    # Random sample from each pool
    selected = []

    if novelty_videos:
        sample_count = min(novelty_count, len(novelty_videos))
        selected.extend(random.sample(novelty_videos, sample_count))

    if favorite_videos:
        sample_count = min(favorites_count, len(favorite_videos))
        selected.extend(random.sample(favorite_videos, sample_count))

    # If we don't have enough yet, fill with any remaining available videos
    if len(selected) < count:
        remaining_videos = [v for v in available_videos if v not in selected]
        if remaining_videos:
            need_count = count - len(selected)
            sample_count = min(need_count, len(remaining_videos))
            selected.extend(random.sample(remaining_videos, sample_count))

    # Shuffle the final selection so novelty and favorites are mixed
    random.shuffle(selected)

    return selected[:count], daily_limit


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
