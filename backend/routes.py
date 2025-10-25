"""
API route definitions for Safe YouTube Viewer.

All routes will be defined here in a single file.

TIER 2 Rule 12: API responses must use consistent structure
"""

import json
import logging
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel

from googleapiclient.errors import HttpError

from backend.auth import (
    create_session,
    invalidate_session,
    require_auth,
    verify_password,
)
from backend.db.queries import get_setting
from backend.exceptions import QuotaExceededError, NotFoundError, NoVideosAvailableError
from backend.middleware import limiter
from backend.services import content_source, viewing_session

router = APIRouter()
logger = logging.getLogger(__name__)


# =============================================================================
# REQUEST/RESPONSE MODELS
# =============================================================================


class LoginRequest(BaseModel):
    """Request model for admin login."""

    password: str


class AddSourceRequest(BaseModel):
    """Request model for adding content source."""

    input: str


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
@limiter.limit("20/minute")  # More restrictive for login to prevent brute-force
def admin_login(request: Request, login_data: LoginRequest, response: Response):
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
@limiter.limit("100/minute")
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


# =============================================================================
# CHANNEL MANAGEMENT ROUTES (Story 1.5)
# =============================================================================


@router.get("/admin/channels", response_class=HTMLResponse)
@limiter.limit("100/minute")
def admin_channels_page(request: Request):
    """
    Serve admin channel management page.

    Args:
        request: FastAPI Request object for accessing app state

    Returns:
        HTML response with channels template
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/channels.html",
        {
            "request": request,
            "interface": "admin",
            "dev_mode": True,  # TODO: Use config.DEBUG in production
        },
    )


@router.post("/admin/sources")
@limiter.limit("100/minute")
def add_source(request: Request, source_data: AddSourceRequest):
    """
    Add new YouTube channel or playlist as content source.

    TIER 1 Rules Applied:
    - Rule 5: Input validation via content_source.add_source()
    - Rule 6: SQL placeholders via database query functions

    TIER 2 Rules Applied:
    - Rule 10: Require authentication via require_auth()
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error messages for users.

    Args:
        request: FastAPI Request object for authentication
        source_data: AddSourceRequest with input field (URL or ID)

    Returns:
        Success (200): {
            "success": true,
            "source": {...},
            "videosAdded": 487,
            "message": "Kanal lagt til: Blippi (487 videoer)"
        }
        Partial fetch (200): {
            "success": true,
            "partial": true,
            "source": {...},
            "videosAdded": 600,
            "message": "Lagt til 600 videoer (nettverksfeil)...",
            "retryAvailable": true
        }
        Error responses: 409 (duplicate), 400 (invalid), 503 (quota/API error)

    Example:
        POST /admin/sources
        Body: {"input": "https://www.youtube.com/@Blippi"}
        Response: {"success": true, "source": {...}, "videosAdded": 487}
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Call service layer to add source
        result = content_source.add_source(source_data.input)

        # Check if fetch was complete or partial
        fetch_complete = result.get("fetch_complete", True)
        source_name = result["name"]
        video_count = result["video_count"]

        # Convert snake_case to camelCase for frontend
        source_dict = {
            "id": result.get("id"),  # Will be set by database
            "sourceId": result["source_id"],
            "sourceType": result["source_type"],
            "name": source_name,
            "videoCount": video_count,
        }

        if fetch_complete:
            # Complete fetch - success message
            return {
                "success": True,
                "source": source_dict,
                "videosAdded": video_count,
                "message": f"Kanal lagt til: {source_name} ({video_count} videoer)",
            }
        else:
            # Partial fetch - warning message with retry hint
            return {
                "success": True,
                "partial": True,
                "source": source_dict,
                "videosAdded": video_count,
                "message": f"Lagt til {video_count} videoer (nettverksfeil). Klikk 'Oppdater' for å hente resten.",
                "retryAvailable": True,
            }

    except ValueError as e:
        # Handle validation errors (duplicate, invalid input)
        error_msg = str(e)
        logger.warning(f"Validation error adding source: {error_msg}")

        # Check if it's a duplicate error
        if "allerede lagt til" in error_msg:
            return JSONResponse(
                status_code=409, content={"error": "Already exists", "message": error_msg}
            )
        else:
            # Invalid input format
            return JSONResponse(
                status_code=400, content={"error": "Invalid input", "message": error_msg}
            )

    except QuotaExceededError as e:
        # YouTube API quota exceeded
        logger.error(f"Quota exceeded while adding source: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "error": "Quota exceeded",
                "message": "YouTube kvote oppbrukt. Prøv igjen i morgen.",
            },
        )

    except HttpError as e:
        # YouTube API errors
        logger.error(f"YouTube API error while adding source: {e}")

        if e.resp.status == 404:
            return JSONResponse(
                status_code=404, content={"error": "Not found", "message": "Kanal ikke funnet"}
            )
        elif e.resp.status == 403:
            return JSONResponse(
                status_code=503,
                content={
                    "error": "YouTube API error",
                    "message": "YouTube API ikke tilgjengelig",
                },
            )
        else:
            # Generic YouTube API error
            return JSONResponse(
                status_code=503,
                content={
                    "error": "YouTube API error",
                    "message": "YouTube API ikke tilgjengelig",
                },
            )

    except Exception as e:
        # Generic error handler
        logger.error(f"Unexpected error adding source: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


@router.get("/admin/sources")
@limiter.limit("100/minute")
def list_sources(request: Request, response: Response):
    """
    List all content sources (channels and playlists).

    TIER 2 Rules Applied:
    - Rule 10: Require authentication via require_auth()
    - Rule 12: Consistent API response structure

    Args:
        request: FastAPI Request object for authentication

    Returns:
        {"sources": [
            {
                "id": 1,
                "sourceId": "UCrwObTfqv8u1KO7Fgk-FXHQ",
                "sourceType": "channel",
                "name": "Blippi",
                "videoCount": 487,
                "lastRefresh": "2025-10-19T10:15:00Z",
                "fetchMethod": "api",
                "addedAt": "2025-10-19T10:15:00Z"
            }
        ]}

    Example:
        GET /admin/sources
        Response: {"sources": [...]}
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Call service layer to list sources
        sources = content_source.list_sources()

        # TIER 2 Rule 12: Consistent response structure
        return {"sources": sources}

    except Exception as e:
        logger.error(f"Error listing sources: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


@router.delete("/admin/sources/{source_id}")
@limiter.limit("100/minute")
def remove_source(request: Request, source_id: int):
    """
    Remove content source and all its videos.

    CASCADE DELETE automatically removes videos due to foreign key constraint.

    TIER 1 Rule 6: SQL placeholders via delete_content_source().
    TIER 2 Rules Applied:
    - Rule 10: Require authentication via require_auth()
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error and success messages.

    Args:
        request: FastAPI Request object for authentication
        source_id: Primary key ID of content_sources table

    Returns:
        Success (200): {
            "success": true,
            "videosRemoved": 487,
            "message": "Kilde fjernet: Blippi (487 videoer slettet)"
        }
        Error (404): {"error": "Not found", "message": "Kilde ikke funnet"}

    Example:
        DELETE /admin/sources/3
        Response: {"success": true, "videosRemoved": 487}
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Call service layer to remove source
        result = content_source.remove_source(source_id)

        source_name = result["source_name"]
        videos_removed = result["videos_removed"]

        # TIER 2 Rule 12: Consistent response structure
        # TIER 3 Rule 14: Norwegian success message
        return {
            "success": True,
            "videosRemoved": videos_removed,
            "message": f"Kilde fjernet: {source_name} ({videos_removed} videoer slettet)",
        }

    except NotFoundError as e:
        # Source not found
        logger.warning(f"Source not found for deletion: {source_id}")
        return JSONResponse(status_code=404, content={"error": "Not found", "message": str(e)})

    except ValueError as e:
        # Legacy fallback - in case ValueError is raised instead of NotFoundError
        logger.warning(f"Source not found for deletion: {source_id}")
        return JSONResponse(status_code=404, content={"error": "Not found", "message": str(e)})

    except Exception as e:
        logger.error(f"Error removing source {source_id}: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


@router.post("/admin/sources/{source_id}/refresh")
@limiter.limit("100/minute")
def refresh_source(request: Request, source_id: int):
    """
    Refresh content source by fetching new videos.

    Compares fetched videos with existing database videos and inserts only NEW videos.

    TIER 1 Rules Applied:
    - Rule 3: UTC timestamps via content_source.refresh_source()
    - Rule 6: SQL placeholders via database query functions

    TIER 2 Rules Applied:
    - Rule 10: Require authentication via require_auth()
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error and success messages.

    Args:
        request: FastAPI Request object for authentication
        source_id: Primary key ID of content_sources table

    Returns:
        Success (200): {
            "success": true,
            "videosAdded": 12,
            "videosUpdated": 0,
            "lastRefresh": "2025-10-19T14:30:00Z",
            "message": "Oppdatert: 12 nye videoer"
        }
        Error responses: 404 (not found), 503 (quota/API error)

    Example:
        POST /admin/sources/3/refresh
        Response: {"success": true, "videosAdded": 12, "lastRefresh": "..."}
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Call service layer to refresh source
        result = content_source.refresh_source(source_id)

        videos_added = result["videos_added"]

        # TIER 2 Rule 12: Consistent response structure
        # TIER 3 Rule 14: Norwegian success message
        return {
            "success": True,
            "videosAdded": videos_added,
            "videosUpdated": 0,
            "lastRefresh": result["last_refresh"],
            "message": f"Oppdatert: {videos_added} nye videoer",
        }

    except ValueError as e:
        # Source not found or invalid source type
        error_msg = str(e)
        logger.warning(f"Error refreshing source {source_id}: {error_msg}")
        raise HTTPException(status_code=404, detail={"error": "Not found", "message": error_msg})

    except QuotaExceededError as e:
        # YouTube API quota exceeded
        logger.error(f"Quota exceeded while refreshing source {source_id}: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "Quota exceeded",
                "message": "YouTube kvote oppbrukt. Prøv igjen i morgen.",
            },
        )

    except HttpError as e:
        # YouTube API errors
        logger.error(f"YouTube API error while refreshing source {source_id}: {e}")

        if e.resp.status == 404:
            raise HTTPException(
                status_code=404, detail={"error": "Not found", "message": "Kanal ikke funnet"}
            )
        elif e.resp.status == 403:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "YouTube API error",
                    "message": "YouTube API ikke tilgjengelig",
                },
            )
        else:
            # Generic YouTube API error
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "YouTube API error",
                    "message": "YouTube API ikke tilgjengelig",
                },
            )

    except Exception as e:
        logger.error(f"Unexpected error refreshing source {source_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail={"error": "Internal error", "message": "Noe gikk galt"}
        )


# =============================================================================
# CHILD VIEWING ROUTES (Story 2.1)
# =============================================================================


@router.get("/child/grid", response_class=HTMLResponse)
@limiter.limit("100/minute")
def child_grid_page(request: Request):
    """
    Serve child video grid page.

    No authentication required - child interface is public.

    Args:
        request: FastAPI Request object for accessing app state

    Returns:
        HTML response with child grid template
    """
    from backend.config import DEBUG

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "child/grid.html",
        {
            "request": request,
            "interface": "child",
            "dev_mode": DEBUG,
        },
    )


@router.get("/api/videos")
@limiter.limit("100/minute")
def get_videos(request: Request, response: Response, count: int = 9):
    """
    Fetch videos for the child's video grid.

    Uses weighted random selection (60-80% novelty, 20-40% favorites).
    Returns videos and daily limit state.

    TIER 1 Rules Applied:
    - Rule 1: Videos filtered for banned/unavailable (via viewing_session service)
    - Rule 2: Time limits exclude manual_play/grace_play (via get_daily_limit)
    - Rule 3: UTC timezone for all date operations (via service layer)
    - Rule 5: Validate input (count range 4-15)

    TIER 2 Rules Applied:
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error messages for users.

    Args:
        request: FastAPI Request object (for rate limiting)
        count: Number of videos to return (default 9, range 4-15)

    Returns:
        Success (200): {
            "videos": [
                {
                    "videoId": "dQw4w9WgXcQ",
                    "title": "Excavator Song for Kids",
                    "youtubeChannelName": "Blippi",
                    "thumbnailUrl": "https://i.ytimg.com/vi/dQw4w9WgXcQ/hqdefault.jpg",
                    "durationSeconds": 245
                }
            ],
            "dailyLimit": {
                "date": "2025-01-03",
                "minutesWatched": 15,
                "minutesRemaining": 15,
                "currentState": "normal",
                "resetTime": "2025-01-04T00:00:00Z"
            }
        }
        Error (400): {"error": "Invalid parameter", "message": "..."}
        Error (503): {"error": "No videos available", "message": "Ingen videoer tilgjengelig..."}

    Example:
        GET /api/videos?count=9
        Response: {"videos": [...], "dailyLimit": {...}}
    """
    # TIER 1 Rule 5: Validate input parameter
    if not (4 <= count <= 15):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid parameter",
                "message": "Antall videoer må være mellom 4 og 15",
            },
        )

    try:
        # Call service layer to get videos and daily limit
        videos, daily_limit = viewing_session.get_videos_for_grid(count)

        # TIER 2 Rule 12: Consistent response structure
        return {"videos": videos, "dailyLimit": daily_limit}

    except NoVideosAvailableError as e:
        # No videos available (empty database or all filtered out)
        # TIER 3 Rule 14: Norwegian error message
        logger.warning(f"No videos available for grid: {e}")
        return JSONResponse(
            status_code=503,
            content={"error": "No videos available", "message": str(e)},
        )

    except Exception as e:
        # Generic error handler
        logger.error(f"Unexpected error fetching videos for grid: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )
