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
import time
from datetime import datetime, timezone

import isodate  # type: ignore[import-untyped]
from googleapiclient.discovery import build  # type: ignore[import-untyped]
from googleapiclient.errors import HttpError  # type: ignore[import-untyped]

from backend.config import YOUTUBE_API_KEY
from backend.db.queries import (
    bulk_insert_videos,
    delete_content_source,
    get_all_content_sources,
    get_daily_quota_usage,
    get_source_by_id,
    get_source_by_source_id,
    insert_content_source,
    log_api_call,
    update_content_source_refresh,
)
from backend.exceptions import QuotaExceededError

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


def _parse_input(input: str) -> tuple[str, str]:
    """
    Parse YouTube URL and extract source type and ID.

    Supports:
    - Channel URL: https://www.youtube.com/channel/{CHANNEL_ID}
    - Custom URL: https://www.youtube.com/@{HANDLE}
    - Playlist URL: https://www.youtube.com/playlist?list={PLAYLIST_ID}

    Args:
        input: YouTube URL (channel, custom, or playlist)

    Returns:
        Tuple of (source_type, source_id) where:
        - source_type: 'channel' or 'playlist'
        - source_id: Extracted channel ID, handle, or playlist ID

    Raises:
        ValueError: If URL format is invalid (Norwegian message for user)

    TIER 1 Rule 5: Input validation is safety-critical.
    Risk Mitigation (SEC-002): ReDoS protection with length limit.

    Examples:
        >>> _parse_input("https://www.youtube.com/channel/UCrwObTfqv8u1KO7Fgk-FXHQ")
        ('channel', 'UCrwObTfqv8u1KO7Fgk-FXHQ')

        >>> _parse_input("https://www.youtube.com/@Blippi")
        ('channel', 'Blippi')

        >>> _parse_input("https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf")
        ('playlist', 'PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf')
    """
    import re

    # TIER 1 Rule 5: Validate input exists and is string
    if not input or not isinstance(input, str):
        raise ValueError("Ugyldig inndata. Vennligst oppgi en YouTube-lenke.")

    # SEC-002 Risk Mitigation: Enforce maximum length to prevent ReDoS attacks
    MAX_URL_LENGTH = 500
    if len(input) > MAX_URL_LENGTH:
        raise ValueError(
            f"URL er for lang (maks {MAX_URL_LENGTH} tegn). "
            "Vennligst oppgi en gyldig YouTube-lenke."
        )

    # Strip whitespace
    input = input.strip()

    # SEC-002 Risk Mitigation: Simple regex patterns to avoid catastrophic backtracking
    # Note: Using non-greedy quantifiers and specific character classes

    # Channel URL: https://www.youtube.com/channel/{CHANNEL_ID}
    # Channel IDs are typically 24 characters starting with UC
    channel_pattern = r"^https://www\.youtube\.com/channel/([A-Za-z0-9_-]{1,50})(?:[/?]|$)"
    channel_match = re.match(channel_pattern, input)
    if channel_match:
        channel_id = channel_match.group(1)
        logger.info(f"Parsed channel URL: {channel_id}")
        return ("channel", channel_id)

    # Custom URL: https://www.youtube.com/@{HANDLE}
    # Handles can contain letters, numbers, underscores, periods
    custom_pattern = r"^https://www\.youtube\.com/@([A-Za-z0-9_.-]{1,50})(?:[/?]|$)"
    custom_match = re.match(custom_pattern, input)
    if custom_match:
        handle = custom_match.group(1)
        logger.info(f"Parsed custom URL (handle): @{handle}")
        return ("channel", handle)

    # Playlist URL: https://www.youtube.com/playlist?list={PLAYLIST_ID}
    # Playlist IDs vary but are typically alphanumeric with dashes/underscores
    playlist_pattern = r"^https://www\.youtube\.com/playlist\?list=([A-Za-z0-9_-]{1,100})(?:&|$)"
    playlist_match = re.match(playlist_pattern, input)
    if playlist_match:
        playlist_id = playlist_match.group(1)
        logger.info(f"Parsed playlist URL: {playlist_id}")
        return ("playlist", playlist_id)

    # Invalid URL - Norwegian error message (TIER 2 Rule 14)
    logger.warning(f"Failed to parse YouTube URL: {input[:50]}...")
    raise ValueError(
        "Ugyldig YouTube-URL. Vennligst oppgi en gyldig kanal- eller spillelistelenke.\n"
        "Støttede formater:\n"
        "- Kanal: https://www.youtube.com/channel/UCrwObTfqv...\n"
        "- Egendefinert: https://www.youtube.com/@Blippi\n"
        "- Spilleliste: https://www.youtube.com/playlist?list=PLrAXtm..."
    )


