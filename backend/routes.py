"""
API route definitions for Safe YouTube Viewer.

All routes will be defined here in a single file.

TIER 2 Rule 12: API responses must use consistent structure
"""

import json
import logging
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from backend.auth import (
    create_session,
    invalidate_session,
    require_auth,
    verify_password,
)
from backend.db.queries import get_setting

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class LoginRequest(BaseModel):
    """Request model for admin login."""

    password: str


# =============================================================================
# ADMIN AUTHENTICATION ROUTES (Story 1.4)
# =============================================================================


@router.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    """
    Serve admin login page.

    Args:
        request: FastAPI Request object (for accessing app state)

    Returns:
        HTML response with login template
    """
    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/login.html",
        {
            "request": request,
            "interface": "admin",
            "dev_mode": True,  # TODO: Use config.DEBUG in production
        },
    )


@router.post("/admin/login")
def admin_login(login_data: LoginRequest, response: Response):
    """
    Admin login endpoint with password authentication.

    TIER 1 Rules Applied:
    - Rule 4: Use bcrypt for password verification
    - Rule 5: Validate input (password field required by Pydantic)
    - Rule 6: SQL placeholders (via get_setting function)

    TIER 2 Rules Applied:
    - Rule 10: Use centralized auth helper (create_session)
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error messages for users.

    Args:
        login_data: LoginRequest with password field
        response: FastAPI Response object for setting cookies

    Returns:
        Success: {"success": true, "redirect": "/admin/dashboard"}
        Error: 401 with {"error": "Invalid password", "message": "Feil passord"}

    Example:
        POST /admin/login
        Body: {"password": "admin_password_123"}
        Response: {"success": true, "redirect": "/admin/dashboard"}
        Sets-Cookie: session_id=...; HttpOnly; Secure; SameSite=Lax
    """
    try:
        # Get admin password hash from settings table
        password_hash_json = get_setting("admin_password_hash")
        stored_hash = json.loads(password_hash_json)  # Unwrap JSON encoding

        # TIER 1 Rule 4: Verify password using bcrypt
        if not verify_password(login_data.password, stored_hash):
            # Log failed login attempt
            logger.warning("Failed login attempt")
            # TIER 3 Rule 14: Norwegian error message
            raise HTTPException(
                status_code=401,
                detail={"error": "Invalid password", "message": "Feil passord"},
            )

        # Create session and set secure cookie
        session_id = create_session()

        # TIER 2 Rule 10: Set secure cookie attributes
        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,  # Prevent JavaScript access (XSS protection)
            secure=True,  # HTTPS only in production
            samesite="lax",  # CSRF protection
            max_age=86400,  # 24 hours in seconds
        )

        logger.info("Successful admin login")

        # TIER 2 Rule 12: Consistent response structure
        return {"success": True, "redirect": "/admin/dashboard"}

    except KeyError:
        # Admin password not set in database
        logger.error("admin_password_hash setting not found in database")
        raise HTTPException(
            status_code=500,
            detail={"error": "Server error", "message": "Noe gikk galt"},
        )


@router.post("/admin/logout")
def admin_logout(request: Request, response: Response):
    """
    Admin logout endpoint - invalidates session and clears cookie.

    TIER 2 Rule 10: Use centralized auth helper (require_auth, invalidate_session).
    TIER 2 Rule 12: Consistent API response structure.

    Args:
        request: FastAPI Request object for reading cookies
        response: FastAPI Response object for clearing cookies

    Returns:
        {"success": true, "redirect": "/admin/login"}

    Example:
        POST /admin/logout
        Response: {"success": true, "redirect": "/admin/login"}
        Clears session_id cookie
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    # Get session ID and invalidate it
    session_id = request.cookies.get("session_id")
    if session_id:
        invalidate_session(session_id)

    # Clear session cookie
    response.delete_cookie(key="session_id")

    logger.info("Admin logout successful")

    # TIER 2 Rule 12: Consistent response structure
    return {"success": True, "redirect": "/admin/login"}


# Routes will be added in future stories
# Example structure:
# @router.get("/api/videos")
# async def get_videos():
#     return {"success": True, "videos": []}
