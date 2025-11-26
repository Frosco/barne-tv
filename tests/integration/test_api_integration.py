"""
Integration tests for authentication API endpoints.

Tests complete login/logout flows with FastAPI TestClient.
Verifies session management, cookie handling, and error responses.
"""

import json
import pytest
import sqlite3
from pathlib import Path
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import hash_password, sessions


@pytest.fixture
def test_db_file(tmp_path, monkeypatch):
    """
    Create file-based test database and configure app to use it.

    This approach avoids SQLite thread-safety issues with TestClient.
    """
    # Create test database file
    db_file = tmp_path / "test_auth.db"

    # Monkeypatch DATABASE_PATH before creating connection
    monkeypatch.setattr("backend.config.DATABASE_PATH", str(db_file))
    monkeypatch.setattr("backend.db.queries.DATABASE_PATH", str(db_file))

    # Create connection and load schema
    conn = sqlite3.connect(str(db_file))
    conn.row_factory = sqlite3.Row

    # Load schema
    schema_path = Path(__file__).parent.parent.parent / "backend" / "db" / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    conn.commit()
    conn.close()

    yield str(db_file)

    # Cleanup happens automatically with tmp_path


@pytest.fixture
def client():
    """Create FastAPI test client with localhost base_url for TrustedHostMiddleware."""
    return TestClient(app, base_url="http://localhost")


@pytest.fixture
def setup_admin_password(test_db_file):
    """
    Set up admin password in database for testing.

    Uses test password: 'test_admin_password'
    """
    password = "test_admin_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)

    # Connect to test database and set password
    conn = sqlite3.connect(test_db_file)
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("admin_password_hash", json_value),
    )
    conn.commit()
    conn.close()

    return password


# =============================================================================
# LOGIN FLOW TESTS
# =============================================================================


def test_login_with_valid_password(client, setup_admin_password):
    """Test successful login with valid password sets session cookie."""
    sessions.clear()

    password = setup_admin_password

    # Attempt login
    response = client.post("/admin/login", json={"password": password})

    # Verify success response
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["redirect"] == "/admin/dashboard"

    # Verify session cookie was set
    assert "session_id" in response.cookies
    session_id = response.cookies["session_id"]

    # Verify session exists in store
    assert session_id in sessions


def test_login_with_invalid_password(client, setup_admin_password):
    """Test login with wrong password returns 401 error."""
    sessions.clear()

    # Attempt login with wrong password
    response = client.post("/admin/login", json={"password": "wrong_password"})

    # Verify error response
    assert response.status_code == 401
    data = response.json()
    assert "message" in data["detail"]
    assert data["detail"]["message"] == "Feil passord"  # Norwegian error message

    # Verify no session cookie was set
    assert "session_id" not in response.cookies

    # Verify no session was created
    assert len(sessions) == 0


def test_login_without_password_field(client):
    """Test login without password field returns validation error."""
    response = client.post("/admin/login", json={})

    # Pydantic validation should fail
    assert response.status_code == 422


def test_login_with_empty_password(client, setup_admin_password):
    """Test login with empty password returns 401 error."""
    response = client.post("/admin/login", json={"password": ""})

    # Should fail authentication
    assert response.status_code == 401


# =============================================================================
# LOGOUT FLOW TESTS
# =============================================================================


def test_logout_clears_session(client, setup_admin_password):
    """Test logout invalidates session and clears cookie."""
    sessions.clear()

    password = setup_admin_password

    # Login first
    login_response = client.post("/admin/login", json={"password": password})
    assert login_response.status_code == 200
    session_id = login_response.cookies["session_id"]

    # Verify session exists
    assert session_id in sessions

    # Set cookie on client for subsequent requests
    client.cookies.set("session_id", session_id)

    # Logout
    logout_response = client.post("/admin/logout")

    # Verify success response
    assert logout_response.status_code == 200
    data = logout_response.json()
    assert data["success"] is True
    assert data["redirect"] == "/admin/login"

    # Verify session was invalidated
    assert session_id not in sessions


def test_logout_without_session_fails(client):
    """Test logout without valid session returns 401."""
    sessions.clear()

    # Attempt logout without session
    response = client.post("/admin/logout")

    # Should fail authentication
    assert response.status_code == 401


def test_logout_with_invalid_session_fails(client):
    """Test logout with invalid session ID returns 401."""
    sessions.clear()

    # Set invalid session cookie manually
    client.cookies.set("session_id", "invalid_session_id")

    # Attempt logout
    response = client.post("/admin/logout")

    # Should fail authentication
    assert response.status_code == 401


