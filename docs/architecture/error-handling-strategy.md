# Error Handling Strategy

Based on your all-sync architecture using FastAPI with Python 3.11, and the child-safety focus of this application, here's the error handling approach:

## General Approach

**Error Model:** Exception-based with custom exception hierarchy  
**Exception Structure:**
```python
# backend/exceptions.py
class AppException(Exception):
    """Base exception for all application errors"""
    def __init__(self, message: str, status_code: int = 500, details: dict = None):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

class YouTubeAPIError(AppException):
    """YouTube API unavailable or quota exceeded"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=503, details=details)

class VideoUnavailableError(AppException):
    """Video cannot be played (deleted, private, region-locked)"""
    def __init__(self, video_id: str):
        super().__init__(
            f"Video {video_id} is unavailable",
            status_code=404,
            details={"video_id": video_id}
        )

class ContentSourceNotFoundError(AppException):
    """Channel or playlist doesn't exist"""
    def __init__(self, source_id: str):
        super().__init__(
            f"Content source {source_id} not found",
            status_code=404,
            details={"source_id": source_id}
        )

class DatabaseError(AppException):
    """Database operation failed"""
    def __init__(self, operation: str, details: dict = None):
        super().__init__(
            f"Database operation failed: {operation}",
            status_code=500,
            details=details
        )

class ValidationError(AppException):
    """Input validation failed"""
    def __init__(self, message: str, details: dict = None):
        super().__init__(message, status_code=400, details=details)
```

**Error Propagation:** Exceptions bubble up to route handlers where FastAPI exception handlers convert them to JSON responses

**FastAPI Exception Handlers:**
```python
# backend/main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    # Log unexpected errors
    logger.exception(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "En uventet feil oppstod" if is_admin(request) else "Noe gikk galt"
        }
    )
```

## Logging Standards

**Library:** Python's built-in `logging` module (3.11+)  
**Format:** Structured JSON for easy parsing  
**Levels:** DEBUG, INFO, WARNING, ERROR, CRITICAL

**Configuration:**
```python
# backend/logging.conf (for uvicorn --log-config)
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add custom fields from extra
        if hasattr(record, "video_id"):
            log_data["video_id"] = record.video_id
        if hasattr(record, "source_id"):
            log_data["source_id"] = record.source_id
            
        return json.dumps(log_data)

# backend/main.py
logger = logging.getLogger("youtube-viewer")
logger.setLevel(logging.INFO)

handler = logging.FileHandler("/opt/youtube-viewer/logs/app.log")
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

**Required Context:**
- **Request ID:** Not implemented (single-user, not needed for this scale)
- **Operation Context:** Function name, module (automatic via logging)
- **User Context:** Session ID for admin requests only (child requests anonymous)

**Log Examples:**
```python
# Info level - normal operations
logger.info("Video fetched successfully", extra={"video_id": video_id, "duration": 245})

# Warning level - degraded but functional
logger.warning("YouTube API slow response", extra={"response_time_ms": 3500})

# Error level - operation failed
logger.error("Failed to fetch channel videos", extra={"source_id": source_id}, exc_info=True)
```

## Error Handling Patterns

### 1. External API Errors (YouTube Data API v3)

**Retry Policy:** Page-level retries only (not entire operations)

```python
# backend/services/content_source.py
import time
from typing import Optional

def fetch_videos_with_retry(
    youtube,
    channel_id: str,
    page_token: Optional[str] = None,
    max_retries: int = 3
) -> dict:
    """
    Fetch single page of videos with retry logic.
    
    Args:
        max_retries: Maximum retry attempts per page (default 3)
        - Retry 1: immediate
        - Retry 2: 1 second wait
        - Retry 3: 2 second wait
    
    Total max delay: 3 seconds per page
    For 800 videos (16 pages), worst case: 48 seconds additional wait
    """
    for attempt in range(max_retries):
        try:
            response = youtube.search().list(
                channelId=channel_id,
                part="id",
                maxResults=50,
                pageToken=page_token
            ).execute()
            return response
        except HttpError as e:
            if e.resp.status == 403:
                # Quota exceeded - don't retry
                raise YouTubeAPIError(
                    "YouTube API quota exceeded. Try again tomorrow.",
                    details={"quota_exceeded": True}
                )
            elif e.resp.status == 404:
                # Not found - don't retry
                raise ContentSourceNotFoundError(channel_id)
            elif attempt < max_retries - 1:
                # Transient error - retry with exponential backoff
                wait_time = attempt  # 0, 1, 2 seconds
                logger.warning(
                    f"YouTube API error on attempt {attempt + 1}, retrying in {wait_time}s",
                    extra={"status_code": e.resp.status, "attempt": attempt + 1}
                )
                time.sleep(wait_time)
            else:
                # Final attempt failed
                raise YouTubeAPIError(
                    f"YouTube API error after {max_retries} attempts",
                    details={"status_code": e.resp.status}
                )
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = attempt
                logger.warning(
                    f"Network error on attempt {attempt + 1}, retrying in {wait_time}s",
                    extra={"attempt": attempt + 1}
                )
                time.sleep(wait_time)
            else:
                logger.exception("YouTube API error after all retries")
                raise YouTubeAPIError("YouTube API utilgjengelig. Prøv igjen senere.")

