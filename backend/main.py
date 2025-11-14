"""
FastAPI application entry point for Safe YouTube Viewer.

TIER 3 Rule 13: All backend operations are synchronous (no async/await)
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from slowapi.errors import RateLimitExceeded

from backend.config import DEBUG, ALLOWED_HOSTS, validate_config
from backend.logging_config import setup_logging
from backend.middleware import get_limiter, custom_rate_limit_handler
from backend.routes import router

# Initialize JSON logging (Story 5.4 AC 3-5)
setup_logging()

logger = logging.getLogger(__name__)

# Validate configuration on startup
validate_config()


# =============================================================================
# LIFESPAN EVENTS (Story 1.2)
# =============================================================================


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan event handler for startup and shutdown.

    Story 1.2: Validates YouTube API key on application startup.
    Logs prominently but does NOT prevent startup (allows development mode).

    Note: While this handler is async (FastAPI requirement), the validation
    logic inside remains synchronous per TIER 3 Rule 13.
    """
    # Startup
    logger.info("Validating YouTube API key...")

    # Import here to avoid circular dependency
    from backend.services.content_source import validate_youtube_api_key

    try:
        if not validate_youtube_api_key():
            logger.error("=" * 80)
            logger.error("CRITICAL: Invalid YouTube API key")
            logger.error("Application will not function correctly without valid API key")
            logger.error("Please check your YOUTUBE_API_KEY in .env file")
            logger.error("See docs/youtube-api-setup.md for setup instructions")
            logger.error("=" * 80)
            # Don't prevent startup - allows development mode
            # In production, consider: raise RuntimeError("Invalid YouTube API key")
        else:
            logger.info("YouTube API key validated successfully")
    except Exception as e:
        logger.error(f"Failed to validate YouTube API key: {e}")
        logger.error("Application may not function correctly")

    yield  # Application runs here

    # Shutdown (if needed in future)
    logger.info("Application shutting down")


# Initialize FastAPI application with lifespan handler
app = FastAPI(
    title="Safe YouTube Viewer",
    description="Safe YouTube video viewer for kids with parental controls",
    version="1.0.0",
    debug=DEBUG,
    lifespan=lifespan,
)

# Configure rate limiting (Story 1.5 QA Fix)
limiter = get_limiter()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)

# Configure Jinja2 templates
TEMPLATE_DIR = Path(__file__).parent.parent / "frontend" / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Make templates object available to routes
app.state.templates = templates


# =============================================================================
# SECURITY MIDDLEWARE (Story 2.3)
# =============================================================================

# Trusted host protection - validates Host header against ALLOWED_HOSTS
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=ALLOWED_HOSTS,
)


# Custom security headers middleware (defense-in-depth)
# Primary headers set by Nginx, this provides protection if Nginx bypassed
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    """
    Add security headers to all responses.

    Story 2.3: Defense-in-depth security headers.
    Primary headers are set by Nginx in production, but FastAPI middleware
    provides backup protection if Nginx is bypassed or misconfigured.

    Headers added:
    - X-Robots-Tag: Prevents search engine indexing (AC 3)
    - X-Content-Type-Options: Prevents MIME sniffing (AC 12)
    - X-Frame-Options: Prevents clickjacking (AC 11)
    - X-XSS-Protection: Legacy browser XSS protection (AC 13)

    Note: While this middleware is async (FastAPI requirement), it only adds
    headers and does not perform async operations.
    """
    response = await call_next(request)
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    return response


# =============================================================================
# CORS MIDDLEWARE (Development only)
# =============================================================================

# Configure CORS for local development
if DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Mount static files directory (for built frontend assets and images)
STATIC_DIR = Path(__file__).parent.parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Mount frontend public directory (for images in development)
PUBLIC_DIR = Path(__file__).parent.parent / "frontend" / "public"
if PUBLIC_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(PUBLIC_DIR / "images")), name="images")

# Include API routes
app.include_router(router)


@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring.

    Story 5.3 AC 17: Verifies database connectivity.

    Returns:
        Dictionary with status and database connectivity indicator
        - {"status": "ok", "database": "connected"} on success
        - {"status": "error", "database": "disconnected"} on database failure
    """
    from datetime import datetime, timezone
    from backend.db.queries import get_connection

    try:
        # Test database connectivity with simple query
        with get_connection() as conn:
            conn.execute("SELECT 1").fetchone()
        return {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
        }
    except Exception as e:
        logger.error(f"Database connectivity check failed: {e}")
        return {
            "status": "error",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "disconnected",
        }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
    )