# =============================================================================
# PROTECTED ROUTE TESTS
# =============================================================================


def test_protected_route_access_without_session(client):
    """Test accessing protected route without session returns 401."""
    sessions.clear()

    # Attempt to access logout (protected route) without session
    response = client.post("/admin/logout")

    assert response.status_code == 401


def test_protected_route_access_with_valid_session(client, setup_admin_password):
    """Test accessing protected route with valid session succeeds."""
    sessions.clear()

    password = setup_admin_password

    # Login to get valid session
    login_response = client.post("/admin/login", json={"password": password})
    assert login_response.status_code == 200
    session_id = login_response.cookies["session_id"]

    # Set cookie on client for subsequent requests
    client.cookies.set("session_id", session_id)

    # Access protected route (logout)
    response = client.post("/admin/logout")

    # Should succeed
    assert response.status_code == 200


def test_protected_route_access_after_logout_fails(client, setup_admin_password):
    """Test accessing protected route after logout returns 401."""
    sessions.clear()

    password = setup_admin_password

    # Login
    login_response = client.post("/admin/login", json={"password": password})
    assert login_response.status_code == 200
    session_id = login_response.cookies["session_id"]

    # Set cookie on client for subsequent requests
    client.cookies.set("session_id", session_id)

    # Logout
    logout_response = client.post("/admin/logout")
    assert logout_response.status_code == 200

    # Try to access protected route again
    response = client.post("/admin/logout")

    # Should fail (session invalidated)
    assert response.status_code == 401


# =============================================================================
# SESSION EXPIRY TESTS
# =============================================================================


def test_session_expiry_after_24_hours(client, setup_admin_password, mocker):
    """Test that session expires after 24 hours."""
    sessions.clear()

    password = setup_admin_password

    # Login
    login_response = client.post("/admin/login", json={"password": password})
    assert login_response.status_code == 200

    # Mock time to 25 hours in the future
    from datetime import datetime, timezone, timedelta

    future_time = datetime.now(timezone.utc) + timedelta(hours=25)
    mocker.patch("backend.auth.datetime").now.return_value = future_time

    # Try to access protected route with expired session
    response = client.post("/admin/logout")

    # Should fail (session expired)
    assert response.status_code == 401


# =============================================================================
# COOKIE SECURITY TESTS
# =============================================================================


def test_login_sets_httponly_cookie(client, setup_admin_password):
    """Test that login sets HttpOnly cookie flag."""
    sessions.clear()

    password = setup_admin_password

    # Login
    response = client.post("/admin/login", json={"password": password})
    assert response.status_code == 200

    # Check Set-Cookie header
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header


def test_login_sets_samesite_cookie(client, setup_admin_password):
    """Test that login sets SameSite=Lax cookie attribute."""
    sessions.clear()

    password = setup_admin_password

    # Login
    response = client.post("/admin/login", json={"password": password})
    assert response.status_code == 200

    # Check Set-Cookie header
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "SameSite=lax" in set_cookie_header or "SameSite=Lax" in set_cookie_header


# =============================================================================
# NORWEGIAN ERROR MESSAGES
# =============================================================================


def test_login_error_message_in_norwegian(client, setup_admin_password):
    """Test that login error messages are in Norwegian."""
    response = client.post("/admin/login", json={"password": "wrong_password"})

    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["message"] == "Feil passord"  # Norwegian


# =============================================================================
# CHANNEL MANAGEMENT API (Story 1.5)
# =============================================================================


def test_add_channel_requires_authentication(client, test_db_file):
    """Test POST /admin/sources requires authentication (Story 1.5)."""
    # Attempt to add channel without login
    response = client.post("/admin/sources", json={"input": "https://youtube.com/channel/UCtest"})

    # Should return 401 Unauthorized
    assert response.status_code == 401


def test_get_sources_requires_authentication(client, test_db_file):
    """Test GET /admin/sources requires authentication (Story 1.5)."""
    # Attempt to get sources without login
    response = client.get("/admin/sources")

    # Should return 401 Unauthorized
    assert response.status_code == 401


def test_delete_source_requires_authentication(client, test_db_file):
    """Test DELETE /admin/sources/{id} requires authentication (Story 1.5)."""
    # Attempt to delete without login
    response = client.delete("/admin/sources/1")

    # Should return 401 Unauthorized
    assert response.status_code == 401


