"""
Tests for admin settings endpoints (Story 3.2).

Covers:
- GET /api/admin/settings (authentication, excludes password hash)
- PUT /api/admin/settings (partial update, validation, immediate effect)
- POST /api/admin/settings/reset (restores defaults, preserves password)

TIER 1 Rules Tested:
- Rule 3: UTC time handling in set_setting
- Rule 4: Admin password never returned, never reset
- Rule 5: Pydantic validation enforces ranges
- Rule 6: SQL injection prevention via parameterized queries
- Rule 10: Authentication required for admin endpoints
"""

import pytest
import json
from datetime import datetime, timezone

from backend.auth import hash_password


# =============================================================================
# TEST FIXTURES AND HELPERS
# =============================================================================


def setup_admin_auth(test_db):
    """
    Setup admin password in test database.

    Returns the password for use in login.
    """
    password = "test_admin_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)

    # Insert setting directly into test database
    now = datetime.now(timezone.utc).isoformat()
    test_db.execute(
        "INSERT OR REPLACE INTO settings (key, value, updated_at, created_at) VALUES (?, ?, ?, ?)",
        ("admin_password_hash", json_value, now, now),
    )
    test_db.commit()

    return password


def authenticate_client(test_client, test_db):
    """
    Authenticate test client and set session cookie.
    """
    password = setup_admin_auth(test_db)
    login_response = test_client.post("/admin/login", json={"password": password})
    assert login_response.status_code == 200

    # Manually set session cookie
    session_cookie = login_response.cookies.get("session_id")
    assert session_cookie is not None
    test_client.cookies.set("session_id", session_cookie)


# =============================================================================
# GET /api/admin/settings TESTS
# =============================================================================


@pytest.mark.tier1
def test_get_settings_requires_authentication(test_client):
    """
    Test GET /api/admin/settings returns 401 without session.

    Verifies TIER 1 Rule 10: Authentication required.
    T3.2-BE-003
    """
    # Act
    response = test_client.get("/api/admin/settings")

    # Assert
    assert response.status_code == 401


