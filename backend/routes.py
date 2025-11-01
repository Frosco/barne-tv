"""
API route definitions for Safe YouTube Viewer.

All routes will be defined here in a single file.

TIER 2 Rule 12: API responses must use consistent structure
"""

import json
import logging
from fastapi import APIRouter, Request, Response, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from googleapiclient.errors import HttpError

from backend.auth import (
    create_session,
    invalidate_session,
    require_auth,
    verify_password,
)
from backend.db.queries import (
    get_connection,
    get_setting,
    insert_watch_history,
    update_video_availability,
)
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


class WatchVideoRequest(BaseModel):
    """Request model for logging video watch (Story 2.2, extended in Story 3.1)."""

    videoId: str
    completed: bool
    durationWatchedSeconds: int
    manualPlay: bool = False  # Story 3.1: defaults to False for normal child playback


class VideoUnavailableRequest(BaseModel):
    """Request model for marking video unavailable (Story 2.2)."""

    videoId: str


class ReplayVideoRequest(BaseModel):
    """Request model for manual video replay (Story 3.1)."""

    videoId: str


class UpdateSettingsRequest(BaseModel):
    """Request model for updating settings (Story 3.2).

    Supports partial updates - all fields optional.
    TIER 1 Rule 5: Pydantic validation enforces ranges.
    """

    daily_limit_minutes: int | None = Field(None, ge=5, le=180)
    grid_size: int | None = Field(None, ge=4, le=15)
    audio_enabled: bool | None = None


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