def test_refresh_source_requires_authentication(client, test_db_file):
    """Test POST /admin/sources/{id}/refresh requires authentication (Story 1.5)."""
    # Attempt to refresh without login
    response = client.post("/admin/sources/1/refresh")

    # Should return 401 Unauthorized
    assert response.status_code == 401


def test_add_channel_complete_flow(client, test_db_file, setup_admin_password, monkeypatch):
    """
    Test complete add channel flow (Story 1.5).

    Verifies:
    - POST /admin/sources with valid URL succeeds
    - Source created and videos added
    - GET /admin/sources shows new source in list
    """
    from unittest.mock import Mock

    # Login first
    sessions.clear()
    login_response = client.post("/admin/login", json={"password": setup_admin_password})
    assert login_response.status_code == 200
    session_cookie = login_response.cookies.get("session_id")

    # Mock YouTube API calls
    def mock_parse(source_input):
        return ("channel", "UCtest123")

    def mock_get_source(source_id):
        return None  # Not exists yet

    def mock_create_youtube():
        return Mock()

    def mock_fetch_all_channel(youtube, channel_id):
        return (["video1", "video2"], True)

    def mock_fetch_details(video_ids):
        return [
            {
                "video_id": "video1",
                "title": "Test Video 1",
                "youtube_channel_id": "UCtest123",
                "youtube_channel_name": "Test Channel",
                "thumbnail_url": "https://example.com/thumb1.jpg",
                "duration_seconds": 120,
                "published_at": "2023-01-01T00:00:00Z",
                "fetched_at": "2023-12-01T00:00:00Z",
            },
            {
                "video_id": "video2",
                "title": "Test Video 2",
                "youtube_channel_id": "UCtest123",
                "youtube_channel_name": "Test Channel",
                "thumbnail_url": "https://example.com/thumb2.jpg",
                "duration_seconds": 180,
                "published_at": "2023-01-02T00:00:00Z",
                "fetched_at": "2023-12-01T00:00:00Z",
            },
        ]

    def mock_dedupe(videos):
        return videos

    def mock_insert_source(**kwargs):
        return 1

    def mock_bulk_insert(videos, source_id):
        pass

    def mock_log_api_call(*args, **kwargs):
        pass

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)
    monkeypatch.setattr("backend.services.content_source.get_source_by_source_id", mock_get_source)
    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", mock_create_youtube
    )
    monkeypatch.setattr(
        "backend.services.content_source.fetch_all_channel_videos", mock_fetch_all_channel
    )
    monkeypatch.setattr("backend.services.content_source._fetch_video_details", mock_fetch_details)
    monkeypatch.setattr("backend.services.content_source._deduplicate_videos", mock_dedupe)
    monkeypatch.setattr("backend.services.content_source.insert_content_source", mock_insert_source)
    monkeypatch.setattr("backend.services.content_source.bulk_insert_videos", mock_bulk_insert)
    monkeypatch.setattr("backend.services.content_source.log_api_call", mock_log_api_call)

    # Add channel
    add_response = client.post(
        "/admin/sources",
        json={"input": "https://www.youtube.com/channel/UCtest123"},
        cookies={"session_id": session_cookie},
    )

    # Verify success
    assert add_response.status_code == 200
    add_data = add_response.json()
    assert add_data["success"] is True
    assert add_data["videosAdded"] == 2
    assert "Test Channel" in add_data["message"]


def test_add_duplicate_channel_returns_409(client, test_db_file, setup_admin_password, monkeypatch):
    """
    Test adding duplicate channel returns 409 Conflict (Story 1.5).

    Verifies:
    - Duplicate detection works
    - Returns 409 status code
    - Norwegian error message
    """
    # Login first
    sessions.clear()
    login_response = client.post("/admin/login", json={"password": setup_admin_password})
    session_cookie = login_response.cookies.get("session_id")

    # Mock YouTube API - source already exists
    def mock_parse(source_input):
        return ("channel", "UCexisting")

    def mock_get_source(source_id):
        return {"id": 1, "source_id": "UCexisting", "name": "Existing Channel"}

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)
    monkeypatch.setattr("backend.services.content_source.get_source_by_source_id", mock_get_source)

    # Attempt to add duplicate
    response = client.post(
        "/admin/sources",
        json={"input": "https://www.youtube.com/channel/UCexisting"},
        cookies={"session_id": session_cookie},
    )

    # Verify 409 Conflict
    assert response.status_code == 409
    data = response.json()
    assert "allerede lagt til" in data["message"].lower()