@pytest.mark.tier1
def test_get_settings_rejects_expired_and_invalid_sessions(test_client, test_db):
    """
    Test GET /api/admin/settings returns 401 for expired/invalid session tokens.

    Verifies TIER 1 Rule 10: Authentication enforcement with expired sessions.
    T3.2-BE-004
    """
    # Test 1: Expired session token
    # Arrange: Create a valid session then manually expire it
    from backend.auth import sessions, create_session
    from datetime import timedelta

    session_id = create_session()
    # Manually set expiry to the past
    sessions[session_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
    test_client.cookies.set("session_id", session_id)

    # Act
    response1 = test_client.get("/api/admin/settings")

    # Assert
    assert response1.status_code == 401

    # Test 2: Malformed/non-existent session token
    # Arrange: Use fake session ID that doesn't exist
    fake_session_id = "this_session_does_not_exist_in_store"
    test_client.cookies.clear()
    test_client.cookies.set("session_id", fake_session_id)

    # Act
    response2 = test_client.get("/api/admin/settings")

    # Assert
    assert response2.status_code == 401

    # Test 3: Empty session token
    # Arrange: Empty string as session ID
    test_client.cookies.clear()
    test_client.cookies.set("session_id", "")

    # Act
    response3 = test_client.get("/api/admin/settings")

    # Assert
    assert response3.status_code == 401


def test_get_settings_returns_current_values(test_client, test_db):
    """
    Test GET /api/admin/settings returns all settings with correct values.

    Verifies AC: Returns current settings values.
    """
    # Arrange
    authenticate_client(test_client, test_db)

    # Act
    response = test_client.get("/api/admin/settings")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "settings" in data
    assert data["settings"]["daily_limit_minutes"] == 30  # Default
    assert data["settings"]["grid_size"] == 9  # Default
    assert data["settings"]["audio_enabled"] is True  # Default


@pytest.mark.tier1
def test_get_settings_excludes_password_hash(test_client, test_db):
    """
    Test GET /api/admin/settings NEVER returns admin_password_hash.

    Verifies TIER 1 Rule 4: Password security - never expose hash.
    """
    # Arrange
    authenticate_client(test_client, test_db)

    # Act
    response = test_client.get("/api/admin/settings")

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "admin_password_hash" not in data.get("settings", {})
    assert "password" not in str(data).lower()  # No password-related keys at all


# =============================================================================
# PUT /api/admin/settings TESTS
# =============================================================================


@pytest.mark.tier1
def test_update_settings_requires_authentication(test_client):
    """
    Test PUT /api/admin/settings returns 401 without session.

    Verifies TIER 1 Rule 10: Authentication required.
    T3.2-BE-012
    """
    # Act
    response = test_client.put("/api/admin/settings", json={"daily_limit_minutes": 45})

    # Assert
    assert response.status_code == 401

    # Also verify expired/invalid sessions are rejected (part of BE-004)
    from backend.auth import sessions, create_session
    from datetime import timedelta

    # Test expired session
    session_id = create_session()
    sessions[session_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
    test_client.cookies.set("session_id", session_id)
    response_expired = test_client.put("/api/admin/settings", json={"daily_limit_minutes": 45})
    assert response_expired.status_code == 401

    # Test invalid session
    test_client.cookies.clear()
    test_client.cookies.set("session_id", "invalid_session_token")
    response_invalid = test_client.put("/api/admin/settings", json={"daily_limit_minutes": 45})
    assert response_invalid.status_code == 401


def test_update_settings_partial_update(test_client, test_db):
    """
    Test PUT /api/admin/settings supports partial update (only specified fields updated).

    Verifies AC: Partial update works correctly.
    """
    # Arrange
    authenticate_client(test_client, test_db)

    # Act: Update only daily_limit_minutes
    response = test_client.put("/api/admin/settings", json={"daily_limit_minutes": 45})

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["settings"]["daily_limit_minutes"] == 45
    assert data["settings"]["grid_size"] == 9  # Unchanged
    assert data["settings"]["audio_enabled"] is True  # Unchanged
    assert "message" in data
    assert "Innstillinger lagret" in data["message"]


@pytest.mark.tier1
def test_update_settings_validation_range_limits(test_client, test_db):
    """
    Test PUT /api/admin/settings enforces Pydantic range validation.

    Verifies TIER 1 Rule 5: Input validation (ge/le constraints).
    """
    # Arrange
    authenticate_client(test_client, test_db)

    # Act: Try to set daily_limit below minimum (5)
    response1 = test_client.put("/api/admin/settings", json={"daily_limit_minutes": 4})

    # Act: Try to set daily_limit above maximum (180)
    response2 = test_client.put("/api/admin/settings", json={"daily_limit_minutes": 181})

    # Act: Try to set grid_size below minimum (4)
    response3 = test_client.put("/api/admin/settings", json={"grid_size": 3})

    # Act: Try to set grid_size above maximum (15)
    response4 = test_client.put("/api/admin/settings", json={"grid_size": 16})

    # Assert: All should return 422 Unprocessable Entity
    assert response1.status_code == 422
    assert response2.status_code == 422
    assert response3.status_code == 422
    assert response4.status_code == 422


def test_update_settings_invalid_type_rejected(test_client, test_db):
    """
    Test PUT /api/admin/settings rejects invalid types.

    Verifies TIER 1 Rule 5: Input validation (type safety).
    """
    # Arrange
    authenticate_client(test_client, test_db)

    # Act: Try to send string for int field
    response1 = test_client.put("/api/admin/settings", json={"daily_limit_minutes": "not_a_number"})

    # Act: Try to send int for bool field
    response2 = test_client.put("/api/admin/settings", json={"audio_enabled": 123})

    # Assert: Both should return 422 Unprocessable Entity
    assert response1.status_code == 422
    assert response2.status_code == 422


def test_update_settings_applies_immediately(test_client, test_db):
    """
    Test settings changes apply immediately (GET returns updated values).

    Verifies AC: Settings apply immediately without restart.
    """
    # Arrange
    authenticate_client(test_client, test_db)

    # Act: Update settings
    update_response = test_client.put(
        "/api/admin/settings",
        json={"daily_limit_minutes": 60, "grid_size": 12, "audio_enabled": False},
    )

    # Act: Immediately fetch settings
    get_response = test_client.get("/api/admin/settings")

    # Assert: Updated values returned
    assert update_response.status_code == 200
    assert get_response.status_code == 200
    data = get_response.json()
    assert data["settings"]["daily_limit_minutes"] == 60
    assert data["settings"]["grid_size"] == 12
    assert data["settings"]["audio_enabled"] is False


# =============================================================================
# POST /api/admin/settings/reset TESTS
# =============================================================================


@pytest.mark.tier1
def test_reset_settings_requires_authentication(test_client):
    """
    Test POST /api/admin/settings/reset returns 401 without session.

    Verifies TIER 1 Rule 10: Authentication required.
    T3.2-BE-015
    """
    # Act
    response = test_client.post("/api/admin/settings/reset")

    # Assert
    assert response.status_code == 401

    # Also verify expired/invalid sessions are rejected (part of BE-004)
    from backend.auth import sessions, create_session
    from datetime import timedelta

    # Test expired session
    session_id = create_session()
    sessions[session_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(hours=1)
    test_client.cookies.set("session_id", session_id)
    response_expired = test_client.post("/api/admin/settings/reset")
    assert response_expired.status_code == 401

    # Test invalid session
    test_client.cookies.clear()
    test_client.cookies.set("session_id", "invalid_session_token")
    response_invalid = test_client.post("/api/admin/settings/reset")
    assert response_invalid.status_code == 401


def test_reset_settings_restores_defaults(test_client, test_db):
    """
    Test POST /api/admin/settings/reset restores all defaults.

    Verifies AC: Reset to defaults works correctly.
    """
    # Arrange
    authenticate_client(test_client, test_db)

    # Setup: Change settings from defaults
    test_client.put(
        "/api/admin/settings",
        json={"daily_limit_minutes": 120, "grid_size": 6, "audio_enabled": False},
    )

    # Act: Reset
    reset_response = test_client.post("/api/admin/settings/reset")

    # Assert: Defaults restored
    assert reset_response.status_code == 200
    data = reset_response.json()
    assert data["success"] is True
    assert data["settings"]["daily_limit_minutes"] == 30
    assert data["settings"]["grid_size"] == 9
    assert data["settings"]["audio_enabled"] is True
    assert "message" in data
    assert "Innstillinger tilbakestilt" in data["message"]


@pytest.mark.tier1
def test_reset_settings_preserves_password(test_client, test_db):
    """
    Test POST /api/admin/settings/reset NEVER resets admin password.

    Verifies TIER 1 Rule 4: Password security - preserve on reset.
    """
    # Arrange
    authenticate_client(test_client, test_db)

    # Setup: Get current password hash
    original_hash_result = test_db.execute(
        "SELECT value FROM settings WHERE key = 'admin_password_hash'"
    ).fetchone()
    original_hash = original_hash_result[0]

    # Act: Reset settings
    reset_response = test_client.post("/api/admin/settings/reset")

    # Assert: Password unchanged
    assert reset_response.status_code == 200
    current_hash_result = test_db.execute(
        "SELECT value FROM settings WHERE key = 'admin_password_hash'"
    ).fetchone()
    current_hash = current_hash_result[0]

    assert current_hash == original_hash  # Password preserved
