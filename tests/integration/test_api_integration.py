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
