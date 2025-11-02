"""
Integration tests for wind-down video filtering (Story 4.2).

Tests GET /api/videos?max_duration parameter for wind-down mode.
"""

import pytest
from tests.backend.conftest import (
    setup_content_source,
    setup_test_videos,
    create_test_video,
    ban_video,
)


@pytest.mark.integration
def test_videos_endpoint_with_max_duration(test_client, test_db, monkeypatch):
    """
    Test GET /api/videos with max_duration parameter filters correctly.

    Wind-down mode should only return videos shorter than max_duration.
    """
    # Arrange: Create content source and videos of various durations
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    videos = [
        create_test_video(
            video_id="short_1",
            title="Short Video 1",
            content_source_id=source_id,
            duration_seconds=120,  # 2 minutes
        ),
        create_test_video(
            video_id="short_2",
            title="Short Video 2",
            content_source_id=source_id,
            duration_seconds=180,  # 3 minutes
        ),
        create_test_video(
            video_id="medium_1",
            title="Medium Video 1",
            content_source_id=source_id,
            duration_seconds=300,  # 5 minutes (exactly at limit)
        ),
        create_test_video(
            video_id="long_1",
            title="Long Video 1",
            content_source_id=source_id,
            duration_seconds=420,  # 7 minutes
        ),
        create_test_video(
            video_id="long_2",
            title="Long Video 2",
            content_source_id=source_id,
            duration_seconds=600,  # 10 minutes
        ),
    ]
    setup_test_videos(test_db, videos)

    # Mock viewing_session.get_videos_for_grid to use test database
    from backend.services import viewing_session
    from backend.db.queries import get_available_videos
    import random

    def mock_get_videos_for_grid(count, max_duration=None):
        videos = get_available_videos(max_duration_seconds=max_duration, conn=test_db)
        # Shuffle and limit to count
        random.shuffle(videos)
        selected = videos[:count]

        # Return mock daily limit
        daily_limit = {
            "date": "2025-01-03",
            "minutesWatched": 25,
            "minutesRemaining": 5,
            "currentState": "winddown",
            "resetTime": "2025-01-04T00:00:00Z",
        }
        return selected, daily_limit

    monkeypatch.setattr(viewing_session, "get_videos_for_grid", mock_get_videos_for_grid)

    # Act: Request videos with max_duration=300 (5 minutes)
    response = test_client.get("/api/videos?count=9&max_duration=300")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "videos" in data

    # All returned videos should be ≤ 300 seconds
    for video in data["videos"]:
        assert video["durationSeconds"] <= 300, f"Video {video['videoId']} exceeds max_duration"

    # Should include short videos and 5-minute video
    video_ids = [v["videoId"] for v in data["videos"]]
    assert len(video_ids) <= 3  # Only 3 videos fit (short_1, short_2, medium_1)


@pytest.mark.integration
def test_winddown_no_fitting_videos_fallback(test_client, test_db, monkeypatch):
    """
    Test AC 13: If no videos fit remaining time, show all videos.

    Better than empty grid.
    """
    # Arrange: Create only long videos
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    videos = [
        create_test_video(
            video_id="long_1",
            title="Long Video 1",
            content_source_id=source_id,
            duration_seconds=600,  # 10 minutes
        ),
        create_test_video(
            video_id="long_2",
            title="Long Video 2",
            content_source_id=source_id,
            duration_seconds=720,  # 12 minutes
        ),
    ]
    setup_test_videos(test_db, videos)

    # Mock viewing_session to handle fallback
    from backend.services import viewing_session
    from backend.db.queries import get_available_videos
    import random

    def mock_get_videos_for_grid(count, max_duration=None):
        filtered_videos = get_available_videos(max_duration_seconds=max_duration, conn=test_db)

        # AC 13: If no videos fit, fall back to all videos
        if not filtered_videos and max_duration is not None:
            filtered_videos = get_available_videos(max_duration_seconds=None, conn=test_db)

        random.shuffle(filtered_videos)
        selected = filtered_videos[:count]

        daily_limit = {
            "date": "2025-01-03",
            "minutesWatched": 28,
            "minutesRemaining": 2,
            "currentState": "winddown",
            "resetTime": "2025-01-04T00:00:00Z",
        }
        return selected, daily_limit

    monkeypatch.setattr(viewing_session, "get_videos_for_grid", mock_get_videos_for_grid)

    # Act: Request with max_duration=120 (2 minutes) - no videos fit
    response = test_client.get("/api/videos?count=9&max_duration=120")

    # Assert: Should fall back to all videos
    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 2  # Both long videos returned as fallback


