"""
FastAPI application entry point for Safe YouTube Viewer.

TIER 3 Rule 13: All backend operations are synchronous (no async/await)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config import DEBUG, validate_config
from backend.routes import router

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