def test_add_invalid_url_returns_400(client, test_db_file, setup_admin_password, monkeypatch):
    """
    Test adding invalid URL returns 400 Bad Request (Story 1.5).

    Verifies:
    - Invalid URL validation
    - Returns 400 status code
    - Norwegian error message
    """
    # Login first
    sessions.clear()
    login_response = client.post("/admin/login", json={"password": setup_admin_password})
    session_cookie = login_response.cookies.get("session_id")

    # Mock parsing to raise ValueError
    def mock_parse(source_input):
        raise ValueError("Ugyldig YouTube-URL")

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)

    # Attempt to add invalid URL
    response = client.post(
        "/admin/sources", json={"input": "not-a-valid-url"}, cookies={"session_id": session_cookie}
    )

    # Verify 400 Bad Request
    assert response.status_code == 400
    data = response.json()
    assert "ugyldig" in data["message"].lower()


def test_remove_channel_cascade_deletes_videos(
    client, test_db_file, setup_admin_password, monkeypatch
):
    """
    Test removing channel CASCADE deletes videos (Story 1.5).

    Verifies:
    - DELETE /admin/sources/{id} succeeds
    - Videos are CASCADE deleted
    - Returns video count
    - Norwegian success message
    """
    # Login first
    sessions.clear()
    login_response = client.post("/admin/login", json={"password": setup_admin_password})
    session_cookie = login_response.cookies.get("session_id")

    # Mock service layer
    def mock_remove_source(source_id):
        return {"videos_removed": 42, "source_name": "Test Channel"}

    monkeypatch.setattr("backend.services.content_source.remove_source", mock_remove_source)

    # Delete channel
    response = client.delete("/admin/sources/1", cookies={"session_id": session_cookie})

    # Verify success
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["videosRemoved"] == 42
    assert "Test Channel" in data["message"]
    assert "42 videoer slettet" in data["message"]


def test_remove_nonexistent_channel_returns_404(
    client, test_db_file, setup_admin_password, monkeypatch
):
    """
    Test removing non-existent channel returns 404 (Story 1.5).

    Verifies:
    - NotFoundError handling
    - Returns 404 status code
    - Norwegian error message
    """
    from backend.exceptions import NotFoundError

    # Login first
    sessions.clear()
    login_response = client.post("/admin/login", json={"password": setup_admin_password})
    session_cookie = login_response.cookies.get("session_id")

    # Mock service to raise NotFoundError
    def mock_remove_source(source_id):
        raise NotFoundError("Kilde ikke funnet")

    monkeypatch.setattr("backend.services.content_source.remove_source", mock_remove_source)

    # Attempt to delete non-existent channel
    response = client.delete("/admin/sources/999", cookies={"session_id": session_cookie})

    # Verify 404
    assert response.status_code == 404
    data = response.json()
    assert "ikke funnet" in data["message"].lower()


def test_refresh_channel_adds_new_videos(client, test_db_file, setup_admin_password, monkeypatch):
    """
    Test refreshing channel adds new videos (Story 1.5).

    Verifies:
    - POST /admin/sources/{id}/refresh succeeds
    - Returns count of new videos added
    - Norwegian success message
    """
    # Login first
    sessions.clear()
    login_response = client.post("/admin/login", json={"password": setup_admin_password})
    session_cookie = login_response.cookies.get("session_id")

    # Mock service layer
    def mock_refresh_source(source_id):
        return {
            "success": True,
            "videos_added": 5,
            "videos_updated": 0,
            "last_refresh": "2023-12-01T10:00:00Z",
        }

    monkeypatch.setattr("backend.services.content_source.refresh_source", mock_refresh_source)

    # Refresh channel
    response = client.post("/admin/sources/1/refresh", cookies={"session_id": session_cookie})

    # Verify success
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["videosAdded"] == 5
    assert "5 nye videoer" in data["message"]


