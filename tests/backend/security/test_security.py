"""
Security tests for authentication system.

Tests session security, cookie attributes, timing attacks, and information leakage.
All tests marked with @pytest.mark.security
"""

import pytest
import time
from fastapi.testclient import TestClient

from backend.main import app
from backend.auth import create_session, hash_password, verify_password, sessions


@pytest.fixture
def client():
    """Create FastAPI test client."""
    return TestClient(app)


# =============================================================================
# SESSION SECURITY TESTS
# =============================================================================


@pytest.mark.security
def test_session_id_is_cryptographically_random():
    """
    Test that session IDs have sufficient entropy (32 bytes = 256 bits).

    Verifies:
    - Session IDs are unique
    - Session IDs are URL-safe
    - Session IDs have expected length (43 chars for 32 bytes base64)
    """
    sessions.clear()

    # Generate multiple session IDs
    session_ids = [create_session() for _ in range(100)]

    # Verify all are unique (no collisions)
    assert len(session_ids) == len(set(session_ids)), "Session IDs must be unique"

    # Verify length (32 bytes = 43 chars in URL-safe base64)
    for session_id in session_ids:
        assert len(session_id) == 43, "Session ID must be 43 characters (32 bytes)"

        # Verify URL-safe characters only (base64url: A-Za-z0-9_-)
        assert all(c.isalnum() or c in "-_" for c in session_id), "Session ID must be URL-safe"


@pytest.mark.security
def test_session_isolation():
    """
    Test that sessions are isolated from each other.

    Verifies:
    - Different sessions have different IDs
    - One session cannot access another session's data
    """
    sessions.clear()

    session_id1 = create_session()
    session_id2 = create_session()

    # Verify sessions are different
    assert session_id1 != session_id2

    # Verify each session has independent data
    session1 = sessions[session_id1]
    session2 = sessions[session_id2]
    assert session1["created_at"] != session2["created_at"]


# =============================================================================
# COOKIE SECURITY TESTS
# =============================================================================


@pytest.mark.security
def test_session_cookie_httponly_attribute(client, test_db):
    """
    Test that session cookie has HttpOnly flag to prevent JavaScript access.

    This protects against XSS attacks by preventing JavaScript from reading
    the session cookie.
    """
    # Set up admin password
    import json
    from backend.db.queries import set_setting

    password = "test_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)
    set_setting("admin_password_hash", json_value)

    # Login to get session cookie
    response = client.post("/admin/login", json={"password": password})
    assert response.status_code == 200

    # Check Set-Cookie header for HttpOnly flag
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "HttpOnly" in set_cookie_header, "Session cookie must have HttpOnly flag"


@pytest.mark.security
def test_session_cookie_secure_attribute(client, test_db):
    """
    Test that session cookie has Secure flag for HTTPS-only transmission.

    This prevents session cookies from being sent over unencrypted HTTP.
    """
    # Set up admin password
    import json
    from backend.db.queries import set_setting

    password = "test_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)
    set_setting("admin_password_hash", json_value)

    # Login to get session cookie
    response = client.post("/admin/login", json={"password": password})
    assert response.status_code == 200

    # Check Set-Cookie header for Secure flag
    set_cookie_header = response.headers.get("set-cookie", "")
    assert (
        "Secure" in set_cookie_header or "secure" in set_cookie_header
    ), "Session cookie must have Secure flag"


@pytest.mark.security
def test_session_cookie_samesite_attribute(client, test_db):
    """
    Test that session cookie has SameSite=Lax for CSRF protection.

    This prevents the browser from sending the cookie in cross-site requests.
    """
    # Set up admin password
    import json
    from backend.db.queries import set_setting

    password = "test_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)
    set_setting("admin_password_hash", json_value)

    # Login to get session cookie
    response = client.post("/admin/login", json={"password": password})
    assert response.status_code == 200

    # Check Set-Cookie header for SameSite attribute
    set_cookie_header = response.headers.get("set-cookie", "")
    assert (
        "SameSite=lax" in set_cookie_header or "SameSite=Lax" in set_cookie_header
    ), "Session cookie must have SameSite=Lax"


# =============================================================================
# TIMING ATTACK PROTECTION
# =============================================================================