def _resolve_handle_to_channel_id(youtube, handle: str) -> str:
    """
    Resolve YouTube handle (@username) to channel ID.

    YouTube handles (like @Blippi) cannot be used directly in search().list()
    API calls which expect channel IDs (UC...). This function resolves the
    handle to the actual channel ID using the channels().list() API with
    the forHandle parameter (added to YouTube API in January 2024).

    Args:
        youtube: YouTube API client
        handle: YouTube handle without @ symbol (e.g., "Blippi", "DerElefant")

    Returns:
        Channel ID string (e.g., "UCrwObTfqv8u1KO7Fgk-FXHQ")

    Raises:
        ValueError: If handle does not resolve to a channel (Norwegian message)
        HttpError: If YouTube API request fails

    TIER 1 Rules Applied:
    - Rule 5: Input validation for handle
    - Rule 6: API responses validated before use

    Example:
        >>> youtube = create_youtube_client()
        >>> channel_id = _resolve_handle_to_channel_id(youtube, "Blippi")
        >>> print(channel_id)
        UCrwObTfqv8u1KO7Fgk-FXHQ
    """
    # TIER 1 Rule 5: Validate input
    if not handle or not isinstance(handle, str):
        raise ValueError("Handle må være en gyldig tekststreng")

    logger.info(f"Resolving handle to channel ID: {handle}")

    try:
        # Call YouTube API to resolve handle to channel ID
        # forHandle parameter added in January 2024
        response = youtube.channels().list(forHandle=handle, part="id", maxResults=1).execute()

        # Log API call for quota tracking (1 quota unit)
        log_api_call("youtube_channels_forHandle", 1, True)

        # TIER 1 Rule 6: Validate API response
        items = response.get("items", [])
        if not items:
            logger.warning(f"Handle not found: {handle}")
            raise ValueError(f"Kanal ikke funnet for handle: @{handle}")

        channel_id = items[0]["id"]
        logger.info(f"Resolved handle {handle} to channel ID: {channel_id}")

        return channel_id

    except HttpError as e:
        # Log failed API call
        log_api_call("youtube_channels_forHandle", 1, False, str(e))

        # Re-raise for upstream handling
        logger.error(f"Failed to resolve handle {handle}: {e}")
        raise


def fetch_videos_with_retry(
    youtube, channel_id: str, page_token: str | None, max_retries: int = 3
) -> tuple[list[str], str | None, bool]:
    """
    Retry individual page fetch with exponential backoff.

    Fetches one page of video IDs from a channel with automatic retry on
    transient network errors. Does NOT retry on quota exceeded (403) or
    not found (404) errors.

    Args:
        youtube: YouTube API client
        channel_id: YouTube channel ID
        page_token: Page token for pagination (None for first page)
        max_retries: Maximum number of retry attempts (default 3)

    Returns:
        Tuple of (video_ids, next_page_token, success) where:
        - video_ids: List of video IDs from this page
        - next_page_token: Token for next page (None if last page)
        - success: True if fetch succeeded, False if all retries failed

    Risk Mitigation (DATA-002): Retry logic handles transient network errors.
    Exponential backoff schedule: 0s, 1s, 2s wait times between retries.

    Example:
        >>> youtube = create_youtube_client()
        >>> videos, next_page, success = fetch_videos_with_retry(youtube, "UC_channel", None)
        >>> if success:
        ...     print(f"Fetched {len(videos)} videos")
    """
    for attempt in range(max_retries):
        try:
            # Fetch one page of videos (50 results max, 100 quota units)
            response = (
                youtube.search()
                .list(
                    channelId=channel_id,
                    part="id",
                    type="video",
                    maxResults=50,
                    pageToken=page_token,
                )
                .execute()
            )

            # Extract video IDs from response
            video_ids = [item["id"]["videoId"] for item in response.get("items", [])]
            next_page = response.get("nextPageToken")

            logger.debug(
                f"Successfully fetched page (attempt {attempt + 1}): "
                f"{len(video_ids)} videos, has_next={bool(next_page)}"
            )

            return (video_ids, next_page, True)

        except HttpError as e:
            # Don't retry on quota exceeded (403) or not found (404)
            if e.resp.status in [403, 404]:
                logger.error(
                    f"Non-retryable error (status {e.resp.status}) for channel {channel_id}: {e}"
                )
                raise

            # Retry on network errors (5xx, timeouts, etc.)
            if attempt < max_retries - 1:
                # Exponential backoff: 0s, 1s, 2s
                wait_time = attempt  # 0, 1, 2
                logger.warning(
                    f"Network error on attempt {attempt + 1}/{max_retries} "
                    f"for channel {channel_id}. Retrying in {wait_time}s... Error: {e}"
                )
                time.sleep(wait_time)
            else:
                # Final attempt failed - return failure
                logger.error(
                    f"All {max_retries} attempts failed for channel {channel_id} page. "
                    "Returning partial fetch."
                )
                return ([], None, False)

    # Should never reach here, but defensive programming
    return ([], None, False)


