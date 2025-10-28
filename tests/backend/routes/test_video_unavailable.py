"""
Backend tests for POST /api/videos/unavailable endpoint.

Tests video unavailability marking, global duplicate instance updates,
and filtering enforcement.
"""

import pytest
from tests.backend.conftest import create_test_video, setup_test_videos, setup_content_source


@pytest.mark.tier1
def test_marking_video_unavailable_updates_all_duplicate_instances(test_db, test_client):
    """
    2.2-INT-012: Verify marking video unavailable updates ALL duplicate instances globally.

    TIER 1: Safety-critical - global availability flag ensures unavailable videos
    never appear in grid, regardless of which content source they came from.
    """
    # Arrange: Create test content sources
    source1_id = setup_content_source(
        test_db, source_id="UCsource1", source_type="channel", name="Channel 1"
    )
    source2_id = setup_content_source(
        test_db, source_id="UCsource2", source_type="channel", name="Channel 2"
    )

    # Create DUPLICATE video entries (same video_id, different content_source_id)
    duplicate_videos = [
        create_test_video(
            video_id="NsKaCS3CtsY",  # Valid 11-char YouTube video ID
            title="Duplicate Video from Source 1",
            content_source_id=source1_id,
            duration_seconds=300,
            is_available=1,  # Initially available
        ),
        create_test_video(
            video_id="NsKaCS3CtsY",  # SAME video_id
            title="Duplicate Video from Source 2",
            content_source_id=source2_id,
            duration_seconds=300,
            is_available=1,  # Initially available
        ),
    ]
    setup_test_videos(test_db, duplicate_videos)

    # Act: Call POST /api/videos/unavailable
    response = test_client.post("/api/videos/unavailable", json={"videoId": "NsKaCS3CtsY"})

    # Assert
    # 1. Response status code = 200
    assert response.status_code == 200

    # 2. Response body: {"success": True}
    data = response.json()
    assert data["success"] is True

    # 3. Query videos table: Both instances marked unavailable
    unavailable_count = test_db.execute(
        "SELECT COUNT(*) as count FROM videos WHERE video_id = ? AND is_available = 0",
        ("NsKaCS3CtsY",),
    ).fetchone()["count"]

    # 4. Count should be 2 (BOTH instances marked unavailable)
    assert unavailable_count == 2

    # 5. Query: No instances still available
    available_count = test_db.execute(
        "SELECT COUNT(*) as count FROM videos WHERE video_id = ? AND is_available = 1",
        ("NsKaCS3CtsY",),
    ).fetchone()["count"]

    # 6. Count should be 0 (NO instances still available)
    assert available_count == 0


@pytest.mark.tier1
def test_unavailable_videos_do_not_appear_in_subsequent_grid_requests(test_db, test_client):
    """
    2.2-INT-013: Verify unavailable videos do not appear in subsequent grid requests.

    TIER 1: Safety-critical - filter enforcement prevents child from seeing
    unavailable videos repeatedly.
    """
    # Arrange: Create content source and videos
    source_id = setup_content_source(test_db)

    videos = [
        create_test_video(
            video_id="available_video_001",
            title="Available Video",
            content_source_id=source_id,
            duration_seconds=300,
            is_available=1,
        ),
        create_test_video(
            video_id="unavailable_video_002",
            title="Unavailable Video",
            content_source_id=source_id,
            duration_seconds=300,
            is_available=0,  # Already marked unavailable
        ),
    ]
    setup_test_videos(test_db, videos)

    # Act: Call GET /api/videos?count=10
    response = test_client.get("/api/videos?count=10")

    # Assert
    assert response.status_code == 200
    data = response.json()

    # Extract video IDs from response
    video_ids = [video["videoId"] for video in data["videos"]]

    # 1. Response contains video "available_video_001"
    assert "available_video_001" in video_ids

    # 2. Response does NOT contain video "unavailable_video_002"
    assert "unavailable_video_002" not in video_ids

    # 3. Verify all returned videos are available
    for video in data["videos"]:
        db_video = test_db.execute(
            "SELECT is_available FROM videos WHERE video_id = ?", (video["videoId"],)
        ).fetchone()
        assert db_video["is_available"] == 1


def test_unavailable_endpoint_with_invalid_video_id_returns_400(test_db, test_client):
    """
    2.2-INT-014: Verify unavailable endpoint with invalid videoId returns validation error.

    Input validation - malformed video IDs should be rejected.
    """
    # Arrange: No video setup needed for validation test

    # Test case 1: videoId is empty string (endpoint validates length)
    response = test_client.post("/api/videos/unavailable", json={"videoId": ""})
    assert response.status_code == 400
    assert "error" in response.json()

    # Test case 2: videoId is missing (FastAPI returns 422 for missing required fields)
    response = test_client.post("/api/videos/unavailable", json={})
    assert response.status_code == 422
    assert "detail" in response.json()

    # Test case 3: videoId is not a string (integer)
    response = test_client.post("/api/videos/unavailable", json={"videoId": 123})
    # Pydantic may coerce or reject - either 422 (type error) or 400 (length validation) is acceptable
    assert response.status_code in [400, 422]


def test_idempotency_calling_unavailable_twice_on_same_video_is_safe(test_db, test_client):
    """
    2.2-INT-015: Verify idempotency - calling unavailable endpoint twice on same video is safe.

    API reliability - multiple calls should not cause errors or side effects.
    """
    # Arrange: Create content source and video
    source_id = setup_content_source(test_db)
    video = create_test_video(
        video_id="L_jWHffIx5E",  # Valid 11-char YouTube video ID
        title="Idempotent Test Video",
        content_source_id=source_id,
        duration_seconds=300,
        is_available=1,
    )
    setup_test_videos(test_db, [video])

    # Act: Call POST /api/videos/unavailable TWICE
    # First call
    response1 = test_client.post("/api/videos/unavailable", json={"videoId": "L_jWHffIx5E"})

    # Second call (same video)
    response2 = test_client.post("/api/videos/unavailable", json={"videoId": "L_jWHffIx5E"})

    # Assert
    # 1. Both calls return status code 200
    assert response1.status_code == 200
    assert response2.status_code == 200

    # 2. Both calls return {"success": True}
    assert response1.json()["success"] is True
    assert response2.json()["success"] is True

    # 3. Video is marked unavailable after first call
    video_after_first = test_db.execute(
        "SELECT is_available FROM videos WHERE video_id = ?", ("L_jWHffIx5E",)
    ).fetchone()
    assert video_after_first["is_available"] == 0

    # 4. Video remains unavailable after second call (no error)
    video_after_second = test_db.execute(
        "SELECT is_available FROM videos WHERE video_id = ?", ("L_jWHffIx5E",)
    ).fetchone()
    assert video_after_second["is_available"] == 0

    # 5. No duplicate entries or database errors (only one video row exists)
    video_count = test_db.execute(
        "SELECT COUNT(*) as count FROM videos WHERE video_id = ?", ("L_jWHffIx5E",)
    ).fetchone()["count"]
    assert video_count == 1
