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
    """Create FastAPI test client."""
    return TestClient(app)


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