def fetch_all_channel_videos(youtube, channel_id: str) -> tuple[list[str], bool]:
    """
    Fetch all videos from a channel with full pagination.

    No limits - fetches entire channel history with automatic retry logic.
    Implements safety valve at 100 pages (5000 videos) to prevent infinite loops.

    Args:
        youtube: YouTube API client
        channel_id: YouTube channel ID

    Returns:
        Tuple of (video_ids, fetch_complete) where:
        - video_ids: List of all video IDs fetched
        - fetch_complete: True if all videos fetched, False if partial

    Raises:
        QuotaExceededError: If daily quota exceeded during fetch
        HttpError: For non-retryable errors (404 not found, etc.)

    Risk Mitigation (PERF-002): Checks quota before each API call.
    Risk Mitigation (DATA-002): Returns partial data on network failure.
    Risk Mitigation (TECH-001): Safety valve prevents infinite loops.

    Example:
        >>> youtube = create_youtube_client()
        >>> video_ids, complete = fetch_all_channel_videos(youtube, "UC_channel")
        >>> if complete:
        ...     print(f"Fetched all {len(video_ids)} videos")
        ... else:
        ...     print(f"Partial fetch: {len(video_ids)} videos")
    """
    all_video_ids: list[str] = []
    next_page_token = None
    fetch_complete = True
    page_count = 0
    SAFETY_VALVE_MAX_PAGES = 100  # 5000 videos max (50 per page)

    logger.info(f"Starting full channel fetch for {channel_id}")

    while True:
        page_count += 1

        # Risk Mitigation (TECH-001): Safety valve to prevent infinite loops
        if page_count > SAFETY_VALVE_MAX_PAGES:
            logger.warning(
                f"Safety valve triggered at {SAFETY_VALVE_MAX_PAGES} pages "
                f"({len(all_video_ids)} videos) for channel {channel_id}. "
                "Stopping fetch."
            )
            fetch_complete = False
            break

        # Risk Mitigation (PERF-002): Check quota before each API call
        if is_quota_exceeded():
            logger.error(
                f"Quota exceeded before page {page_count} for channel {channel_id}. "
                f"Fetched {len(all_video_ids)} videos so far."
            )
            fetch_complete = False
            raise QuotaExceededError(
                "YouTube API-kvote overskredet under kanalhenting. " "Noen videoer kan mangle."
            )

        logger.info(
            f"Fetching page {page_count} for channel {channel_id} "
            f"(total so far: {len(all_video_ids)} videos)"
        )

        # Fetch one page with retry logic
        videos, next_page, success = fetch_videos_with_retry(youtube, channel_id, next_page_token)

        # Log API call (100 quota units per search page)
        log_api_call("youtube_search", 100, success)

        if not success:
            # Network error after all retries - return partial fetch
            logger.error(
                f"Failed to fetch page {page_count} after retries for channel {channel_id}. "
                f"Returning partial fetch with {len(all_video_ids)} videos."
            )
            fetch_complete = False
            break

        # Add videos from this page
        all_video_ids.extend(videos)

        # Check if there are more pages
        if not next_page:
            # No more pages - complete fetch
            logger.info(
                f"Completed channel fetch for {channel_id}: "
                f"{len(all_video_ids)} videos across {page_count} pages"
            )
            break

        next_page_token = next_page

    return (all_video_ids, fetch_complete)


