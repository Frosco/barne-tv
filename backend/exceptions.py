"""
Custom exception classes for Safe YouTube Viewer.
"""


class ValidationError(Exception):
    """Raised when input validation fails."""

    pass


class APIError(Exception):
    """Raised when external API calls fail."""

    pass


class NoVideosAvailableError(Exception):
    """Raised when no videos are available for selection."""

    pass


class AuthenticationError(Exception):
    """Raised when authentication fails."""

    pass


class VideoUnavailableError(Exception):
    """Raised when a video is no longer available."""

    pass


class QuotaExceededError(Exception):
    """
    Raised when YouTube API quota is exceeded.

    TIER 3 Rule 14: Norwegian messages for users, English for code/logs.

    Story 1.2 - YouTube API Quota Tracking
    """

    def __init__(self, message: str = "YouTube API-kvote overskredet. Prøv igjen i morgen."):
        self.message = message
        super().__init__(self.message)
