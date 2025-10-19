"""
Unit tests for backend/auth.py module.

Tests session management, password hashing, and authentication helpers.
Coverage target: 85%+ for auth.py
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from fastapi import HTTPException

from backend.auth import (
    hash_password,
    verify_password,
    create_session,
    validate_session,
    invalidate_session,
    require_auth,
    sessions,
)


# =============================================================================
# PASSWORD HASHING TESTS
# =============================================================================


def test_hash_password_returns_bcrypt_hash():
    """Test that hash_password returns a valid bcrypt hash."""
    password = "test_password_123"
    hashed = hash_password(password)

    # Verify bcrypt format
    assert hashed.startswith("$2b$")
    assert len(hashed) == 60


def test_verify_password_with_correct_password():
    """Test password verification succeeds with correct password."""
    password = "correct_password"
    hashed = hash_password(password)

    assert verify_password(password, hashed) is True


def test_verify_password_with_wrong_password():
    """Test password verification fails with wrong password."""
    password = "correct_password"
    wrong_password = "wrong_password"
    hashed = hash_password(password)

    assert verify_password(wrong_password, hashed) is False


# =============================================================================
# SESSION MANAGEMENT TESTS
# =============================================================================


def test_create_session_generates_unique_token():
    """Test that create_session generates a unique session ID."""
    # Clear sessions before test
    sessions.clear()

    session_id1 = create_session()
    session_id2 = create_session()

    # Session IDs should be unique
    assert session_id1 != session_id2

    # Session IDs should be URL-safe strings (43 chars for 32 bytes base64)
    assert len(session_id1) == 43
    assert len(session_id2) == 43


def test_create_session_stores_session_data():
    """Test that create_session stores session with timestamps."""
    sessions.clear()

    session_id = create_session()

    # Verify session exists in store
    assert session_id in sessions

    # Verify session has required fields
    session = sessions[session_id]
    assert "created_at" in session
    assert "expires_at" in session

    # Verify timestamps are datetime objects with UTC timezone
    assert isinstance(session["created_at"], datetime)
    assert isinstance(session["expires_at"], datetime)
    assert session["created_at"].tzinfo == timezone.utc
    assert session["expires_at"].tzinfo == timezone.utc


def test_create_session_sets_24_hour_expiry():
    """Test that sessions expire after 24 hours."""
    sessions.clear()

    session_id = create_session()
    session = sessions[session_id]

    # Calculate expected expiry (24 hours from creation)
    expected_expiry = session["created_at"] + timedelta(hours=24)

    # Verify expiry is set correctly (within 1 second tolerance)
    time_diff = abs((session["expires_at"] - expected_expiry).total_seconds())
    assert time_diff < 1, "Session expiry should be 24 hours from creation"


def test_validate_session_returns_true_for_valid_session():
    """Test that validate_session returns True for valid, unexpired session."""
    sessions.clear()

    session_id = create_session()

    # Validate immediately after creation
    assert validate_session(session_id) is True


def test_validate_session_returns_false_for_nonexistent_session():
    """Test that validate_session returns False for non-existent session."""
    sessions.clear()

    # Try to validate session that doesn't exist
    assert validate_session("nonexistent_session_id") is False


def test_validate_session_returns_false_for_expired_session(mocker):
    """Test that validate_session returns False for expired session."""
    sessions.clear()

    session_id = create_session()

    # Mock datetime.now to simulate time passing (25 hours)
    future_time = datetime.now(timezone.utc) + timedelta(hours=25)
    mocker.patch("backend.auth.datetime").now.return_value = future_time

    # Validate expired session
    assert validate_session(session_id) is False

    # Verify expired session was removed from store
    assert session_id not in sessions


def test_validate_session_removes_expired_sessions(mocker):
    """Test that validate_session automatically cleans up expired sessions."""
    sessions.clear()

    session_id = create_session()

    # Verify session exists
    assert session_id in sessions

    # Mock datetime to simulate expiry
    future_time = datetime.now(timezone.utc) + timedelta(hours=25)
    mock_datetime = mocker.patch("backend.auth.datetime")
    mock_datetime.now.return_value = future_time

    # Validate expired session
    validate_session(session_id)

    # Verify session was removed
    assert session_id not in sessions


def test_invalidate_session_removes_session():
    """Test that invalidate_session removes session from store."""
    sessions.clear()

    session_id = create_session()

    # Verify session exists
    assert session_id in sessions

    # Invalidate session
    invalidate_session(session_id)

    # Verify session was removed
    assert session_id not in sessions


def test_invalidate_session_handles_nonexistent_session():
    """Test that invalidate_session gracefully handles non-existent session."""
    sessions.clear()

    # Should not raise exception
    invalidate_session("nonexistent_session_id")


# =============================================================================
# REQUIRE_AUTH TESTS
# =============================================================================


def test_require_auth_allows_valid_session():
    """Test that require_auth allows request with valid session."""
    sessions.clear()

    session_id = create_session()

    # Mock request with valid session cookie
    mock_request = Mock()
    mock_request.cookies = {"session_id": session_id}

    # Should not raise exception
    require_auth(mock_request)


def test_require_auth_raises_401_for_missing_session():
    """Test that require_auth raises 401 for missing session cookie."""
    sessions.clear()

    # Mock request without session cookie
    mock_request = Mock()
    mock_request.cookies = {}

    # Should raise 401 HTTPException
    with pytest.raises(HTTPException) as exc_info:
        require_auth(mock_request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail == "Unauthorized"


def test_require_auth_raises_401_for_invalid_session():
    """Test that require_auth raises 401 for invalid session ID."""
    sessions.clear()

    # Mock request with invalid session cookie
    mock_request = Mock()
    mock_request.cookies = {"session_id": "invalid_session_id"}

    # Should raise 401 HTTPException
    with pytest.raises(HTTPException) as exc_info:
        require_auth(mock_request)

    assert exc_info.value.status_code == 401


def test_require_auth_raises_401_for_expired_session(mocker):
    """Test that require_auth raises 401 for expired session."""
    sessions.clear()

    session_id = create_session()

    # Mock datetime to simulate expiry
    future_time = datetime.now(timezone.utc) + timedelta(hours=25)
    mocker.patch("backend.auth.datetime").now.return_value = future_time

    # Mock request with expired session
    mock_request = Mock()
    mock_request.cookies = {"session_id": session_id}

    # Should raise 401 HTTPException
    with pytest.raises(HTTPException) as exc_info:
        require_auth(mock_request)

    assert exc_info.value.status_code == 401


# =============================================================================
# UTC TIMESTAMP TESTS (TIER 1 Rule 3)
# =============================================================================


def test_create_session_uses_utc_timestamps():
    """Test that create_session uses UTC timezone for all timestamps."""
    sessions.clear()

    session_id = create_session()
    session = sessions[session_id]

    # Verify both timestamps have UTC timezone
    assert session["created_at"].tzinfo == timezone.utc
    assert session["expires_at"].tzinfo == timezone.utc


def test_validate_session_uses_utc_for_expiry_check(mocker):
    """Test that validate_session uses UTC for expiry comparisons."""
    sessions.clear()

    session_id = create_session()

    # Mock datetime.now to return a specific UTC time
    mock_now = datetime.now(timezone.utc) + timedelta(hours=1)
    mock_datetime = mocker.patch("backend.auth.datetime")
    mock_datetime.now.return_value = mock_now

    # Validate session (should still be valid)
    result = validate_session(session_id)

    # Verify datetime.now was called with timezone.utc
    mock_datetime.now.assert_called_with(timezone.utc)
    assert result is True