@router.get("/admin/dashboard", response_class=HTMLResponse)
@limiter.limit("100/minute")
def admin_dashboard_page(request: Request, response: Response):
    """
    Serve admin dashboard page with navigation to all admin sections.

    TIER 2 Rule 10: Require authentication.

    Args:
        request: FastAPI Request object (for auth and templates)
        response: FastAPI Response object

    Returns:
        HTML response with dashboard template
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/dashboard.html",
        {
            "request": request,
            "interface": "admin",
        },
    )


# =============================================================================
# CHANNEL MANAGEMENT ROUTES (Story 1.5)
# =============================================================================


@router.get("/admin/channels", response_class=HTMLResponse)
@limiter.limit("100/minute")
def admin_channels_page(request: Request, response: Response):
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
def add_source(request: Request, response: Response, source_data: AddSourceRequest):
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
def remove_source(request: Request, response: Response, source_id: int):
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
def refresh_source(request: Request, response: Response, source_id: int):
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
def child_grid_page(request: Request, response: Response):
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


# =============================================================================
# VIDEO PLAYBACK TRACKING (Story 2.2)
# =============================================================================


@router.post("/api/videos/watch")
@limiter.limit("100/minute")
def log_video_watch(request: Request, response: Response, data: WatchVideoRequest):
    """
    Log that a video was watched (completed or partial).

    Called when video ends naturally or when Back button pressed.
    NOT called when ESC key pressed (cancelled playback).

    **Story 3.1 Addition:** Now accepts optional manualPlay parameter.
    When manualPlay=True, video does NOT count toward daily limit.

    TIER 1 Rules Applied:
    - Rule 2: manual_play and grace_play flags control limit counting
    - Rule 3: UTC timestamp recorded server-side (insert_watch_history uses datetime.now(timezone.utc))
    - Rule 5: Validate all inputs (videoId format, durationWatchedSeconds range)
    - Rule 6: SQL placeholders used in database layer

    TIER 2 Rules Applied:
    - Rule 7: Context manager used in database layer
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error messages for users.

    Args:
        request: FastAPI Request object (for rate limiting)
        data: WatchVideoRequest with videoId, completed, durationWatchedSeconds, manualPlay (optional)

    Returns:
        Success (200): {
            "success": true,
            "dailyLimit": {
                "date": "2025-01-03",
                "minutesWatched": 19,
                "minutesRemaining": 11,
                "currentState": "winddown",
                "resetTime": "2025-01-04T00:00:00Z"
            }
        }
        Error (400): {"error": "Invalid parameter", "message": "..."}
        Error (500): {"error": "Internal error", "message": "Noe gikk galt"}

    Example:
        POST /api/videos/watch
        Body: {"videoId": "dQw4w9WgXcQ", "completed": true, "durationWatchedSeconds": 212}
        Response: {"success": true, "dailyLimit": {...}}
    """
    # TIER 1 Rule 5: Validate input parameters
    if not data.videoId or len(data.videoId) != 11:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid parameter",
                "message": "Video ID må være 11 tegn",
            },
        )

    if data.durationWatchedSeconds < 0:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid parameter",
                "message": "Varighet kan ikke være negativ",
            },
        )

    try:
        # Insert watch history record
        # TIER 1 Rule 2: manual_play flag controls limit counting (Story 3.1)
        # TIER 1 Rule 3: UTC timestamp recorded server-side
        insert_watch_history(
            video_id=data.videoId,
            completed=data.completed,
            duration_watched_seconds=data.durationWatchedSeconds,
            manual_play=data.manualPlay,  # Story 3.1: Pass from request (default False)
            grace_play=False,  # Still hardcoded - grace logic is separate
        )

        # Get updated daily limit state
        daily_limit = viewing_session.get_daily_limit()

        # TIER 2 Rule 12: Consistent response structure
        return {"success": True, "dailyLimit": daily_limit}

    except Exception as e:
        # Generic error handler
        # TIER 3 Rule 14: Norwegian error message
        logger.error(f"Unexpected error logging video watch: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


@router.post("/api/videos/unavailable")
@limiter.limit("100/minute")
def mark_video_unavailable(request: Request, response: Response, data: VideoUnavailableRequest):
    """
    Mark video as unavailable globally (all duplicate instances).

    Called when YouTube returns error codes 100 or 150 (video not found/embedding restricted).

    TIER 1 Rules Applied:
    - Rule 1: Updates ALL duplicate video instances globally (is_available flag)
    - Rule 5: Validate input (videoId format)
    - Rule 6: SQL placeholders used in database layer

    TIER 2 Rules Applied:
    - Rule 7: Context manager used in database layer
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error messages for users.

    Args:
        request: FastAPI Request object (for rate limiting)
        data: VideoUnavailableRequest with videoId

    Returns:
        Success (200): {"success": true}
        Error (400): {"error": "Invalid parameter", "message": "..."}
        Error (500): {"error": "Internal error", "message": "Noe gikk galt"}

    Example:
        POST /api/videos/unavailable
        Body: {"videoId": "dQw4w9WgXcQ"}
        Response: {"success": true}
    """
    # TIER 1 Rule 5: Validate input parameter
    if not data.videoId or len(data.videoId) != 11:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid parameter",
                "message": "Video ID må være 11 tegn",
            },
        )

    try:
        # Mark video unavailable globally
        # TIER 1 Rule 1: Updates ALL duplicate instances
        rows_updated = update_video_availability(video_id=data.videoId, is_available=False)

        logger.info(
            f"Marked video {data.videoId} as unavailable ({rows_updated} instances updated)"
        )

        # TIER 2 Rule 12: Consistent response structure
        return {"success": True}

    except Exception as e:
        # Generic error handler
        # TIER 3 Rule 14: Norwegian error message
        logger.error(f"Unexpected error marking video unavailable: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


# =============================================================================
# ADMIN HISTORY ROUTES (Story 3.1)
# =============================================================================


@router.get("/admin/api/history")
@limiter.limit("100/minute")
def get_admin_history(
    request: Request,
    response: Response,
    limit: int = 50,
    offset: int = 0,
    date_from: str | None = None,
    date_to: str | None = None,
    channel: str | None = None,
    search: str | None = None,
):
    """
    Get paginated watch history with optional filters.

    TIER 1 Rules Applied:
    - Rule 3: UTC timestamps stored, returned as ISO 8601
    - Rule 6: SQL placeholders for all filter parameters

    TIER 2 Rules Applied:
    - Rule 10: Require authentication via require_auth()
    - Rule 12: Consistent API response structure

    Args:
        request: FastAPI Request object for authentication
        limit: Number of entries per page (default 50)
        offset: Offset for pagination (default 0)
        date_from: Start date filter YYYY-MM-DD (optional)
        date_to: End date filter YYYY-MM-DD (optional)
        channel: Channel name filter (optional)
        search: Title search term (optional)

    Returns:
        {
            "history": [
                {
                    "id": 1,
                    "videoId": "dQw4w9WgXcQ",
                    "videoTitle": "Excavator Song",
                    "channelName": "Blippi",
                    "thumbnailUrl": "https://i.ytimg.com/vi/dQw4w9WgXcQ/default.jpg",
                    "watchedAt": "2025-10-29T14:30:00Z",
                    "completed": true,
                    "manualPlay": false,
                    "gracePlay": false,
                    "durationWatchedSeconds": 245
                }
            ],
            "total": 150
        }
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Build WHERE clause with filters (TIER 1 Rule 6: Use SQL placeholders)
        where_conditions = ["1=1"]
        params = []

        # Date range filter
        if date_from:
            where_conditions.append("DATE(h.watched_at) >= ?")
            params.append(date_from)

        if date_to:
            where_conditions.append("DATE(h.watched_at) <= ?")
            params.append(date_to)

        # Channel filter
        if channel:
            where_conditions.append("h.channel_name = ?")
            params.append(channel)

        # Search filter (case-insensitive)
        if search:
            where_conditions.append("h.video_title LIKE ? COLLATE NOCASE")
            params.append(f"%{search}%")

        where_clause = " AND ".join(where_conditions)

        # Build count query (for pagination total)
        count_query = f"""
            SELECT COUNT(*)
            FROM watch_history h
            WHERE {where_clause}
        """

        # Build main query
        query = f"""
            SELECT h.*,
                   COALESCE(v.thumbnail_url,
                            'https://i.ytimg.com/vi/' || h.video_id || '/default.jpg') as thumbnail_url
            FROM watch_history h
            LEFT JOIN videos v ON v.video_id = h.video_id
            WHERE {where_clause}
            ORDER BY h.watched_at DESC
            LIMIT ? OFFSET ?
        """

        with get_connection() as conn:
            # Get total count
            total_result = conn.execute(count_query, tuple(params)).fetchone()
            total = int(total_result[0]) if total_result else 0

            # Get paginated results
            params_with_pagination = params + [limit, offset]
            results = conn.execute(query, tuple(params_with_pagination)).fetchall()

            # Convert to response format (camelCase for frontend)
            history = []
            for row in results:
                history.append(
                    {
                        "id": row["id"],
                        "videoId": row["video_id"],
                        "videoTitle": row["video_title"],
                        "channelName": row["channel_name"],
                        "thumbnailUrl": row["thumbnail_url"],
                        "watchedAt": row["watched_at"],
                        "completed": bool(row["completed"]),
                        "manualPlay": bool(row["manual_play"]),
                        "gracePlay": bool(row["grace_play"]),
                        "durationWatchedSeconds": row["duration_watched_seconds"],
                    }
                )

            # TIER 2 Rule 12: Consistent response structure
            return {"history": history, "total": total}

    except Exception as e:
        logger.error(f"Error fetching admin history: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


@router.post("/admin/history/replay")
@limiter.limit("100/minute")
def replay_video(request: Request, response: Response, data: ReplayVideoRequest):
    """
    Prepare video for manual replay by admin.

    Returns embed URL without logging to history yet.
    History will be logged when video completes via modified /api/videos/watch endpoint.

    TIER 1 Rules Applied:
    - Rule 5: Validate videoId format (11 characters)

    TIER 2 Rules Applied:
    - Rule 10: Require authentication via require_auth()
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error messages for users.

    Args:
        request: FastAPI Request object for authentication
        data: ReplayVideoRequest with videoId field

    Returns:
        Success (200): {
            "success": true,
            "videoId": "dQw4w9WgXcQ",
            "embedUrl": "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&rel=0&modestbranding=1"
        }
        Error (400): {"error": "Invalid parameter", "message": "Ugyldig video-ID"}
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    # TIER 1 Rule 5: Validate videoId format
    video_id = data.videoId

    if not video_id or len(video_id) != 11:
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid parameter", "message": "Video-ID må være 11 tegn"},
        )

    # Validate character set (alphanumeric, dash, underscore)
    if not all(c.isalnum() or c in "-_" for c in video_id):
        return JSONResponse(
            status_code=400,
            content={"error": "Invalid parameter", "message": "Ugyldig video-ID format"},
        )

    # Construct YouTube embed URL
    embed_url = f"https://www.youtube.com/embed/{video_id}?autoplay=1&rel=0&modestbranding=1"

    logger.info(f"Admin replay request for video {video_id}")

    # TIER 2 Rule 12: Consistent response structure
    return {"success": True, "videoId": video_id, "embedUrl": embed_url}


@router.get("/admin/history", response_class=HTMLResponse)
@limiter.limit("100/minute")
def admin_history_page(request: Request, response: Response):
    """
    Serve admin history page.

    TIER 2 Rule 10: Require authentication via require_auth().

    Args:
        request: FastAPI Request object for accessing app state and authentication

    Returns:
        HTML response with history template
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/history.html",
        {
            "request": request,
            "interface": "admin",
            "dev_mode": True,  # TODO: Use config.DEBUG in production
        },
    )


