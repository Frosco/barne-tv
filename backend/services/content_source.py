"""
YouTube channel/playlist management and video fetching.

This module handles:
- Adding new content sources (channels, playlists)
- Fetching videos from YouTube Data API v3
- Refreshing existing sources
- Parsing YouTube URLs
- API quota monitoring (Story 1.2)
- API key validation (Story 1.2)

TIER 1 Rules:
- Rule 3: Always use UTC for timestamps (datetime.now(timezone.utc))
- Rule 5: All inputs must be validated and sanitized
- Rule 6: All SQL queries must use parameterized placeholders
"""

import logging
from datetime import datetime, timezone

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from backend.config import YOUTUBE_API_KEY
from backend.db.queries import get_daily_quota_usage, log_api_call

logger = logging.getLogger(__name__)


# =============================================================================
# YOUTUBE API CLIENT (Story 1.2)
# =============================================================================


def create_youtube_client():
    """
    Create and return YouTube Data API v3 client.

    Returns:
        Resource: YouTube API client from google-api-python-client

    Example:
        youtube = create_youtube_client()
        response = youtube.search().list(q="test", part="id").execute()
    """
    return build("youtube", "v3", developerKey=YOUTUBE_API_KEY)


# =============================================================================
# QUOTA MONITORING (Story 1.2)
# =============================================================================


def is_quota_exceeded() -> bool:
    """
    Check if daily YouTube API quota is exceeded.

    Uses 9,500 units as threshold (500 unit buffer below 10,000 limit).
    This conservative threshold prevents hitting the hard limit mid-operation.

    TIER 1 Rule 3: Uses UTC for date calculation.

    Returns:
        True if quota >= 9500 units, False otherwise

    Example:
        if is_quota_exceeded():
            raise QuotaExceededError("API-kvote overskredet")
    """
    # TIER 1 Rule 3: Always use UTC
    today = datetime.now(timezone.utc).date().isoformat()
    usage = get_daily_quota_usage(today)
    return usage >= 9500


def validate_youtube_api_key() -> bool:
    """
    Validate YouTube API key with minimal test request.

    Makes a search request for "test" with maxResults=1 (1 quota unit).
    Logs the validation result to database for audit trail.

    TIER 1 Rules Applied:
    - Rule 3: UTC timestamps in log_api_call
    - Rule 5: Validates API key before use

    Returns:
        True if API key is valid and working
        False if API key is invalid (HTTP 400/403)

    Raises:
        HttpError: For non-authentication errors (network issues, etc.)

    Example:
        if not validate_youtube_api_key():
            logger.error("Invalid YouTube API key")
            sys.exit(1)
    """
    try:
        youtube = create_youtube_client()

        # Make minimal test request (1 quota unit)
        youtube.search().list(q="test", part="id", maxResults=1).execute()

        # Log successful validation
        log_api_call("youtube_search_validation", 1, True)

        logger.info("YouTube API key validated successfully")
        return True

    except HttpError as e:
        # Handle invalid API key errors
        if e.resp.status in [400, 403]:
            logger.error(f"Invalid YouTube API key: {e}")
            log_api_call("youtube_search_validation", 1, False, str(e))
            return False

        # Re-raise other errors (network issues, server errors, etc.)
        raise


# =============================================================================
# CONTENT SOURCE MANAGEMENT (Future stories)
# =============================================================================


def add_source(source_input: str) -> dict:
    """
    Add a new YouTube channel or playlist as content source.

    Args:
        source_input: YouTube URL, channel ID, or playlist ID

    Returns:
        Dictionary with source info and video count

    Raises:
        ValidationError: If input is invalid
        APIError: If YouTube API fails

    TIER 1 Rule 5: Must validate and sanitize all parent inputs
    """
    # Placeholder implementation - will be completed in future story
    return {}


def fetch_videos(source_id: str, source_type: str) -> list[dict]:
    """
    Fetch all videos from a YouTube source.

    Args:
        source_id: YouTube channel ID or playlist ID
        source_type: Either 'channel' or 'playlist'

    Returns:
        List of video dictionaries with metadata

    TIER 2 Rule 8: Must use YouTube API retry helper
    """
    # Placeholder implementation - will be completed in future story
    return []