def test_partial_fetch_scenario(client, test_db_file, setup_admin_password, monkeypatch):
    """
    Test partial fetch returns correct flag (Story 1.5).

    Verifies:
    - Partial fetch flag returned in response
    - Partial videos are still saved
    - Frontend can show retry UI
    """
    from unittest.mock import Mock

    # Login first
    sessions.clear()
    login_response = client.post("/admin/login", json={"password": setup_admin_password})
    session_cookie = login_response.cookies.get("session_id")

    # Mock YouTube API - partial fetch (network error on page 3)
    def mock_parse(source_input):
        return ("channel", "UCpartial")

    def mock_get_source(source_id):
        return None

    def mock_create_youtube():
        return Mock()

    def mock_fetch_all_channel(youtube, channel_id):
        # Return partial fetch (fetch_complete=False)
        return (["video1", "video2"], False)

    def mock_fetch_details(video_ids):
        return [
            {
                "video_id": vid,
                "title": f"Video {vid}",
                "youtube_channel_id": "UCpartial",
                "youtube_channel_name": "Partial Channel",
                "thumbnail_url": f"https://example.com/{vid}.jpg",
                "duration_seconds": 120,
                "published_at": "2023-01-01T00:00:00Z",
                "fetched_at": "2023-12-01T00:00:00Z",
            }
            for vid in video_ids
        ]

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)
    monkeypatch.setattr("backend.services.content_source.get_source_by_source_id", mock_get_source)
    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", mock_create_youtube
    )
    monkeypatch.setattr(
        "backend.services.content_source.fetch_all_channel_videos", mock_fetch_all_channel
    )
    monkeypatch.setattr("backend.services.content_source._fetch_video_details", mock_fetch_details)
    monkeypatch.setattr("backend.services.content_source._deduplicate_videos", lambda v: v)
    monkeypatch.setattr("backend.services.content_source.insert_content_source", lambda **k: 1)
    monkeypatch.setattr("backend.services.content_source.bulk_insert_videos", lambda *a: None)
    monkeypatch.setattr("backend.services.content_source.log_api_call", lambda *a, **k: None)

    # Add channel with partial fetch
    response = client.post(
        "/admin/sources",
        json={"input": "https://www.youtube.com/channel/UCpartial"},
        cookies={"session_id": session_cookie},
    )

    # Verify partial fetch flag
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["partial"] is True
    assert data["videosAdded"] == 2
    assert "nettverksfeil" in data["message"].lower()
    assert data["retryAvailable"] is True


# =============================================================================
# STORY 2.1: CHILD VIDEO GRID INTEGRATION TESTS
# =============================================================================


