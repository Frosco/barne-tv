"""
FastAPI application entry point for Safe YouTube Viewer.

TIER 3 Rule 13: All backend operations are synchronous (no async/await)
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import DEBUG, validate_config
from backend.routes import router

logger = logging.getLogger(__name__)

# Validate configuration on startup
validate_config()

# Initialize FastAPI application
app = FastAPI(
    title="Safe YouTube Viewer",
    description="Safe YouTube video viewer for kids with parental controls",
    version="1.0.0",
    debug=DEBUG,
)

# Configure CORS for local development
if DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Include API routes
app.include_router(router)


# =============================================================================
# STARTUP EVENTS (Story 1.2)
# =============================================================================


@app.on_event("startup")
def startup_event():
    """
    Validate YouTube API key on application startup.

    Story 1.2: This validates that the API key works before serving requests.
    Logs prominently but does NOT prevent startup (allows development mode).

    In production, you may want to fail fast by raising RuntimeError if invalid.
    """
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


@app.get("/health")
def health_check():
    """
    Health check endpoint for monitoring.

    Returns:
        Dictionary with status indicator
    """
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=DEBUG,
    )
