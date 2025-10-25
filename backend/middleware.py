"""
Rate limiting middleware for Safe YouTube Viewer.

Protects admin endpoints from brute-force and DoS attacks.

TIER 2 Rule (New): Rate limiting for admin endpoints
- 100 requests per minute per IP address
- Returns 429 Too Many Requests with Norwegian message
- Health check endpoint exempt from rate limiting

Story 1.5 - Channel Management (QA Fix)
"""

import logging
import os
from slowapi import Limiter
from slowapi.util import get_remote_address

logger = logging.getLogger(__name__)

# Create limiter instance
# Uses IP address as the key for rate limiting
# Note: Disabled in tests via TESTING environment variable

TESTING = os.getenv("TESTING", "false").lower() == "true"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["100/minute"] if not TESTING else [],  # No limits during testing
    headers_enabled=not TESTING,  # Disable headers in tests (TestClient incompatibility)
    enabled=not TESTING,  # Disable rate limiting entirely during tests
)


def get_limiter():
    """
    Get the configured rate limiter instance.

    Returns:
        Limiter: SlowAPI limiter configured for this application
    """
    return limiter


def custom_rate_limit_handler(request, exc):
    """
    Custom error handler for rate limit exceeded.

    Returns Norwegian error message consistent with other error responses.

    Args:
        request: FastAPI Request object
        exc: RateLimitExceeded exception

    Returns:
        JSONResponse with 429 status and Norwegian message
    """
    from fastapi.responses import JSONResponse

    logger.warning(f"Rate limit exceeded for IP: {get_remote_address(request)}")

    return JSONResponse(
        status_code=429,
        content={
            "error": "Rate limit exceeded",
            "message": "For mange forespørsler. Prøv igjen om litt.",
        },
    )