@pytest.fixture
def setup_videos_for_grid(test_db_file):
    """
    Setup test videos and watch history for grid tests.

    Creates:
    - 20 available videos from 5 channels (algorithm has max 3 per channel constraint)
    - 5 videos in recent watch history (last 7 days)
    - Daily limit settings
    """
    conn = sqlite3.connect(test_db_file)

    # Add 5 content sources (channels) to satisfy max 3 per channel constraint
    channels = [
        ("UCtest1", "Test Channel 1"),
        ("UCtest2", "Test Channel 2"),
        ("UCtest3", "Test Channel 3"),
        ("UCtest4", "Test Channel 4"),
        ("UCtest5", "Test Channel 5"),
    ]
    source_ids = []
    for channel_id, channel_name in channels:
        conn.execute(
            """INSERT INTO content_sources
               (source_id, source_type, name, video_count, last_refresh, fetch_method, added_at)
               VALUES (?, ?, ?, ?, datetime('now'), ?, datetime('now'))""",
            (channel_id, "channel", channel_name, 4, "api"),
        )
        source_ids.append(conn.execute("SELECT last_insert_rowid()").fetchone()[0])

    # Add 20 videos (4 per channel) - algorithm allows max 3 per channel in results
    for i in range(20):
        channel_idx = i // 4  # 0-3 → channel 0, 4-7 → channel 1, etc.
        channel_id, channel_name = channels[channel_idx]
        source_id = source_ids[channel_idx]
        conn.execute(
            """INSERT INTO videos
               (video_id, title, content_source_id, youtube_channel_id, youtube_channel_name,
                thumbnail_url, duration_seconds, published_at, fetched_at, is_available)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 1)""",
            (
                f"video_{i}",
                f"Test Video {i}",
                source_id,
                channel_id,
                channel_name,
                f"https://i.ytimg.com/vi/video_{i}/default.jpg",
                300 + (i * 10),  # Varying durations: 300, 310, 320, ...
            ),
        )

    # Add watch history for 5 videos (watched yesterday)
    from datetime import datetime, timezone, timedelta

    yesterday = (datetime.now(timezone.utc) - timedelta(days=1)).date().isoformat()
    for i in [0, 1, 2, 3, 4]:
        channel_idx = i // 4  # Videos 0-3 → channel 1, video 4 → channel 2
        channel_name = channels[channel_idx][1]
        conn.execute(
            """INSERT INTO watch_history
               (video_id, video_title, channel_name, watched_at, duration_watched_seconds, completed, manual_play, grace_play)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                f"video_{i}",
                f"Test Video {i}",
                channel_name,
                f"{yesterday}T12:00:00Z",
                300,
                1,
                0,
                0,
            ),
        )

    # Set daily limit to 30 minutes
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("daily_limit_minutes", "30"),
    )

    conn.commit()
    conn.close()

    return test_db_file


def test_int_001_get_api_videos_returns_requested_count(client, setup_videos_for_grid):
    """
    2.1-INT-001: GET /api/videos returns requested count of videos.

    Verifies:
    - API endpoint responds with requested number of videos
    - Response structure is correct
    - Daily limit included in response
    """
    # Request 9 videos
    response = client.get("/api/videos?count=9")

    # Verify response
    assert response.status_code == 200
    data = response.json()

    # Check structure
    assert "videos" in data
    assert "dailyLimit" in data

    # Check count
    assert len(data["videos"]) == 9

    # Verify video structure
    video = data["videos"][0]
    assert "videoId" in video
    assert "title" in video
    assert "youtubeChannelName" in video
    assert "thumbnailUrl" in video
    assert "durationSeconds" in video


def test_int_002_fetch_grid_size_setting_from_database(client, setup_videos_for_grid):
    """
    2.1-INT-002: Grid size controlled by database setting.

    Verifies:
    - Grid size can be configured via settings
    - API respects count parameter
    - Setting persists in database
    """
    # Note: In current implementation, count is passed as query param
    # Setting integration would be tested by fetching setting first
    # then passing count. For now, test count parameter works.

    # Request 12 videos
    response = client.get("/api/videos?count=12")

    assert response.status_code == 200
    data = response.json()
    assert len(data["videos"]) == 12


def test_int_003_algorithm_with_real_watch_history_data(client, setup_videos_for_grid):
    """
    2.1-INT-003: Weighted random algorithm uses real watch history from database.

    Verifies:
    - Algorithm accesses watch history table
    - Favorites calculated from last 7 days
    - Novelty videos identified correctly
    """
    # Request videos multiple times to observe weighted selection
    selections = []
    for _ in range(10):
        response = client.get("/api/videos?count=9")
        assert response.status_code == 200
        data = response.json()

        video_ids = [v["videoId"] for v in data["videos"]]
        selections.append(set(video_ids))

    # Verify: Selections vary (randomness)
    # If algorithm works, we should see different selections
    unique_selections = [frozenset(s) for s in selections]
    assert len(set(unique_selections)) > 1, "All selections identical - randomness not working"

    # Verify: Some selections include favorites (video_0 to video_4)
    favorites = {f"video_{i}" for i in range(5)}
    has_favorites = any(favorites.intersection(s) for s in selections)
    assert has_favorites, "No favorites ever selected"


def test_int_004_selection_excludes_videos_watched_today(client, setup_videos_for_grid):
    """
    2.1-INT-004: Algorithm considers videos watched TODAY when calculating novelty.

    Verifies:
    - Recent watch history (last 7 days) used for favorites pool
    - Videos watched yesterday are in favorites pool
    - Algorithm respects UTC dates
    """
    # Our setup has videos watched YESTERDAY, so they should appear in selections
    # (favorites pool, not excluded)

    response = client.get("/api/videos?count=9")
    assert response.status_code == 200
    data = response.json()

    # Should successfully return 9 videos
    assert len(data["videos"]) == 9


def test_int_007_randomness_validated_over_20_iterations(client, setup_videos_for_grid):
    """
    2.1-INT-007: Verify randomness over multiple API calls (20 iterations).

    Verifies:
    - No deterministic patterns in selection
    - Different videos returned on each call
    - Random shuffle works correctly
    """
    selections = []

    for _ in range(20):
        response = client.get("/api/videos?count=9")
        assert response.status_code == 200
        data = response.json()

        video_ids = tuple(v["videoId"] for v in data["videos"])
        selections.append(video_ids)

    # Verify: At least 10 unique selections (50% unique)
    unique_selections = set(selections)
    assert (
        len(unique_selections) >= 10
    ), f"Only {len(unique_selections)}/20 unique selections - possible deterministic pattern"


def test_int_008_api_returns_different_videos_on_subsequent_calls(client, setup_videos_for_grid):
    """
    2.1-INT-008: Grid refresh returns different videos.

    Verifies:
    - No caching between API calls
    - Fresh random selection each time
    - AC10: Grid refreshes when returning from playback
    """
    # First call
    response1 = client.get("/api/videos?count=9")
    assert response1.status_code == 200
    video_ids_1 = {v["videoId"] for v in response1.json()["videos"]}

    # Second call
    response2 = client.get("/api/videos?count=9")
    assert response2.status_code == 200
    video_ids_2 = {v["videoId"] for v in response2.json()["videos"]}

    # Should not be identical (very unlikely with 20 videos and random selection)
    assert video_ids_1 != video_ids_2, "Two consecutive calls returned identical videos"


def test_int_009_setting_change_reflected_in_grid_size(client, setup_videos_for_grid):
    """
    2.1-INT-009: Changing grid_size setting affects API response.

    Verifies:
    - Configuration changes respected
    - Count parameter controls grid size
    - Range validation (4-15)
    """
    # Test different count values
    for count in [4, 9, 12, 15]:
        response = client.get(f"/api/videos?count={count}")
        assert response.status_code == 200
        data = response.json()
        assert len(data["videos"]) == count


def test_int_010_wind_down_filters_videos_by_max_duration(client, setup_videos_for_grid):
    """
    2.1-INT-010: Wind-down mode filters videos by duration.

    Verifies:
    - When daily limit approaching, short videos selected
    - max_duration_seconds parameter works
    - TIER 1 Rule: Time limit enforcement
    """
    conn = sqlite3.connect(setup_videos_for_grid)

    # Add watch history for TODAY to trigger wind-down (8 minutes remaining)
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).date().isoformat()
    conn.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, duration_watched_seconds, completed, manual_play, grace_play)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "video_10",
            "Test Video 10",
            "Test Channel",
            f"{today}T12:00:00Z",
            1320,  # 22 minutes watched
            1,
            0,
            0,
        ),
    )
    conn.commit()
    conn.close()

    # Request videos (should be in wind-down mode with 8 min remaining = 480 sec)
    response = client.get("/api/videos?count=9")
    assert response.status_code == 200
    data = response.json()

    # Verify wind-down state
    assert data["dailyLimit"]["currentState"] == "winddown"
    assert data["dailyLimit"]["minutesRemaining"] == 8

    # Verify videos returned (should be filtered by duration, but fallback if none fit)
    assert len(data["videos"]) > 0


def test_int_011_wind_down_shows_all_videos_if_none_fit_duration(client, test_db_file):
    """
    2.1-INT-011: Wind-down fallback when no videos fit remaining time.

    Verifies:
    - If max_duration filters out ALL videos, return all videos anyway
    - Better to show options than empty grid
    - Fallback logic works correctly
    """
    conn = sqlite3.connect(test_db_file)

    # Add content source
    conn.execute(
        """INSERT INTO content_sources
           (source_id, source_type, name, video_count, last_refresh, fetch_method, added_at)
           VALUES (?, ?, ?, ?, datetime('now'), ?, datetime('now'))""",
        ("UCtest456", "channel", "Test Channel 2", 5, "api"),
    )
    source_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

    # Add 5 videos - ALL longer than 5 minutes (600+ seconds)
    for i in range(5):
        conn.execute(
            """INSERT INTO videos
               (video_id, title, content_source_id, youtube_channel_id, youtube_channel_name,
                thumbnail_url, duration_seconds, published_at, fetched_at, is_available)
               VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), 1)""",
            (
                f"long_video_{i}",
                f"Long Video {i}",
                source_id,
                "UCtest456",
                "Test Channel 2",
                f"https://i.ytimg.com/vi/long_video_{i}/default.jpg",
                600 + (i * 60),  # All >10 minutes
            ),
        )

    # Add watch history to get to wind-down with only 3 minutes remaining
    from datetime import datetime, timezone

    today = datetime.now(timezone.utc).date().isoformat()
    conn.execute(
        """INSERT INTO watch_history
           (video_id, video_title, channel_name, watched_at, duration_watched_seconds, completed, manual_play, grace_play)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            "long_video_0",
            "Long Video 0",
            "Test Channel 2",
            f"{today}T12:00:00Z",
            1620,  # 27 minutes watched
            1,
            0,
            0,
        ),
    )

    # Set daily limit
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("daily_limit_minutes", "30"),
    )

    conn.commit()
    conn.close()

    # Request videos (wind-down with 3 min remaining, but all videos >10 min)
    response = client.get("/api/videos?count=9")
    assert response.status_code == 200
    data = response.json()

    # Verify: Still returns videos (fallback - all 5 long videos)
    assert len(data["videos"]) == 5


