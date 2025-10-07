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