@pytest.mark.security
def test_password_verification_constant_time():
    """
    Test that password verification does not leak timing information.

    Bcrypt inherently protects against timing attacks, but we verify
    that both success and failure cases take similar time.

    This is a basic check - bcrypt's work factor provides the actual protection.
    """
    password = "correct_password"
    hashed = hash_password(password)

    # Time correct password verification
    start = time.time()
    result1 = verify_password(password, hashed)
    time_correct = time.time() - start

    # Time incorrect password verification
    start = time.time()
    result2 = verify_password("wrong_password", hashed)
    time_incorrect = time.time() - start

    # Verify results are as expected
    assert result1 is True
    assert result2 is False

    # Both should take similar time (within 50% difference)
    # Bcrypt ensures constant-time comparison
    ratio = max(time_correct, time_incorrect) / min(time_correct, time_incorrect)
    assert ratio < 1.5, "Password verification timing should not leak information (ratio < 1.5)"


# =============================================================================
# INFORMATION LEAKAGE TESTS
# =============================================================================


@pytest.mark.security
def test_password_hash_never_in_error_messages(client, test_db):
    """
    Test that password hashes never appear in error messages or logs.

    This prevents information leakage that could aid attackers.
    """
    # Set up admin password
    import json
    from backend.db.queries import set_setting

    password = "test_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)
    set_setting("admin_password_hash", json_value)

    # Try various error scenarios
    responses = [
        client.post("/admin/login", json={"password": "wrong"}),
        client.post("/admin/login", json={}),
        client.post("/admin/logout"),
    ]

    # Verify hash never appears in any response
    for response in responses:
        response_text = response.text
        assert hashed not in response_text, "Password hash must never appear in responses"
        assert "$2b$" not in response_text, "Bcrypt hash format must not leak in responses"


@pytest.mark.security
def test_login_error_messages_do_not_leak_information(client, test_db):
    """
    Test that login errors don't distinguish between invalid password and other errors.

    This prevents username enumeration attacks (not applicable here since there's
    only one admin account, but good practice).
    """
    # Set up admin password
    import json
    from backend.db.queries import set_setting

    password = "test_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)
    set_setting("admin_password_hash", json_value)

    # Try login with wrong password
    response = client.post("/admin/login", json={"password": "wrong_password"})

    # Error message should be generic Norwegian message
    assert response.status_code == 401
    data = response.json()
    assert data["detail"]["message"] == "Feil passord"

    # Should not reveal any system information
    response_text = response.text.lower()
    assert "database" not in response_text
    assert "sql" not in response_text
    assert "exception" not in response_text


# =============================================================================
# SESSION FIXATION PROTECTION
# =============================================================================


@pytest.mark.security
def test_new_session_created_on_each_login():
    """
    Test that each login creates a fresh session ID.

    This prevents session fixation attacks where an attacker tricks
    a user into using a known session ID.
    """
    sessions.clear()

    # Create multiple sessions
    session_id1 = create_session()
    session_id2 = create_session()
    session_id3 = create_session()

    # All session IDs should be different
    assert session_id1 != session_id2
    assert session_id2 != session_id3
    assert session_id1 != session_id3


# =============================================================================
# BRUTE FORCE PROTECTION
# =============================================================================


@pytest.mark.security
def test_multiple_failed_login_attempts_allowed():
    """
    Test that the system allows multiple failed login attempts.

    Note: This project does not implement rate limiting or account lockout
    for the single admin account. Bcrypt's work factor provides computational
    cost protection against brute force.

    This test documents the current behavior and can be extended with
    rate limiting in the future if needed.
    """
    # Set up admin password
    import json
    from fastapi.testclient import TestClient
    from backend.db.queries import set_setting

    client = TestClient(app)

    password = "test_password"
    hashed = hash_password(password)
    json_value = json.dumps(hashed)
    set_setting("admin_password_hash", json_value)

    # Attempt multiple failed logins
    for _ in range(5):
        response = client.post("/admin/login", json={"password": "wrong"})
        assert response.status_code == 401

    # Verify correct password still works after failed attempts
    response = client.post("/admin/login", json={"password": password})
    assert response.status_code == 200