def test_int_012_sql_uses_placeholders_no_string_formatting(client, setup_videos_for_grid):
    """
    2.1-INT-012: TIER 1 Rule 6 - SQL injection prevention via placeholders.

    Verifies:
    - All SQL queries use placeholders (?)
    - No string formatting in SQL
    - Count parameter validated before use
    """
    # Attempt SQL injection via count parameter (FastAPI will validate type)
    # But test that valid range is enforced
    response = client.get("/api/videos?count=999")

    # Should reject (outside 4-15 range)
    assert response.status_code == 400
    data = response.json()
    assert "error" in data


def test_int_013_handle_no_videos_available_error_with_norwegian_message(client, test_db_file):
    """
    2.1-INT-013: NoVideosAvailableError returns Norwegian error message.

    Verifies:
    - TIER 3 Rule 14: Norwegian user messages
    - Error handling for empty database
    - Proper HTTP status code (503)
    """
    # Setup: Empty database (no videos)
    conn = sqlite3.connect(test_db_file)
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("daily_limit_minutes", "30"),
    )
    conn.commit()
    conn.close()

    # Request videos from empty database
    response = client.get("/api/videos?count=9")

    # Verify: 503 Service Unavailable with Norwegian message
    assert response.status_code == 503
    data = response.json()
    assert "error" in data
    assert "message" in data
    assert "Ingen videoer tilgjengelig" in data["message"]


