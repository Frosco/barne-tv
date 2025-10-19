"""
Session management and authentication for admin interface.

TIER 1 Rule 4: Admin passwords must use bcrypt hashing via passlib
TIER 1 Rule 3: Always use UTC for timestamps
TIER 2 Rule 10: Session validation must use centralized helper
"""

import secrets
from datetime import datetime, timezone, timedelta
from fastapi import Request, HTTPException
from passlib.hash import bcrypt


# In-memory session store
# Sessions lost on application restart (acceptable for single-family deployment)
sessions = {}  # session_id -> {created_at: datetime, expires_at: datetime}


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt with automatic salt generation.

    TIER 1 Rule 4: Must use bcrypt hashing via passlib.

    Args:
        password: Plain text password

    Returns:
        Bcrypt hash string (format: '$2b$12$...', 60 characters)

    Example:
        hashed = hash_password("admin_password_123")
        # Returns: '$2b$12$...' (60 chars)
    """
    return bcrypt.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a bcrypt hash.

    TIER 1 Rule 4: Must use bcrypt hashing via passlib.

    Args:
        plain_password: Plain text password from user
        hashed_password: Bcrypt hashed password from database

    Returns:
        True if password matches, False otherwise

    Example:
        stored_hash = '$2b$12$...'
        is_valid = verify_password("admin_password_123", stored_hash)
    """
    return bcrypt.verify(plain_password, hashed_password)


def create_session() -> str:
    """
    Create new admin session with 24-hour expiry.

    TIER 1 Rule 3: Always use UTC for timestamps.

    Returns:
        Session ID (32-byte URL-safe token = 256-bit entropy)

    Example:
        session_id = create_session()
        # Returns: 'aBcD1234...' (43 chars, URL-safe base64)
    """
    # TIER 1 Rule 3: Always use UTC
    now = datetime.now(timezone.utc)

    # Generate cryptographically secure session ID
    session_id = secrets.token_urlsafe(32)  # 32 bytes = 256 bits of entropy

    # Store session with 24-hour expiry
    sessions[session_id] = {
        "created_at": now,
        "expires_at": now + timedelta(hours=24),
    }

    return session_id


def validate_session(session_id: str) -> bool:
    """
    Validate session exists and hasn't expired.

    Automatically removes expired sessions for cleanup.

    TIER 1 Rule 3: Always use UTC for timestamp comparisons.

    Args:
        session_id: Session ID from cookie

    Returns:
        True if session is valid and not expired, False otherwise

    Example:
        session_id = request.cookies.get('session_id')
        if validate_session(session_id):
            # Allow access
        else:
            # Deny access
    """
    if session_id not in sessions:
        return False

    session = sessions[session_id]

    # TIER 1 Rule 3: Always use UTC
    if datetime.now(timezone.utc) > session["expires_at"]:
        # Session expired - remove it
        del sessions[session_id]
        return False

    return True


def invalidate_session(session_id: str) -> None:
    """
    Remove session from store (used for logout).

    Args:
        session_id: Session ID to invalidate

    Example:
        session_id = request.cookies.get('session_id')
        invalidate_session(session_id)
    """
    sessions.pop(session_id, None)


def require_auth(request: Request) -> None:
    """
    Require authentication for admin routes (FastAPI dependency).

    TIER 2 Rule 10: Centralized session validation helper.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 401 if session invalid or missing

    Usage:
        @app.get("/admin/sources")
        def list_sources(request: Request):
            require_auth(request)
            # Protected logic here
    """
    session_id = request.cookies.get("session_id")
    if not session_id or not validate_session(session_id):
        raise HTTPException(status_code=401, detail="Unauthorized")
