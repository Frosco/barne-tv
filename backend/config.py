"""
Configuration management for Safe YouTube Viewer.

TIER 3 Rule 16: All environment variables accessed via this config module.
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Database Configuration
DATABASE_PATH = os.getenv("DATABASE_PATH", "/opt/youtube-viewer/data/app.db")

# YouTube API Configuration
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


# Server Configuration
def parse_allowed_hosts(env_value: str | None, default: str = "localhost,127.0.0.1") -> list[str]:
    """
    Parse ALLOWED_HOSTS from comma-separated string.

    Handles whitespace around commas, empty strings, and trailing commas.

    Args:
        env_value: Comma-separated host list or None
        default: Default value if env_value is None or empty

    Returns:
        List of cleaned hostnames

    Raises:
        ValueError: If resulting list is empty after parsing
    """
    value = env_value if env_value else default
    # Strip whitespace from each host and filter out empty strings
    hosts = [h.strip() for h in value.split(",") if h.strip()]

    if not hosts:
        raise ValueError("ALLOWED_HOSTS cannot be empty")

    return hosts


ALLOWED_HOSTS = parse_allowed_hosts(os.getenv("ALLOWED_HOSTS"))

# Add "testserver" for FastAPI TestClient compatibility when testing
TESTING = os.getenv("TESTING", "false").lower() == "true"
if TESTING and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS = ALLOWED_HOSTS + ["testserver"]

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