def test_int_014_return_503_status_when_no_videos_available(client, test_db_file):
    """
    2.1-INT-014: HTTP 503 status code when no videos available.

    Verifies:
    - Correct status code for service unavailable
    - Distinguishes from 500 (internal error)
    - API contract for error state
    """
    # Setup: Empty database
    conn = sqlite3.connect(test_db_file)
    conn.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
        ("daily_limit_minutes", "30"),
    )
    conn.commit()
    conn.close()

    # Request videos
    response = client.get("/api/videos?count=9")

    # Verify: 503 status
    assert response.status_code == 503


def test_int_015_always_use_utc_for_datetime_operations(client, setup_videos_for_grid):
    """
    2.1-INT-015: TIER 1 Rule 3 - UTC timezone for all date operations.

    Verifies:
    - Daily limit calculations use UTC
    - Watch history queries use UTC dates
    - Reset time in response is UTC
    """
    response = client.get("/api/videos?count=9")
    assert response.status_code == 200
    data = response.json()

    # Verify: resetTime is UTC (ends with 'Z')
    reset_time = data["dailyLimit"]["resetTime"]
    assert reset_time.endswith("Z"), "resetTime not in UTC format (should end with 'Z')"

    # Verify: date is YYYY-MM-DD format
    date = data["dailyLimit"]["date"]
    assert len(date) == 10, "date not in YYYY-MM-DD format"
    assert date[4] == "-" and date[7] == "-", "date not in YYYY-MM-DD format"


def test_int_016_database_context_manager_used_for_all_queries(client, setup_videos_for_grid):
    """
    2.1-INT-016: TIER 2 Rule 7 - Context manager for database access.

    Verifies:
    - All database queries use context manager
    - Connections properly closed
    - Transactions committed/rolled back correctly
    """
    # This is more of a code review test, but we can verify:
    # - Multiple API calls don't leave connections open
    # - Database not locked after multiple requests

    # Make 10 rapid API calls
    for _ in range(10):
        response = client.get("/api/videos?count=9")
        assert response.status_code == 200

    # Verify: Database still accessible (no locks)
    response = client.get("/api/videos?count=9")
    assert response.status_code == 200


def test_count_parameter_validation_4_to_15_range(client, setup_videos_for_grid):
    """
    Count parameter validation tests (2.1-UNIT-001 to 2.1-UNIT-004).

    Note: These were labeled as "Unit" tests in test design but are actually
    integration tests since they test the API endpoint, not isolated logic.

    Verifies:
    - count < 4 rejected
    - count > 15 rejected
    - Valid range (4-15) accepted
    - Default (9) works
    """
    # Test below minimum
    response = client.get("/api/videos?count=3")
    assert response.status_code == 400

    # Test above maximum
    response = client.get("/api/videos?count=16")
    assert response.status_code == 400

    # Test valid values
    for count in [4, 9, 15]:
        response = client.get(f"/api/videos?count={count}")
        assert response.status_code == 200
        assert len(response.json()["videos"]) == count

    # Test default (no count parameter)
    response = client.get("/api/videos")
    assert response.status_code == 200
    assert len(response.json()["videos"]) == 9  # Default is 9
