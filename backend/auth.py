"""
Session management and authentication for admin interface.

TIER 1 Rule 4: Admin passwords must use bcrypt hashing via passlib
TIER 2 Rule 10: Session validation must use centralized helper
"""

from fastapi import Request, HTTPException


def require_auth(request: Request):
    """
    Require authentication for admin routes.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: 401 if not authenticated

    TIER 2 Rule 10: Centralized session validation helper
    """
    # Placeholder implementation - will be completed in future story
    # For now, always raise to prevent unauthenticated access
    raise HTTPException(status_code=401, detail="Authentication required")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a bcrypt hash.

    Args:
        plain_password: Plain text password from user
        hashed_password: Bcrypt hashed password from database

    Returns:
        True if password matches, False otherwise

    TIER 1 Rule 4: Must use bcrypt hashing via passlib
    """
    # Placeholder implementation - will be completed in future story
    from passlib.hash import bcrypt

    return bcrypt.verify(plain_password, hashed_password)