def _fetch_playlist_videos(playlist_id: str) -> tuple[list[str], bool]:
    """
    Fetch all videos from a playlist with full pagination.

    No limits - fetches entire playlist with automatic retry logic.
    Uses playlistItems API which is more efficient (1 quota unit per page
    vs 100 for channel search).

    Args:
        playlist_id: YouTube playlist ID

    Returns:
        Tuple of (video_ids, fetch_complete) where:
        - video_ids: List of all video IDs fetched
        - fetch_complete: True if all videos fetched, False if partial

    Raises:
        QuotaExceededError: If daily quota exceeded during fetch
        HttpError: For non-retryable errors (404 not found, etc.)

    Risk Mitigation (PERF-002): Checks quota before each API call.
    Risk Mitigation (DATA-002): Returns partial data on network failure.

    Example:
        >>> video_ids, complete = _fetch_playlist_videos("PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf")
        >>> if complete:
        ...     print(f"Fetched all {len(video_ids)} videos")
    """
    youtube = create_youtube_client()
    all_video_ids: list[str] = []
    next_page_token = None
    fetch_complete = True
    page_count = 0

    logger.info(f"Starting full playlist fetch for {playlist_id}")

    while True:
        page_count += 1

        # Risk Mitigation (PERF-002): Check quota before each API call
        if is_quota_exceeded():
            logger.error(
                f"Quota exceeded before page {page_count} for playlist {playlist_id}. "
                f"Fetched {len(all_video_ids)} videos so far."
            )
            fetch_complete = False
            raise QuotaExceededError(
                "YouTube API-kvote overskredet under spillelistehenting. "
                "Noen videoer kan mangle."
            )

        logger.info(
            f"Fetching page {page_count} for playlist {playlist_id} "
            f"(total so far: {len(all_video_ids)} videos)"
        )

        try:
            # Fetch one page of playlist items (50 results max, 1 quota unit)
            response = (
                youtube.playlistItems()
                .list(
                    playlistId=playlist_id,
                    part="snippet",
                    maxResults=50,
                    pageToken=next_page_token,
                )
                .execute()
            )

            # Extract video IDs from nested structure
            items = response.get("items", [])
            page_video_ids = []
            for item in items:
                try:
                    video_id = item["snippet"]["resourceId"]["videoId"]
                    page_video_ids.append(video_id)
                except KeyError as e:
                    logger.warning(f"Missing field in playlist item: {e}. Skipping item.")
                    continue

            all_video_ids.extend(page_video_ids)

            # Log successful API call (1 quota unit per playlistItems page)
            log_api_call("youtube_playlist_items", 1, True)

            logger.debug(
                f"Successfully fetched playlist page {page_count}: " f"{len(page_video_ids)} videos"
            )

            # Check if there are more pages
            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                # No more pages - complete fetch
                logger.info(
                    f"Completed playlist fetch for {playlist_id}: "
                    f"{len(all_video_ids)} videos across {page_count} pages"
                )
                break

        except HttpError as e:
            # Log failed API call
            log_api_call("youtube_playlist_items", 1, False, str(e))

            # Check for quota exceeded
            if e.resp.status == 403 and "quotaExceeded" in str(e):
                logger.error(f"Quota exceeded during playlist page {page_count}")
                fetch_complete = False
                raise QuotaExceededError("YouTube API-kvote overskredet under spillelistehenting.")

            # Check for not found
            if e.resp.status == 404:
                logger.error(f"Playlist not found: {playlist_id}")
                raise ValueError("Spilleliste ikke funnet")

            # Network error - return partial fetch (no retry for simplicity)
            logger.error(
                f"Failed to fetch playlist page {page_count} for {playlist_id}: {e}. "
                f"Returning partial fetch with {len(all_video_ids)} videos."
            )
            fetch_complete = False
            break

    return (all_video_ids, fetch_complete)