# =============================================================================
# ADMIN SETTINGS ROUTES (Story 3.2)
# =============================================================================


@router.get("/admin/settings", response_class=HTMLResponse)
@limiter.limit("100/minute")
def admin_settings_page(request: Request, response: Response):
    """
    Serve admin settings configuration page.

    TIER 2 Rule 10: Require authentication via require_auth().

    Args:
        request: FastAPI Request object for accessing app state and authentication
        response: FastAPI Response object

    Returns:
        HTML response with settings template
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    templates = request.app.state.templates
    return templates.TemplateResponse(
        "admin/settings.html",
        {
            "request": request,
            "interface": "admin",
            "dev_mode": True,  # TODO: Use config.DEBUG in production
        },
    )


@router.get("/api/admin/settings")
@limiter.limit("100/minute")
def get_settings(request: Request):
    """
    Get current application settings (Story 3.2).

    TIER 1 Rules Applied:
    - Rule 3: UTC time handling via get_setting()
    - Rule 4: NEVER return admin_password_hash (security)
    - Rule 6: SQL placeholders via get_setting()

    TIER 2 Rules Applied:
    - Rule 10: Require authentication via require_auth()
    - Rule 12: Consistent API response structure

    Args:
        request: FastAPI Request object for authentication

    Returns:
        JSON with settings dict containing:
        - daily_limit_minutes (int): 5-180
        - grid_size (int): 4-15
        - audio_enabled (bool): true/false

    Example:
        GET /api/admin/settings
        Response: {
            "settings": {
                "daily_limit_minutes": 30,
                "grid_size": 9,
                "audio_enabled": true
            }
        }
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Fetch settings from database (JSON-encoded strings)
        # TIER 1 Rule 6: SQL placeholders via get_setting()
        daily_limit_str = get_setting("daily_limit_minutes")
        grid_size_str = get_setting("grid_size")
        audio_enabled_str = get_setting("audio_enabled")

        # Parse JSON-encoded values
        daily_limit = int(daily_limit_str)
        grid_size = int(grid_size_str)
        audio_enabled = audio_enabled_str == "true"

        # TIER 2 Rule 12: Consistent response structure
        # TIER 1 Rule 4: NEVER return admin_password_hash
        return JSONResponse(
            content={
                "settings": {
                    "daily_limit_minutes": daily_limit,
                    "grid_size": grid_size,
                    "audio_enabled": audio_enabled,
                }
            }
        )

    except KeyError as e:
        logger.error(f"Settings key not found: {e}")
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )
    except Exception as e:
        logger.error(f"Error fetching settings: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


@router.put("/api/admin/settings")
@limiter.limit("100/minute")
def update_settings(request: Request, data: UpdateSettingsRequest):
    """
    Update application settings (partial update supported) (Story 3.2).

    TIER 1 Rules Applied:
    - Rule 3: UTC time via set_setting()
    - Rule 5: Pydantic validation enforces ranges (5-180, 4-15)
    - Rule 6: SQL placeholders via set_setting()

    TIER 2 Rules Applied:
    - Rule 10: Require authentication
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian success message

    Args:
        request: FastAPI Request object for authentication
        data: UpdateSettingsRequest with optional fields for partial update

    Returns:
        Success: {
            "success": true,
            "settings": {...updated values...},
            "message": "Innstillinger lagret"
        }
        Error: 422 (validation), 500 (internal)

    Example:
        PUT /api/admin/settings
        Body: {"daily_limit_minutes": 45}
        Response: {
            "success": true,
            "settings": {
                "daily_limit_minutes": 45,
                "grid_size": 9,
                "audio_enabled": true
            },
            "message": "Innstillinger lagret"
        }
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Import set_setting here (it's in queries module)
        from backend.db.queries import set_setting

        # Partial update: only update provided fields
        # TIER 1 Rule 3: UTC time handled by set_setting()
        # TIER 1 Rule 6: SQL placeholders handled by set_setting()
        if data.daily_limit_minutes is not None:
            set_setting("daily_limit_minutes", str(data.daily_limit_minutes))

        if data.grid_size is not None:
            set_setting("grid_size", str(data.grid_size))

        if data.audio_enabled is not None:
            # JSON-encode boolean as 'true'/'false' string
            set_setting("audio_enabled", "true" if data.audio_enabled else "false")

        # Fetch updated settings to return
        daily_limit = int(get_setting("daily_limit_minutes"))
        grid_size = int(get_setting("grid_size"))
        audio_enabled = get_setting("audio_enabled") == "true"

        logger.info("Settings updated successfully")

        # TIER 2 Rule 12: Consistent response structure
        # TIER 3 Rule 14: Norwegian success message
        return JSONResponse(
            content={
                "success": True,
                "settings": {
                    "daily_limit_minutes": daily_limit,
                    "grid_size": grid_size,
                    "audio_enabled": audio_enabled,
                },
                "message": "Innstillinger lagret",
            }
        )

    except Exception as e:
        logger.error(f"Error updating settings: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


@router.post("/api/admin/settings/reset")
@limiter.limit("100/minute")
def reset_settings(request: Request):
    """
    Reset all settings to default values (Story 3.2).

    CRITICAL: NEVER reset admin_password_hash (security requirement).

    TIER 1 Rules Applied:
    - Rule 3: UTC time via set_setting()
    - Rule 4: NEVER reset admin password (security)
    - Rule 6: SQL placeholders via set_setting()

    TIER 2 Rules Applied:
    - Rule 10: Require authentication
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian success message

    Args:
        request: FastAPI Request object for authentication

    Returns:
        Success: {
            "success": true,
            "settings": {...default values...},
            "message": "Innstillinger tilbakestilt"
        }

    Example:
        POST /api/admin/settings/reset
        Response: {
            "success": true,
            "settings": {
                "daily_limit_minutes": 30,
                "grid_size": 9,
                "audio_enabled": true
            },
            "message": "Innstillinger tilbakestilt"
        }
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Import set_setting here (it's in queries module)
        from backend.db.queries import set_setting

        # Reset to defaults (from schema.sql initial values)
        # TIER 1 Rule 3: UTC time handled by set_setting()
        # TIER 1 Rule 6: SQL placeholders handled by set_setting()
        set_setting("daily_limit_minutes", "30")
        set_setting("grid_size", "9")
        set_setting("audio_enabled", "true")

        # TIER 1 Rule 4: NEVER reset admin_password_hash

        logger.info("Settings reset to defaults")

        # TIER 2 Rule 12: Consistent response structure
        # TIER 3 Rule 14: Norwegian success message
        return JSONResponse(
            content={
                "success": True,
                "settings": {"daily_limit_minutes": 30, "grid_size": 9, "audio_enabled": True},
                "message": "Innstillinger tilbakestilt",
            }
        )

    except Exception as e:
        logger.error(f"Error resetting settings: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )


# =============================================================================
# DAILY LIMIT ROUTES (Story 4.1)
# =============================================================================


@router.get("/api/limit/status")
@limiter.limit("100/minute")
def get_limit_status(request: Request, response: Response):
    """
    Get current daily limit status for child interface.

    No authentication required - child interface is public.

    TIER 1 Rules Applied:
    - Rule 2: Minutes calculation excludes manual_play and grace_play (via get_daily_limit)
    - Rule 3: UTC timezone for all date operations (via get_daily_limit)

    TIER 2 Rules Applied:
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian error messages for users.

    Returns:
        Success (200): {
            "date": "2025-01-03",
            "minutesWatched": 15,
            "minutesRemaining": 15,
            "currentState": "normal|winddown|grace|locked",
            "resetTime": "2025-01-04T00:00:00Z"
        }
        Error (503): {"error": "ServiceUnavailable", "message": "Kunne ikke hente daglig grense"}

    Example:
        GET /api/limit/status
        Response: {
            "date": "2025-01-03",
            "minutesWatched": 15,
            "minutesRemaining": 15,
            "currentState": "normal",
            "resetTime": "2025-01-04T00:00:00Z"
        }
    """
    try:
        # Get daily limit state from viewing session service
        # TIER 1 Rule 2: Excludes manual_play and grace_play from calculations
        # TIER 1 Rule 3: Uses UTC for all date operations
        daily_limit = viewing_session.get_daily_limit()

        # TIER 2 Rule 12: Consistent response structure (return dict directly)
        return daily_limit

    except KeyError as e:
        # Handle missing daily_limit_minutes setting gracefully
        # Task 1 requirement: Fall back to 30 minutes default
        logger.warning(f"daily_limit_minutes setting not found, using default 30: {e}")

        # Return default state with 30 minute limit
        from datetime import datetime, timezone, timedelta

        current_time = datetime.now(timezone.utc)
        today = current_time.date().isoformat()
        tomorrow = current_time.date() + timedelta(days=1)
        reset_time = datetime.combine(tomorrow, datetime.min.time(), tzinfo=timezone.utc)

        return {
            "date": today,
            "minutesWatched": 0,
            "minutesRemaining": 30,
            "currentState": "normal",
            "resetTime": reset_time.isoformat().replace("+00:00", "Z"),
        }

    except Exception as e:
        # Database connection failure or other error
        # TIER 3 Rule 14: Norwegian error message
        logger.error(f"Error fetching daily limit status: {e}", exc_info=True)
        return JSONResponse(
            status_code=503,
            content={
                "error": "ServiceUnavailable",
                "message": "Kunne ikke hente daglig grense",
            },
        )


@router.post("/admin/limit/reset")
@limiter.limit("100/minute")
def reset_limit(request: Request, response: Response):
    """
    Reset today's daily limit (deletes countable watch history entries).

    TIER 1 Rules Applied:
    - Rule 2: Only deletes manual_play=0 AND grace_play=0 (preserves parent/grace entries)
    - Rule 3: UTC timezone for all date operations (via reset_daily_limit)

    TIER 2 Rules Applied:
    - Rule 10: Require authentication via require_auth()
    - Rule 12: Consistent API response structure

    TIER 3 Rule 14: Norwegian success message.

    Args:
        request: FastAPI Request object for authentication
        response: FastAPI Response object

    Returns:
        Success (200): {
            "success": true,
            "message": "Daglig grense tilbakestilt",
            "newLimit": {
                "date": "2025-01-03",
                "minutesWatched": 0,
                "minutesRemaining": 30,
                "currentState": "normal",
                "resetTime": "2025-01-04T00:00:00Z"
            }
        }
        Error (401): Unauthorized (no valid session)
        Error (500): {"error": "Internal error", "message": "Noe gikk galt"}

    Example:
        POST /admin/limit/reset
        Response: {
            "success": true,
            "message": "Daglig grense tilbakestilt",
            "newLimit": {...}
        }
    """
    # TIER 2 Rule 10: Require authentication
    require_auth(request)

    try:
        # Call service layer to reset daily limit
        # TIER 1 Rule 2: Only deletes countable entries (preserves manual/grace)
        # TIER 1 Rule 3: Uses UTC for date operations
        new_limit = viewing_session.reset_daily_limit()

        logger.info("Daily limit reset by admin")

        # TIER 2 Rule 12: Consistent response structure
        # TIER 3 Rule 14: Norwegian success message
        return {
            "success": True,
            "message": "Daglig grense tilbakestilt",
            "newLimit": new_limit,
        }

    except Exception as e:
        # Generic error handler
        # TIER 3 Rule 14: Norwegian error message
        logger.error(f"Error resetting daily limit: {e}", exc_info=True)
        return JSONResponse(
            status_code=500, content={"error": "Internal error", "message": "Noe gikk galt"}
        )