@pytest.mark.integration
def test_winddown_maintains_banned_filter(test_client, test_db, monkeypatch):
    """
    Test that wind-down filtering maintains banned video exclusion.

    TIER 1 Rule 1: ALWAYS filter banned videos.
    """
    # Arrange
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    videos = [
        create_test_video(
            video_id="short_safe",
            title="Short Safe Video",
            content_source_id=source_id,
            duration_seconds=180,  # 3 minutes
        ),
        create_test_video(
            video_id="short_banned",
            title="Short Banned Video",
            content_source_id=source_id,
            duration_seconds=240,  # 4 minutes
        ),
    ]
    setup_test_videos(test_db, videos)

    # Ban the second video
    ban_video(test_db, "short_banned")

    # Mock viewing_session
    from backend.services import viewing_session
    from backend.db.queries import get_available_videos
    import random

    def mock_get_videos_for_grid(count, max_duration=None):
        # TIER 1: Always exclude banned
        videos = get_available_videos(
            exclude_banned=True, max_duration_seconds=max_duration, conn=test_db
        )
        random.shuffle(videos)
        selected = videos[:count]

        daily_limit = {
            "date": "2025-01-03",
            "minutesWatched": 25,
            "minutesRemaining": 5,
            "currentState": "winddown",
            "resetTime": "2025-01-04T00:00:00Z",
        }
        return selected, daily_limit

    monkeypatch.setattr(viewing_session, "get_videos_for_grid", mock_get_videos_for_grid)

    # Act: Request with max_duration=300 (5 minutes)
    response = test_client.get("/api/videos?count=9&max_duration=300")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Only safe short video should be returned
    assert len(data["videos"]) == 1
    assert data["videos"][0]["videoId"] == "short_safe"

    # Banned video should NOT be present
    video_ids = [v["videoId"] for v in data["videos"]]
    assert "short_banned" not in video_ids


@pytest.mark.integration
def test_videos_endpoint_validates_max_duration(test_client):
    """
    Test that max_duration parameter is validated.

    Should reject negative or zero durations.
    """
    # Act: Try with negative max_duration
    response = test_client.get("/api/videos?count=9&max_duration=-300")

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "positiv" in data["message"]


@pytest.mark.integration
def test_videos_endpoint_without_max_duration_still_works(test_client, test_db, monkeypatch):
    """
    Test that GET /api/videos still works without max_duration (backward compatibility).
    """
    # Arrange
    source_id = setup_content_source(test_db, "UCtest", "channel", "Test Channel")

    videos = [
        create_test_video(
            video_id=f"video_{i}",
            title=f"Video {i}",
            content_source_id=source_id,
            duration_seconds=300,
        )
        for i in range(10)
    ]
    setup_test_videos(test_db, videos)

    # Mock viewing_session
    from backend.services import viewing_session
    from backend.db.queries import get_available_videos
    import random

    def mock_get_videos_for_grid(count, max_duration=None):
        videos = get_available_videos(max_duration_seconds=max_duration, conn=test_db)
        random.shuffle(videos)
        selected = videos[:count]

        daily_limit = {
            "date": "2025-01-03",
            "minutesWatched": 15,
            "minutesRemaining": 15,
            "currentState": "normal",
            "resetTime": "2025-01-04T00:00:00Z",
        }
        return selected, daily_limit

    monkeypatch.setattr(viewing_session, "get_videos_for_grid", mock_get_videos_for_grid)

    # Act: Request without max_duration parameter
    response = test_client.get("/api/videos?count=9")

    # Assert: Should work normally
    assert response.status_code == 200
    data = response.json()
    assert "videos" in data
    assert "dailyLimit" in data
    assert len(data["videos"]) <= 9