def _fetch_video_details(video_ids: list[str]) -> list[dict]:
    """
    Fetch detailed metadata for a list of video IDs.

    Batches video IDs into groups of 50 (YouTube API limit) and fetches:
    - video_id, title, youtube_channel_id, youtube_channel_name
    - thumbnail_url, duration_seconds, published_at, fetched_at

    Args:
        video_ids: List of YouTube video IDs to fetch details for

    Returns:
        List of video dictionaries with all metadata fields

    Raises:
        QuotaExceededError: If daily quota is exceeded
        HttpError: If YouTube API request fails

    TIER 1 Rule 3: Uses UTC for fetched_at timestamp.
    TIER 2 Rule 11: Converts ISO 8601 duration to integer seconds.
    Risk Mitigation (PERF-002): Checks quota before each API call.

    Example:
        >>> video_ids = ['dQw4w9WgXcQ', 'jNQXAC9IVRw']
        >>> videos = _fetch_video_details(video_ids)
        >>> len(videos)
        2
        >>> videos[0]['duration_seconds']
        245
    """
    if not video_ids:
        logger.warning("_fetch_video_details called with empty video_ids list")
        return []

    # TIER 1 Rule 3: Always use UTC
    fetched_at = datetime.now(timezone.utc).isoformat()
    youtube = create_youtube_client()
    all_videos: list[dict] = []

    # Batch video IDs into groups of 50 (YouTube API limit)
    BATCH_SIZE = 50
    for i in range(0, len(video_ids), BATCH_SIZE):
        batch = video_ids[i : i + BATCH_SIZE]
        batch_num = (i // BATCH_SIZE) + 1
        total_batches = (len(video_ids) + BATCH_SIZE - 1) // BATCH_SIZE

        logger.info(
            f"Fetching video details batch {batch_num}/{total_batches} " f"({len(batch)} videos)"
        )

        # Risk Mitigation (PERF-002): Check quota before API call
        if is_quota_exceeded():
            logger.error(
                f"Quota exceeded before fetching batch {batch_num}. "
                f"Fetched {len(all_videos)}/{len(video_ids)} videos so far."
            )
            raise QuotaExceededError(
                "YouTube API-kvote overskredet under videohenting. " "Noen videoer kan mangle."
            )

        try:
            # Fetch video details (1 quota unit per batch)
            response = (
                youtube.videos().list(id=",".join(batch), part="snippet,contentDetails").execute()
            )

            # Log successful API call (1 quota unit)
            log_api_call("youtube_videos", 1, True)

            # Extract video details from response
            items = response.get("items", [])
            for item in items:
                try:
                    snippet = item["snippet"]
                    content_details = item["contentDetails"]

                    # Parse ISO 8601 duration to seconds (TIER 2 Rule 11)
                    duration_str = content_details["duration"]
                    duration_timedelta = isodate.parse_duration(duration_str)
                    duration_seconds = int(duration_timedelta.total_seconds())

                    video = {
                        "video_id": item["id"],
                        "title": snippet["title"],
                        "youtube_channel_id": snippet["channelId"],
                        "youtube_channel_name": snippet["channelTitle"],
                        "thumbnail_url": snippet["thumbnails"]["default"]["url"],
                        "duration_seconds": duration_seconds,
                        "published_at": snippet["publishedAt"],
                        "fetched_at": fetched_at,
                    }

                    all_videos.append(video)

                except KeyError as e:
                    # Risk Mitigation (DATA-003): Handle missing fields gracefully
                    video_id = item.get("id", "unknown")
                    logger.warning(
                        f"Missing field in video details response for {video_id}: {e}. "
                        "Skipping video."
                    )
                    continue

        except HttpError as e:
            # Log failed API call
            log_api_call("youtube_videos", 1, False, str(e))

            # Check for quota exceeded (should be caught by pre-check, but defensive)
            if e.resp.status == 403 and "quotaExceeded" in str(e):
                logger.error(f"Quota exceeded during batch {batch_num}")
                raise QuotaExceededError("YouTube API-kvote overskredet under videohenting.")

            # Re-raise other errors
            logger.error(f"Failed to fetch video details batch {batch_num}: {e}")
            raise

    logger.info(f"Successfully fetched details for {len(all_videos)}/{len(video_ids)} videos")
    return all_videos


def _deduplicate_videos(videos: list[dict]) -> list[dict]:
    """
    Remove duplicate video IDs from list.

    YouTube API sometimes returns duplicate video IDs. This function
    keeps the first occurrence of each video ID and discards duplicates.

    Args:
        videos: List of video dictionaries

    Returns:
        List with unique video IDs only (preserves order, keeps first occurrence)

    Risk Mitigation (DATA-001): Simple set-based deduplication logic.

    Example:
        >>> videos = [
        ...     {"video_id": "abc", "title": "Video 1"},
        ...     {"video_id": "def", "title": "Video 2"},
        ...     {"video_id": "abc", "title": "Video 1 Duplicate"}
        ... ]
        >>> deduplicated = _deduplicate_videos(videos)
        >>> len(deduplicated)
        2
        >>> [v["video_id"] for v in deduplicated]
        ['abc', 'def']
    """
    seen = set()
    deduplicated = []
    duplicate_count = 0

    for video in videos:
        video_id = video["video_id"]
        if video_id not in seen:
            seen.add(video_id)
            deduplicated.append(video)
        else:
            # Risk Mitigation (DATA-001): Log duplicates for observability
            duplicate_count += 1
            logger.warning(
                f"Duplicate video ID found: {video_id} (title: {video.get('title', 'N/A')})"
            )

    if duplicate_count > 0:
        logger.info(
            f"Removed {duplicate_count} duplicate videos. "
            f"Unique videos: {len(deduplicated)}/{len(videos)}"
        )

    return deduplicated


def add_source(source_input: str) -> dict:
    """
    Add a new YouTube channel or playlist as content source.

    Orchestrates the complete flow:
    1. Parse and validate input URL
    2. Check for duplicate sources
    3. Fetch video IDs from channel/playlist
    4. Fetch detailed video metadata
    5. Deduplicate videos
    6. Insert content source and videos into database

    TIER 1 Rules Applied:
    - Rule 3: UTC timestamps for all database operations
    - Rule 5: Validate and sanitize all parent inputs
    - Rule 6: SQL placeholders via database query functions

    Risk Mitigation:
    - PERF-002: Quota checking in fetch functions
    - DATA-002: Partial fetch handling with fetch_complete flag
    - SEC-001: API key sanitization in error messages (via log_api_call)
    - SEC-002: ReDoS protection in _parse_input()

    Args:
        source_input: YouTube URL, channel ID, or playlist ID

    Returns:
        Dictionary with source info:
        {
            'success': True,
            'source_id': 'UC...',
            'source_type': 'channel' or 'playlist',
            'name': 'Channel/Playlist Name',
            'video_count': 150,
            'fetch_complete': True/False
        }

    Raises:
        ValueError: If input is invalid (Norwegian message)
        QuotaExceededError: If YouTube API quota exceeded (Norwegian message)
        Exception: Other YouTube API errors

    Example:
        result = add_source('https://www.youtube.com/@Blippi')
        print(f"Added {result['video_count']} videos from {result['name']}")
    """
    # TIER 1 Rule 3: Use UTC for all timestamps
    now = datetime.now(timezone.utc).isoformat()

    # Step 1: Parse and validate input (TIER 1 Rule 5, SEC-002)
    logger.info(f"Parsing input: {source_input[:100]}...")  # Truncate for logs
    source_type, source_id = _parse_input(source_input)
    logger.info(f"Parsed as {source_type}: {source_id}")

    # Step 2: Check for duplicate source
    existing_source = get_source_by_source_id(source_id)
    if existing_source:
        logger.warning(f"Source {source_id} already exists: {existing_source['name']}")
        raise ValueError(f"Denne {source_type}en er allerede lagt til: {existing_source['name']}")

    # Step 3: Resolve handle to channel ID if needed
    # Handles (from @username URLs) need to be resolved to channel IDs
    # before calling search API. Channel IDs start with "UC", handles don't.
    resolved_source_id = source_id
    if source_type == "channel" and not source_id.startswith("UC"):
        logger.info(f"Source ID appears to be a handle: {source_id}. Resolving to channel ID...")
        youtube = create_youtube_client()
        resolved_source_id = _resolve_handle_to_channel_id(youtube, source_id)
        logger.info(f"Resolved handle {source_id} to channel ID: {resolved_source_id}")

    # Step 4: Fetch video IDs based on source type
    logger.info(f"Fetching video IDs for {source_type} {resolved_source_id}...")
    fetch_complete = True  # Track if fetch completed successfully

    if source_type == "channel":
        youtube = create_youtube_client()
        video_ids, fetch_complete = fetch_all_channel_videos(youtube, resolved_source_id)
    elif source_type == "playlist":
        video_ids, fetch_complete = _fetch_playlist_videos(source_id)
    else:
        # Should never happen due to _parse_input validation
        raise ValueError(f"Ugyldig kildetype: {source_type}")

    if not video_ids:
        logger.error(f"No videos found for {source_type} {source_id}")
        raise ValueError(
            f"Ingen videoer funnet for denne {source_type}en. " "Sjekk at lenken er korrekt."
        )

    logger.info(f"Fetched {len(video_ids)} video IDs (complete: {fetch_complete})")

    # Step 4: Fetch detailed video metadata (PERF-002: quota checking inside)
    logger.info(f"Fetching video details for {len(video_ids)} videos...")
    videos = _fetch_video_details(video_ids)

    if not videos:
        logger.error(f"Failed to fetch details for any videos from {source_id}")
        raise ValueError("Kunne ikke hente videoinformasjon. Prøv igjen senere.")

    logger.info(f"Fetched details for {len(videos)} videos")

    # Step 5: Deduplicate videos
    videos = _deduplicate_videos(videos)
    logger.info(f"After deduplication: {len(videos)} unique videos")

    # Step 6: Get source name
    # For channels: use channel_name from first video (already denormalized)
    # For playlists: need to fetch playlist title from API
    if source_type == "channel":
        source_name = videos[0]["youtube_channel_name"]
    else:  # playlist
        # Fetch playlist title from YouTube API
        try:
            youtube = create_youtube_client()

            # Risk Mitigation (PERF-002): Check quota before API call
            if is_quota_exceeded():
                raise QuotaExceededError("YouTube API-kvote overskredet. Noen videoer kan mangle.")

            response = (
                youtube.playlists().list(part="snippet", id=source_id, maxResults=1).execute()
            )

            # Log API call (1 quota unit for playlists.list)
            log_api_call("youtube_playlists", 1, True)

            if response.get("items"):
                source_name = response["items"][0]["snippet"]["title"]
            else:
                # Fallback if playlist not found (shouldn't happen if we got videos)
                source_name = f"Playlist {source_id}"
                logger.warning(f"Playlist title not found, using fallback: {source_name}")

        except HttpError as e:
            # Log failed API call
            log_api_call("youtube_playlists", 1, False, str(e))
            # Use fallback name
            source_name = f"Playlist {source_id}"
            logger.warning(f"Failed to fetch playlist title: {e}. Using fallback: {source_name}")

    logger.info(f"Source name: {source_name}")

    # Step 7: Insert content source (TIER 1 Rule 3: UTC timestamps, Rule 6: SQL placeholders)
    content_source_id = insert_content_source(
        source_id=source_id,
        source_type=source_type,
        name=source_name,
        video_count=len(videos),
        last_refresh=now,
        fetch_method="api",
        added_at=now,
    )
    logger.info(f"Inserted content source with ID: {content_source_id}")

    # Step 8: Bulk insert videos (TIER 1 Rule 6: SQL placeholders via executemany)
    videos_inserted = bulk_insert_videos(content_source_id, videos)
    logger.info(f"Bulk inserted {videos_inserted} videos")

    # Step 9: Return success response
    return {
        "success": True,
        "id": content_source_id,  # Database primary key for frontend
        "source_id": source_id,
        "source_type": source_type,
        "name": source_name,
        "video_count": len(videos),
        "fetch_complete": fetch_complete,
    }


def fetch_all_playlist_videos(youtube, playlist_id: str) -> tuple[list[str], bool]:
    """
    Public wrapper for _fetch_playlist_videos that matches the channel fetch API.

    Args:
        youtube: YouTube API client (for API consistency, though _fetch_playlist_videos creates its own)
        playlist_id: YouTube playlist ID

    Returns:
        Tuple of (video_ids, fetch_complete) where:
        - video_ids: List of all video IDs fetched
        - fetch_complete: True if all videos fetched, False if partial

    Example:
        youtube = create_youtube_client()
        video_ids, complete = fetch_all_playlist_videos(youtube, "PLrAXtm...")
    """
    return _fetch_playlist_videos(playlist_id)


def list_sources() -> list[dict]:
    """
    List all content sources with camelCase keys for frontend.

    Converts database snake_case to JavaScript camelCase convention.

    TIER 3 Rule 14: Return structure matches API specification.

    Returns:
        List of source dicts with camelCase keys:
        {
            'id': 1,
            'sourceId': 'UCrwObTfqv8u1KO7Fgk-FXHQ',
            'sourceType': 'channel',
            'name': 'Blippi',
            'videoCount': 487,
            'lastRefresh': '2025-10-19T10:15:00Z',
            'fetchMethod': 'api',
            'addedAt': '2025-10-19T10:15:00Z'
        }

    Example:
        sources = list_sources()
        for source in sources:
            print(f"{source['name']}: {source['videoCount']} videos")
    """
    sources = get_all_content_sources()

    # Convert snake_case to camelCase for frontend
    camel_sources = []
    for source in sources:
        camel_sources.append(
            {
                "id": source["id"],
                "sourceId": source["source_id"],
                "sourceType": source["source_type"],
                "name": source["name"],
                "videoCount": source["video_count"],
                "lastRefresh": source["last_refresh"],
                "fetchMethod": source["fetch_method"],
                "addedAt": source["added_at"],
            }
        )

    return camel_sources


def remove_source(source_id: int) -> dict:
    """
    Remove content source and all its videos.

    CASCADE DELETE automatically removes videos due to foreign key constraint.
    Returns info about what was deleted for user confirmation message.

    TIER 1 Rules Applied:
    - Rule 6: SQL placeholders via delete_content_source()

    Args:
        source_id: Primary key ID of content_sources table

    Returns:
        Dict with deletion info:
        {
            'success': True,
            'source_name': 'Blippi',
            'videos_removed': 487
        }

    Raises:
        ValueError: If source not found (Norwegian message for user)

    Example:
        result = remove_source(3)
        print(f"Removed {result['videos_removed']} videos from {result['source_name']}")
    """
    # Get source first to retrieve name and count videos
    from backend.exceptions import NotFoundError

    source = get_source_by_id(source_id)
    if not source:
        logger.warning(f"Attempted to remove non-existent source ID: {source_id}")
        raise NotFoundError("Kilde ikke funnet")

    source_name = source["name"]

    # Count videos before deletion
    from backend.db.queries import count_source_videos

    videos_count = count_source_videos(source_id)

    logger.info(f"Removing source {source_id} ({source_name}) with {videos_count} videos")

    # Delete source (CASCADE removes videos automatically)
    delete_content_source(source_id)

    logger.info(f"Successfully removed source {source_id} and {videos_count} videos")

    return {"success": True, "source_name": source_name, "videos_removed": videos_count}


def refresh_source(source_id: int) -> dict:
    """
    Refresh existing content source by fetching new videos.

    Compares fetched video IDs with existing videos in database,
    inserts only NEW videos, and updates source metadata.

    TIER 1 Rules Applied:
    - Rule 3: UTC timestamps for all operations
    - Rule 6: SQL placeholders via database functions

    Args:
        source_id: Primary key ID of content_sources table

    Returns:
        Dict with refresh results:
        {
            'success': True,
            'videos_added': 12,
            'videos_updated': 0,
            'last_refresh': '2025-10-19T14:30:00Z'
        }

    Raises:
        ValueError: If source not found (Norwegian message)
        QuotaExceededError: If YouTube API quota exceeded
        HttpError: Other YouTube API errors

    Example:
        result = refresh_source(3)
        print(f"Added {result['videos_added']} new videos")
    """
    # TIER 1 Rule 3: Use UTC for all timestamps
    now = datetime.now(timezone.utc).isoformat()

    # Step 1: Get existing source
    source = get_source_by_id(source_id)
    if not source:
        logger.warning(f"Attempted to refresh non-existent source ID: {source_id}")
        raise ValueError("Kilde ikke funnet")

    logger.info(f"Refreshing source {source_id} ({source['name']})")

    # Step 2: Resolve handle to channel ID if needed (same as add_source)
    source_type = source["source_type"]
    youtube_source_id = source["source_id"]

    # Handles (from @username URLs) need to be resolved to channel IDs
    resolved_source_id = youtube_source_id
    if source_type == "channel" and not youtube_source_id.startswith("UC"):
        logger.info(
            f"Source ID appears to be a handle: {youtube_source_id}. Resolving to channel ID..."
        )
        youtube = create_youtube_client()
        resolved_source_id = _resolve_handle_to_channel_id(youtube, youtube_source_id)
        logger.info(f"Resolved handle {youtube_source_id} to channel ID: {resolved_source_id}")

    # Step 3: Fetch video IDs based on source type
    if source_type == "channel":
        youtube = create_youtube_client()
        video_ids, fetch_complete = fetch_all_channel_videos(youtube, resolved_source_id)
    elif source_type == "playlist":
        video_ids, fetch_complete = _fetch_playlist_videos(youtube_source_id)
    else:
        raise ValueError(f"Ugyldig kildetype: {source_type}")

    logger.info(f"Fetched {len(video_ids)} video IDs during refresh (complete: {fetch_complete})")

    # Step 3: Query existing video IDs for this source
    from backend.db.queries import get_source_video_ids

    existing_video_ids = get_source_video_ids(source_id)

    logger.info(f"Source currently has {len(existing_video_ids)} videos in database")

    # Step 4: Filter to only NEW videos
    new_video_ids = [vid for vid in video_ids if vid not in existing_video_ids]

    if not new_video_ids:
        logger.info("No new videos found during refresh")
        # Update last_refresh timestamp even if no new videos
        update_content_source_refresh(source_id, now, source["video_count"])
        return {
            "success": True,
            "videos_added": 0,
            "videos_updated": 0,
            "last_refresh": now,
        }

    logger.info(f"Found {len(new_video_ids)} new videos to add")

    # Step 5: Fetch details for new videos
    new_videos = _fetch_video_details(new_video_ids)

    if not new_videos:
        logger.warning("Failed to fetch details for new videos")
        return {
            "success": True,
            "videos_added": 0,
            "videos_updated": 0,
            "last_refresh": now,
        }

    # Step 6: Deduplicate new videos
    new_videos = _deduplicate_videos(new_videos)

    # Step 7: Bulk insert new videos
    videos_added = bulk_insert_videos(source_id, new_videos)
    logger.info(f"Inserted {videos_added} new videos")

    # Step 8: Update source metadata
    new_total = source["video_count"] + videos_added
    update_content_source_refresh(source_id, now, new_total)

    logger.info(f"Refresh complete for source {source_id}: {videos_added} new videos added")

    return {
        "success": True,
        "videos_added": videos_added,
        "videos_updated": 0,
        "last_refresh": now,
    }
