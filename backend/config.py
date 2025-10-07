"""
Configuration management for Safe YouTube Viewer.

TIER 3 Rule 16: All environment variables accessed via this config module.
"""

import os

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "/opt/youtube-viewer/data/app.db")

# YouTube API Configuration
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")

# Server Configuration
ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# Environment
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = ENVIRONMENT == "development"


def validate_config():
    """
    Validate that required configuration is present.

    Raises:
        ValueError: If required configuration is missing
    """
    if not YOUTUBE_API_KEY and ENVIRONMENT == "production":
        raise ValueError("YOUTUBE_API_KEY must be set in production")

    if not DATABASE_PATH:
        raise ValueError("DATABASE_PATH must be set")