def fetch_all_channel_videos(youtube, channel_id: str) -> tuple[list[dict], bool]:
    """
    Fetch all videos from a channel.
    
    Returns:
        tuple: (videos_list, fetch_complete)
        - videos_list: List of video metadata dicts
        - fetch_complete: True if all pages fetched, False if partial
    """
    videos = []
    page_token = None
    fetch_complete = True
    pages_fetched = 0
    
    try:
        while True:
            try:
                response = fetch_videos_with_retry(youtube, channel_id, page_token)
                
                # Extract video IDs from this page
                page_videos = [item['id']['videoId'] for item in response.get('items', [])]
                videos.extend(page_videos)
                pages_fetched += 1
                
                # Check for next page
                page_token = response.get('nextPageToken')
                if not page_token:
                    break  # No more pages
                    
            except YouTubeAPIError as e:
                # Non-retryable error on this page
                logger.error(
                    f"Failed to fetch page after retries, stopping",
                    extra={"pages_fetched": pages_fetched, "videos_so_far": len(videos)}
                )
                fetch_complete = False
                break
                
    except Exception as e:
        # Unexpected error
        logger.exception("Unexpected error during channel video fetch")
        fetch_complete = False
    
    return videos, fetch_complete
```

**Partial Fetch Handling:**

```python
# backend/routes.py
@app.post("/admin/sources")
async def add_source(request: Request):
    require_auth(request)
    
    # ... parse input, validate ...
    
    videos, fetch_complete = content_source.fetch_all_channel_videos(youtube, channel_id)
    
    # Fetch video details (duration, thumbnails)
    video_details = content_source.fetch_video_details(youtube, videos)
    
    # Save to database
    source = db.insert_content_source(source_id, source_type, name, ...)
    db.bulk_insert_videos(video_details, source.id)
    
    if fetch_complete:
        return {
            "success": True,
            "source": source,
            "videosAdded": len(videos),
            "message": f"Kanal lagt til: {name} ({len(videos)} videoer)"
        }
    else:
        # Partial fetch - offer retry
        return {
            "success": True,
            "partial": True,
            "source": source,
            "videosAdded": len(videos),
            "estimatedTotal": "flere",
            "message": f"Lagt til {len(videos)} videoer (nettverksfeil). Klikk 'Oppdater' for å hente resten.",
            "retryAvailable": True
        }
```

**User-Facing Error Messages (Norwegian):**
- Quota exceeded: "YouTube API kvote overskredet. Prøv igjen i morgen."
- Channel not found: "Kanal ikke funnet"
- Network error: "YouTube API utilgjengelig. Prøv igjen senere."

### 2. Business Logic Errors

**Custom Exceptions:** Defined for domain-specific failures
```python
class DailyLimitReachedError(AppException):
    """Child has reached daily viewing limit"""
    def __init__(self):
        super().__init__(
            "Daily limit reached",
            status_code=429,
            details={"limit_type": "daily_viewing"}
        )

class NoVideosAvailableError(AppException):
    """No videos available for selection"""
    def __init__(self, reason: str):
        super().__init__(
            "No videos available",
            status_code=503,
            details={"reason": reason}
        )
```

**User-Facing Errors:** Handled in frontend with mascot messages
- Limit reached → Navigate to /grace screen
- No videos → "Ingen videoer tilgjengelig. Be foreldrene legge til kanaler."

**Error Codes:** Not implemented (simple application, HTTP status codes sufficient)

### 3. Data Consistency

**Transaction Strategy:** SQLite transactions via context manager
```python
# backend/db/queries.py
import sqlite3
from contextlib import contextmanager

@contextmanager
def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Usage in services
with get_connection() as conn:
    conn.execute("INSERT INTO videos (...) VALUES (...)")
    conn.execute("UPDATE content_sources SET video_count = ...")
    # Automatic commit on success, rollback on exception
```

**Compensation Logic:** Not needed (no distributed transactions)

**Idempotency:** Critical operations are idempotent:
- Adding duplicate video: Ignored (video_id + content_source_id is not unique by design)
- Marking video unavailable: Sets flag regardless of current state
- Logging watch history: Always inserts new row (history is append-only)

---

## Rationale for Key Decisions

**Why exception-based over error codes?**
- Python's idiomatic approach
- FastAPI has excellent exception handling
- Simpler for synchronous code
- Easier for AI agents to implement correctly

**Why page-level retry with exponential backoff?**
- Handles transient network hiccups gracefully
- Parent gets clear feedback on partial fetches
- Weekly refresh will automatically complete partial fetches
- Minimal complexity added
- Reasonable wait times (max 3 seconds per page)

**Why JSON logging?**
- Easy to parse for debugging
- Can be ingested by log aggregation tools later
- Structured data beats unstructured text

**Why no request IDs?**
- Single-user application
- Logs can be correlated by timestamp
- Adds complexity without benefit at this scale

**Potential concerns:**
- No circuit breakers: Acceptable for single-user, but would need them at scale
- No dead letter queue: Failed operations just fail - acceptable for this use case
- Logging to file: Works for single server, wouldn't scale to multiple instances

---

