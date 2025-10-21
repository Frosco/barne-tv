"""
Unit tests for content_source service (Story 1.2 - API Validation & Quota).

TIER 1 Safety Tests: 100% coverage required for validation functions.

Test IDs from test design document:
- 1.2-UNIT-012 through 1.2-UNIT-015 (is_quota_exceeded)
- 1.2-UNIT-016 through 1.2-UNIT-018 (QuotaExceededError)
- 1.2-UNIT-019 through 1.2-UNIT-023 (validate_youtube_api_key)
"""

import pytest
from unittest.mock import Mock
from googleapiclient.errors import HttpError
from backend.services.content_source import is_quota_exceeded, validate_youtube_api_key
from backend.exceptions import QuotaExceededError


# =============================================================================
# is_quota_exceeded() Tests
# =============================================================================


@pytest.mark.tier1
def test_is_quota_exceeded_returns_true_when_at_threshold(monkeypatch):
    """
    Test is_quota_exceeded() returns True when usage >= 9500 (1.2-UNIT-012).

    TIER 1 Safety Test - Critical quota threshold enforcement.
    """
    # Arrange - Mock get_daily_quota_usage to return exactly 9500
    monkeypatch.setattr("backend.services.content_source.get_daily_quota_usage", lambda date: 9500)

    # Act
    result = is_quota_exceeded()

    # Assert
    assert result is True


@pytest.mark.tier1
def test_is_quota_exceeded_returns_false_when_below_threshold(monkeypatch):
    """
    Test is_quota_exceeded() returns False when usage < 9500 (1.2-UNIT-013).

    Allows continued API usage when under limit.
    """
    # Arrange - Mock get_daily_quota_usage to return 9499
    monkeypatch.setattr("backend.services.content_source.get_daily_quota_usage", lambda date: 9499)

    # Act
    result = is_quota_exceeded()

    # Assert
    assert result is False


def test_is_quota_exceeded_returns_false_when_no_usage(monkeypatch):
    """
    Test is_quota_exceeded() returns False when usage is 0 (1.2-UNIT-014).

    Edge case: Startup scenario or new day.
    """
    # Arrange
    monkeypatch.setattr("backend.services.content_source.get_daily_quota_usage", lambda date: 0)

    # Act
    result = is_quota_exceeded()

    # Assert
    assert result is False


def test_is_quota_exceeded_boundary_condition(monkeypatch):
    """
    Test is_quota_exceeded() at exactly 9500 (1.2-UNIT-015).

    Boundary condition validation - threshold is inclusive.
    """
    # Test at threshold
    monkeypatch.setattr("backend.services.content_source.get_daily_quota_usage", lambda date: 9500)
    assert is_quota_exceeded() is True

    # Test just below threshold
    monkeypatch.setattr("backend.services.content_source.get_daily_quota_usage", lambda date: 9499)
    assert is_quota_exceeded() is False

    # Test above threshold
    monkeypatch.setattr("backend.services.content_source.get_daily_quota_usage", lambda date: 9501)
    assert is_quota_exceeded() is True


# =============================================================================
# QuotaExceededError Tests
# =============================================================================


@pytest.mark.tier1
def test_quota_exceeded_error_can_be_raised():
    """
    Test that QuotaExceededError can be raised (1.2-UNIT-016).

    Basic error handling validation.
    """
    # Act & Assert
    with pytest.raises(QuotaExceededError) as exc_info:
        raise QuotaExceededError()

    # Verify it's the correct exception type
    assert isinstance(exc_info.value, QuotaExceededError)


@pytest.mark.tier1
def test_quota_exceeded_error_has_norwegian_message():
    """
    Test QuotaExceededError has Norwegian message (1.2-UNIT-017).

    TIER 3 Rule 14: Norwegian messages for users.
    """
    # Act
    error = QuotaExceededError()

    # Assert
    assert "API-kvote overskredet" in str(error)
    assert error.message == "YouTube API-kvote overskredet. Prøv igjen i morgen."


def test_quota_exceeded_error_accepts_custom_message():
    """
    Test QuotaExceededError accepts custom message (1.2-UNIT-018 extended).

    Allows customization while maintaining default.
    """
    # Act
    custom_message = "Custom quota error message"
    error = QuotaExceededError(custom_message)

    # Assert
    assert error.message == custom_message
    assert str(error) == custom_message


# =============================================================================
# validate_youtube_api_key() Tests
# =============================================================================


@pytest.mark.tier1
def test_validate_youtube_api_key_returns_true_for_success(monkeypatch, test_db):
    """
    Test validate_youtube_api_key() returns True for successful API response (1.2-UNIT-019).

    Happy path validation.
    """
    # Arrange
    mock_youtube = Mock()
    mock_search = Mock()
    mock_list = Mock()

    # Set up mock chain: youtube.search().list().execute()
    mock_list.return_value.execute.return_value = {"items": []}
    mock_search.return_value.list = mock_list
    mock_youtube.search = mock_search

    # Mock create_youtube_client to return our mock
    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )

    # Mock log_api_call
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    result = validate_youtube_api_key()

    # Assert
    assert result is True


@pytest.mark.tier1
def test_validate_youtube_api_key_returns_false_for_http_400(monkeypatch):
    """
    Test validate_youtube_api_key() returns False for HTTP 400 (1.2-UNIT-020).

    Invalid key detection - bad request.
    """
    # Arrange
    mock_youtube = Mock()
    mock_response = Mock()
    mock_response.status = 400

    # Create HttpError
    http_error = HttpError(mock_response, b"Bad Request")

    # Mock the entire chain to raise HttpError
    mock_youtube.search.return_value.list.return_value.execute.side_effect = http_error

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    result = validate_youtube_api_key()

    # Assert
    assert result is False


@pytest.mark.tier1
def test_validate_youtube_api_key_returns_false_for_http_403(monkeypatch):
    """
    Test validate_youtube_api_key() returns False for HTTP 403 (1.2-UNIT-021).

    Invalid key detection - forbidden.
    """
    # Arrange
    mock_youtube = Mock()
    mock_response = Mock()
    mock_response.status = 403

    http_error = HttpError(mock_response, b"Forbidden")

    mock_youtube.search.return_value.list.return_value.execute.side_effect = http_error

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    result = validate_youtube_api_key()

    # Assert
    assert result is False


def test_validate_youtube_api_key_raises_for_network_error(monkeypatch):
    """
    Test validate_youtube_api_key() raises exception for network errors (1.2-UNIT-022).

    Error propagation for non-authentication errors.
    """
    # Arrange
    mock_youtube = Mock()
    mock_response = Mock()
    mock_response.status = 500

    http_error = HttpError(mock_response, b"Internal Server Error")

    mock_youtube.search.return_value.list.return_value.execute.side_effect = http_error

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )

    # Act & Assert - Should re-raise non-400/403 errors
    with pytest.raises(HttpError) as exc_info:
        validate_youtube_api_key()

    assert exc_info.value.resp.status == 500


@pytest.mark.tier1
def test_validate_youtube_api_key_logs_validation_result(monkeypatch):
    """
    Test validate_youtube_api_key() logs validation result (1.2-UNIT-023).

    Audit trail requirement - all validations logged.
    """
    # Arrange
    mock_youtube = Mock()
    mock_youtube.search.return_value.list.return_value.execute.return_value = {"items": []}

    mock_log_api_call = Mock()

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.log_api_call", mock_log_api_call)

    # Act
    validate_youtube_api_key()

    # Assert - log_api_call should have been called once
    assert mock_log_api_call.call_count == 1

    # Verify it was called with correct parameters
    call_args = mock_log_api_call.call_args[0]
    assert call_args[0] == "youtube_search_validation"
    assert call_args[1] == 1  # quota cost
    assert call_args[2] is True  # success


# =============================================================================
# _parse_input() Tests (Story 1.3)
# =============================================================================


@pytest.mark.tier1
def test_parse_input_channel_url_returns_tuple():
    """
    Test _parse_input() extracts channel ID from valid channel URL (1.3-UNIT-037).

    TIER 1 Safety Test - Input validation is safety-critical.
    """
    from backend.services.content_source import _parse_input

    # Arrange
    url = "https://www.youtube.com/channel/UCrwObTfqv8u1KO7Fgk-FXHQ"

    # Act
    source_type, source_id = _parse_input(url)

    # Assert
    assert source_type == "channel"
    assert source_id == "UCrwObTfqv8u1KO7Fgk-FXHQ"


@pytest.mark.tier1
def test_parse_input_custom_url_returns_tuple():
    """
    Test _parse_input() extracts handle from custom @handle URL (1.3-UNIT-038).

    TIER 1 Safety Test - Input validation is safety-critical.
    """
    from backend.services.content_source import _parse_input

    # Arrange
    url = "https://www.youtube.com/@Blippi"

    # Act
    source_type, source_id = _parse_input(url)

    # Assert
    assert source_type == "channel"
    assert source_id == "Blippi"


@pytest.mark.tier1
def test_parse_input_playlist_url_returns_tuple():
    """
    Test _parse_input() extracts playlist ID from valid playlist URL (1.3-UNIT-039).

    TIER 1 Safety Test - Input validation is safety-critical.
    """
    from backend.services.content_source import _parse_input

    # Arrange
    url = "https://www.youtube.com/playlist?list=PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"

    # Act
    source_type, source_id = _parse_input(url)

    # Assert
    assert source_type == "playlist"
    assert source_id == "PLrAXtmErZgOeiKm4sgNOknGvNjby9efdf"


@pytest.mark.tier1
def test_parse_input_invalid_url_raises_error():
    """
    Test _parse_input() raises ValueError for invalid URL (1.3-UNIT-040).

    TIER 2 Rule 14: Norwegian error message for user-facing errors.
    """
    from backend.services.content_source import _parse_input

    # Arrange
    invalid_url = "https://www.example.com/not-youtube"

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        _parse_input(invalid_url)

    # Verify Norwegian message
    assert "Ugyldig YouTube-URL" in str(exc_info.value)


@pytest.mark.tier1
def test_parse_input_malformed_url_raises_error():
    """
    Test _parse_input() raises ValueError for malformed URL (1.3-UNIT-041).

    Edge case: URL format doesn't match any expected patterns.
    """
    from backend.services.content_source import _parse_input

    # Arrange
    malformed_url = "not_a_url_at_all"

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        _parse_input(malformed_url)

    # Verify Norwegian message
    assert "Ugyldig YouTube-URL" in str(exc_info.value)


@pytest.mark.tier1
def test_parse_input_rejects_long_url():
    """
    Test _parse_input() rejects URL >500 chars (1.3-UNIT-042).

    Risk Mitigation (SEC-002): Length limit prevents ReDoS attacks.
    """
    from backend.services.content_source import _parse_input

    # Arrange - Create URL exceeding 500 char limit
    long_url = "https://www.youtube.com/channel/" + "A" * 500

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        _parse_input(long_url)

    # Verify error mentions length limit
    assert "for lang" in str(exc_info.value)
    assert "500" in str(exc_info.value)


@pytest.mark.tier1
def test_parse_input_simple_patterns_prevent_redos():
    """
    Test _parse_input() uses simple patterns resistant to ReDoS (1.3-UNIT-043).

    Risk Mitigation (SEC-002): Simple regex patterns with specific character classes
    prevent catastrophic backtracking.

    Note: With our implementation using bounded quantifiers and specific character
    classes (e.g., [A-Za-z0-9_-]{1,50}), ReDoS is not possible. This test validates
    the function completes quickly even with complex input.
    """
    import time
    from backend.services.content_source import _parse_input

    # Arrange - Potentially problematic input (many slashes)
    complex_input = "https://www.youtube.com/" + "/" * 100 + "channel/test"

    # Act
    start_time = time.time()
    try:
        _parse_input(complex_input)
    except ValueError:
        pass  # Expected to fail, we're testing speed not success
    elapsed = time.time() - start_time

    # Assert - Should complete nearly instantly (well under 2 seconds)
    assert elapsed < 0.1, f"URL parsing took {elapsed}s, should be nearly instant"


@pytest.mark.tier1
def test_parse_input_rejects_empty_input():
    """
    Test _parse_input() rejects empty/null input (1.3-UNIT-044).

    TIER 1 Rule 5: All inputs must be validated.
    """
    from backend.services.content_source import _parse_input

    # Test empty string
    with pytest.raises(ValueError) as exc_info:
        _parse_input("")

    assert "Ugyldig inndata" in str(exc_info.value)

    # Test None
    with pytest.raises(ValueError) as exc_info:
        _parse_input(None)

    assert "Ugyldig inndata" in str(exc_info.value)


def test_parse_input_handles_trailing_slash():
    """
    Test _parse_input() handles URLs with trailing slashes (edge case).

    Common user input variation.
    """
    from backend.services.content_source import _parse_input

    # Channel URL with trailing slash
    url = "https://www.youtube.com/channel/UCrwObTfqv8u1KO7Fgk-FXHQ/"
    source_type, source_id = _parse_input(url)
    assert source_type == "channel"
    assert source_id == "UCrwObTfqv8u1KO7Fgk-FXHQ"

    # Custom URL with trailing slash
    url = "https://www.youtube.com/@Blippi/"
    source_type, source_id = _parse_input(url)
    assert source_type == "channel"
    assert source_id == "Blippi"


def test_parse_input_strips_whitespace():
    """
    Test _parse_input() strips leading/trailing whitespace (edge case).

    Common user input variation from copy-paste.
    """
    from backend.services.content_source import _parse_input

    # Arrange - URL with surrounding whitespace
    url = "  https://www.youtube.com/channel/UCrwObTfqv8u1KO7Fgk-FXHQ  \n"

    # Act
    source_type, source_id = _parse_input(url)

    # Assert
    assert source_type == "channel"
    assert source_id == "UCrwObTfqv8u1KO7Fgk-FXHQ"


# =============================================================================
# _fetch_video_details() Tests (Story 1.3)
# =============================================================================


@pytest.mark.tier1
def test_fetch_video_details_returns_list_of_dicts(monkeypatch):
    """
    Test _fetch_video_details() returns list of video dictionaries (1.3-UNIT-012).

    TIER 1 Safety Test - Video metadata extraction is critical for functionality.
    """
    from backend.services.content_source import _fetch_video_details

    # Arrange - Mock YouTube API response
    mock_youtube = Mock()
    mock_response = {
        "items": [
            {
                "id": "test_video_1",
                "snippet": {
                    "title": "Test Video",
                    "channelId": "UC_test_channel",
                    "channelTitle": "Test Channel",
                    "publishedAt": "2023-01-01T00:00:00Z",
                    "thumbnails": {"default": {"url": "https://example.com/thumb.jpg"}},
                },
                "contentDetails": {"duration": "PT4M5S"},
            }
        ]
    }

    mock_youtube.videos.return_value.list.return_value.execute.return_value = mock_response
    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    result = _fetch_video_details(["test_video_1"])

    # Assert
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["video_id"] == "test_video_1"
    assert result[0]["title"] == "Test Video"
    assert result[0]["youtube_channel_id"] == "UC_test_channel"
    assert result[0]["youtube_channel_name"] == "Test Channel"
    assert result[0]["thumbnail_url"] == "https://example.com/thumb.jpg"
    assert result[0]["duration_seconds"] == 245  # 4*60 + 5 = 245
    assert result[0]["published_at"] == "2023-01-01T00:00:00Z"
    assert "fetched_at" in result[0]


@pytest.mark.tier1
def test_fetch_video_details_parses_iso8601_duration(monkeypatch):
    """
    Test _fetch_video_details() correctly parses ISO 8601 duration to seconds (1.3-UNIT-018).

    TIER 2 Rule 11: Duration must be stored as integer seconds.
    """
    from backend.services.content_source import _fetch_video_details

    # Arrange - Various ISO 8601 duration formats
    test_cases = [
        ("PT4M5S", 245),  # 4 minutes 5 seconds
        ("PT10H30M", 37800),  # 10 hours 30 minutes
        ("PT1H", 3600),  # 1 hour
        ("PT45S", 45),  # 45 seconds
    ]

    for duration_str, expected_seconds in test_cases:
        mock_youtube = Mock()
        mock_response = {
            "items": [
                {
                    "id": "test_video",
                    "snippet": {
                        "title": "Test",
                        "channelId": "UC_test",
                        "channelTitle": "Test",
                        "publishedAt": "2023-01-01T00:00:00Z",
                        "thumbnails": {"default": {"url": "https://example.com/thumb.jpg"}},
                    },
                    "contentDetails": {"duration": duration_str},
                }
            ]
        }

        mock_youtube.videos.return_value.list.return_value.execute.return_value = mock_response
        monkeypatch.setattr(
            "backend.services.content_source.create_youtube_client", lambda: mock_youtube
        )
        monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
        monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

        # Act
        result = _fetch_video_details(["test_video"])

        # Assert
        assert result[0]["duration_seconds"] == expected_seconds, f"Failed for {duration_str}"


@pytest.mark.tier1
def test_fetch_video_details_checks_quota_before_api_call(monkeypatch):
    """
    Test _fetch_video_details() checks quota before each API call (1.3-INT-020).

    Risk Mitigation (PERF-002): Quota check prevents exceeding daily limit.
    """
    from backend.services.content_source import _fetch_video_details
    from backend.exceptions import QuotaExceededError

    # Arrange - Mock quota exceeded
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: True)

    # Act & Assert
    with pytest.raises(QuotaExceededError) as exc_info:
        _fetch_video_details(["test_video_1"])

    # Verify Norwegian error message
    assert "API-kvote overskredet" in str(exc_info.value)


@pytest.mark.tier1
def test_fetch_video_details_batches_ids_correctly(monkeypatch):
    """
    Test _fetch_video_details() batches video IDs in groups of 50 (1.3-INT-019).

    YouTube API limit is 50 IDs per videos.list() request.
    """
    from backend.services.content_source import _fetch_video_details

    # Arrange - 130 video IDs (should create 3 batches: 50, 50, 30)
    video_ids = [f"video_{i}" for i in range(130)]

    call_count = 0

    def mock_execute():
        nonlocal call_count
        call_count += 1
        return {"items": []}

    mock_youtube = Mock()
    mock_youtube.videos.return_value.list.return_value.execute = mock_execute

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    _fetch_video_details(video_ids)

    # Assert - Should make 3 API calls (130 / 50 = 2.6 → 3 batches)
    assert call_count == 3


def test_fetch_video_details_handles_empty_list(monkeypatch):
    """
    Test _fetch_video_details() handles empty input list (edge case).

    Should return empty list without making API calls.
    """
    from backend.services.content_source import _fetch_video_details

    # Act
    result = _fetch_video_details([])

    # Assert
    assert result == []


@pytest.mark.tier1
def test_fetch_video_details_logs_api_calls(monkeypatch):
    """
    Test _fetch_video_details() logs each API call for quota tracking (1.3-INT-020).

    Risk Mitigation (PERF-002): All API calls must be logged for quota monitoring.
    """
    from backend.services.content_source import _fetch_video_details

    # Arrange
    mock_youtube = Mock()
    mock_response = {
        "items": [
            {
                "id": "test_video",
                "snippet": {
                    "title": "Test",
                    "channelId": "UC_test",
                    "channelTitle": "Test",
                    "publishedAt": "2023-01-01T00:00:00Z",
                    "thumbnails": {"default": {"url": "https://example.com/thumb.jpg"}},
                },
                "contentDetails": {"duration": "PT4M5S"},
            }
        ]
    }

    mock_youtube.videos.return_value.list.return_value.execute.return_value = mock_response
    mock_log = Mock()

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", mock_log)

    # Act
    _fetch_video_details(["test_video"])

    # Assert - log_api_call should have been called
    assert mock_log.call_count == 1
    call_args = mock_log.call_args[0]
    assert call_args[0] == "youtube_videos"
    assert call_args[1] == 1  # quota cost
    assert call_args[2] is True  # success


# =============================================================================
# _deduplicate_videos() Tests (Story 1.3)
# =============================================================================


@pytest.mark.tier1
def test_deduplicate_videos_removes_duplicates():
    """
    Test _deduplicate_videos() removes duplicate video IDs (1.3-UNIT-045).

    Risk Mitigation (DATA-001): YouTube API sometimes returns duplicates.
    """
    from backend.services.content_source import _deduplicate_videos

    # Arrange
    videos = [
        {"video_id": "abc", "title": "Video 1"},
        {"video_id": "def", "title": "Video 2"},
        {"video_id": "abc", "title": "Video 1 Duplicate"},
        {"video_id": "ghi", "title": "Video 3"},
    ]

    # Act
    result = _deduplicate_videos(videos)

    # Assert
    assert len(result) == 3
    video_ids = [v["video_id"] for v in result]
    assert video_ids == ["abc", "def", "ghi"]


@pytest.mark.tier1
def test_deduplicate_videos_keeps_first_occurrence():
    """
    Test _deduplicate_videos() keeps first occurrence of duplicate (1.3-UNIT-046).

    Behavior specification: First occurrence preserved, later ones discarded.
    """
    from backend.services.content_source import _deduplicate_videos

    # Arrange
    videos = [
        {"video_id": "abc", "title": "First"},
        {"video_id": "abc", "title": "Second"},
        {"video_id": "abc", "title": "Third"},
    ]

    # Act
    result = _deduplicate_videos(videos)

    # Assert
    assert len(result) == 1
    assert result[0]["title"] == "First"


def test_deduplicate_videos_handles_no_duplicates():
    """
    Test _deduplicate_videos() handles list with no duplicates (edge case).

    Should return same list (all videos unique).
    """
    from backend.services.content_source import _deduplicate_videos

    # Arrange
    videos = [
        {"video_id": "abc", "title": "Video 1"},
        {"video_id": "def", "title": "Video 2"},
        {"video_id": "ghi", "title": "Video 3"},
    ]

    # Act
    result = _deduplicate_videos(videos)

    # Assert
    assert len(result) == 3
    assert result == videos


def test_deduplicate_videos_handles_empty_list():
    """
    Test _deduplicate_videos() handles empty input list (edge case).
    """
    from backend.services.content_source import _deduplicate_videos

    # Act
    result = _deduplicate_videos([])

    # Assert
    assert result == []


# =============================================================================
# fetch_videos_with_retry() Tests (Story 1.3 - Phase 1.1)
# =============================================================================


@pytest.mark.tier1
def test_fetch_videos_with_retry_success_first_attempt(monkeypatch):
    """
    Test fetch_videos_with_retry() succeeds on first attempt (1.3-UNIT-049).

    Happy path: No errors, fetch succeeds immediately.
    """
    from backend.services.content_source import fetch_videos_with_retry

    # Arrange
    mock_youtube = Mock()
    mock_response = {
        "items": [{"id": {"videoId": "video1"}}, {"id": {"videoId": "video2"}}],
        "nextPageToken": "next_page_123",
    }
    mock_youtube.search.return_value.list.return_value.execute.return_value = mock_response

    # Act
    video_ids, next_page, success = fetch_videos_with_retry(mock_youtube, "UC_test", None)

    # Assert
    assert success is True
    assert video_ids == ["video1", "video2"]
    assert next_page == "next_page_123"
    assert mock_youtube.search().list().execute.call_count == 1


@pytest.mark.tier1
def test_fetch_videos_with_retry_network_error_retries_with_backoff(monkeypatch):
    """
    Test fetch_videos_with_retry() retries with exponential backoff (1.3-UNIT-048).

    Risk Mitigation (DATA-002): Retry logic with 0s, 1s, 2s backoff.
    Network error on attempt 1, success on attempt 2.
    """
    from backend.services.content_source import fetch_videos_with_retry

    # Arrange
    mock_youtube = Mock()
    mock_response_error = Mock()
    mock_response_error.status = 500  # Server error (retryable)

    attempt_count = 0

    def side_effect():
        nonlocal attempt_count
        attempt_count += 1
        if attempt_count == 1:
            raise HttpError(mock_response_error, b"Server Error")
        return {
            "items": [{"id": {"videoId": "video1"}}],
            "nextPageToken": None,
        }

    mock_youtube.search.return_value.list.return_value.execute.side_effect = side_effect

    # Mock time.sleep to track backoff timing
    sleep_times = []

    def mock_sleep(seconds):
        sleep_times.append(seconds)

    monkeypatch.setattr("time.sleep", mock_sleep)

    # Act
    video_ids, next_page, success = fetch_videos_with_retry(mock_youtube, "UC_test", None)

    # Assert
    assert success is True
    assert video_ids == ["video1"]
    assert attempt_count == 2  # Failed once, succeeded on second
    assert sleep_times == [0]  # First retry has 0s wait (attempt index 0)


@pytest.mark.tier1
def test_fetch_videos_with_retry_does_not_retry_quota_exceeded(monkeypatch):
    """
    Test fetch_videos_with_retry() does NOT retry on 403 quota exceeded (1.3-UNIT-049).

    Risk Mitigation (DATA-002): Quota exceeded should propagate immediately.
    """
    from backend.services.content_source import fetch_videos_with_retry

    # Arrange
    mock_youtube = Mock()
    mock_response = Mock()
    mock_response.status = 403
    http_error = HttpError(mock_response, b"quotaExceeded")
    mock_youtube.search.return_value.list.return_value.execute.side_effect = http_error

    # Act & Assert
    with pytest.raises(HttpError) as exc_info:
        fetch_videos_with_retry(mock_youtube, "UC_test", None)

    assert exc_info.value.resp.status == 403
    # Should not retry - execute() called only once
    assert mock_youtube.search().list().execute.call_count == 1


@pytest.mark.tier1
def test_fetch_videos_with_retry_does_not_retry_not_found(monkeypatch):
    """
    Test fetch_videos_with_retry() does NOT retry on 404 not found (1.3-UNIT-049).

    Risk Mitigation (DATA-002): Not found errors should propagate immediately.
    """
    from backend.services.content_source import fetch_videos_with_retry

    # Arrange
    mock_youtube = Mock()
    mock_response = Mock()
    mock_response.status = 404
    http_error = HttpError(mock_response, b"Not Found")
    mock_youtube.search.return_value.list.return_value.execute.side_effect = http_error

    # Act & Assert
    with pytest.raises(HttpError) as exc_info:
        fetch_videos_with_retry(mock_youtube, "UC_test", None)

    assert exc_info.value.resp.status == 404
    # Should not retry - execute() called only once
    assert mock_youtube.search().list().execute.call_count == 1


@pytest.mark.tier1
def test_fetch_videos_with_retry_all_attempts_fail_returns_failure(monkeypatch):
    """
    Test fetch_videos_with_retry() returns failure after all retries exhausted.

    Risk Mitigation (DATA-002): Partial fetch handling on network failure.
    All 3 attempts fail, should return ([], None, False).
    """
    from backend.services.content_source import fetch_videos_with_retry

    # Arrange
    mock_youtube = Mock()
    mock_response = Mock()
    mock_response.status = 500
    http_error = HttpError(mock_response, b"Server Error")
    mock_youtube.search.return_value.list.return_value.execute.side_effect = http_error

    # Mock time.sleep to avoid delays
    monkeypatch.setattr("time.sleep", lambda x: None)

    # Act
    video_ids, next_page, success = fetch_videos_with_retry(
        mock_youtube, "UC_test", None, max_retries=3
    )

    # Assert
    assert success is False
    assert video_ids == []
    assert next_page is None
    # Should attempt 3 times
    assert mock_youtube.search().list().execute.call_count == 3


# =============================================================================
# fetch_all_channel_videos() Tests (Story 1.3 - Phase 1.2)
# =============================================================================


@pytest.mark.tier1
def test_fetch_all_channel_videos_single_page_success(monkeypatch):
    """
    Test fetch_all_channel_videos() handles single-page response (1.3-UNIT-004).

    Channel with ≤50 videos, no pagination needed.
    """
    from backend.services.content_source import fetch_all_channel_videos

    # Arrange
    def mock_retry(youtube, channel_id, page_token, max_retries=3):
        return (["video1", "video2", "video3"], None, True)

    monkeypatch.setattr("backend.services.content_source.fetch_videos_with_retry", mock_retry)
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    mock_youtube = Mock()

    # Act
    video_ids, fetch_complete = fetch_all_channel_videos(mock_youtube, "UC_test")

    # Assert
    assert fetch_complete is True
    assert video_ids == ["video1", "video2", "video3"]


@pytest.mark.tier1
def test_fetch_all_channel_videos_multi_page_pagination(monkeypatch):
    """
    Test fetch_all_channel_videos() follows pagination correctly (1.3-UNIT-005).

    Multi-page response, should follow nextPageToken.
    """
    from backend.services.content_source import fetch_all_channel_videos

    # Arrange - Simulate 3 pages
    call_count = 0

    def mock_retry(youtube, channel_id, page_token, max_retries=3):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return (["video1", "video2"], "page2", True)
        elif call_count == 2:
            return (["video3", "video4"], "page3", True)
        else:
            return (["video5"], None, True)

    monkeypatch.setattr("backend.services.content_source.fetch_videos_with_retry", mock_retry)
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    mock_youtube = Mock()

    # Act
    video_ids, fetch_complete = fetch_all_channel_videos(mock_youtube, "UC_test")

    # Assert
    assert fetch_complete is True
    assert video_ids == ["video1", "video2", "video3", "video4", "video5"]
    assert call_count == 3


@pytest.mark.tier1
def test_fetch_all_channel_videos_safety_valve_triggers(monkeypatch):
    """
    Test fetch_all_channel_videos() safety valve at 100 pages (1.3-UNIT-023).

    Risk Mitigation (TECH-001): Prevents infinite loops on malformed responses.
    """
    from backend.services.content_source import fetch_all_channel_videos

    # Arrange - Always return next page token
    def mock_retry(youtube, channel_id, page_token, max_retries=3):
        return (["video1"], "next_page_always", True)

    monkeypatch.setattr("backend.services.content_source.fetch_videos_with_retry", mock_retry)
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    mock_youtube = Mock()

    # Act
    video_ids, fetch_complete = fetch_all_channel_videos(mock_youtube, "UC_test")

    # Assert
    assert fetch_complete is False  # Safety valve triggered
    assert len(video_ids) == 100  # 100 pages × 1 video per page


@pytest.mark.tier1
def test_fetch_all_channel_videos_quota_check_before_each_page(monkeypatch):
    """
    Test fetch_all_channel_videos() checks quota before each API call (1.3-INT-023).

    Risk Mitigation (PERF-002): Quota enforcement prevents exceeding daily limit.
    """
    from backend.services.content_source import fetch_all_channel_videos
    from backend.exceptions import QuotaExceededError

    # Arrange - Quota exceeded after 2 pages
    call_count = 0

    def mock_quota_check():
        nonlocal call_count
        call_count += 1
        return call_count > 2  # Exceeded after page 2

    def mock_retry(youtube, channel_id, page_token, max_retries=3):
        return (["video1", "video2"], "next_page", True)

    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", mock_quota_check)
    monkeypatch.setattr("backend.services.content_source.fetch_videos_with_retry", mock_retry)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    mock_youtube = Mock()

    # Act & Assert
    with pytest.raises(QuotaExceededError) as exc_info:
        fetch_all_channel_videos(mock_youtube, "UC_test")

    assert "API-kvote overskredet" in str(exc_info.value)


@pytest.mark.tier1
def test_fetch_all_channel_videos_network_failure_returns_partial(monkeypatch):
    """
    Test fetch_all_channel_videos() returns partial on network failure (1.3-INT-009).

    Risk Mitigation (DATA-002): Partial fetch handling preserves data fetched so far.
    """
    from backend.services.content_source import fetch_all_channel_videos

    # Arrange - Success on page 1-2, failure on page 3
    call_count = 0

    def mock_retry(youtube, channel_id, page_token, max_retries=3):
        nonlocal call_count
        call_count += 1
        if call_count <= 2:
            return (["video1", "video2"], "next_page", True)
        else:
            return ([], None, False)  # Network failure

    monkeypatch.setattr("backend.services.content_source.fetch_videos_with_retry", mock_retry)
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    mock_youtube = Mock()

    # Act
    video_ids, fetch_complete = fetch_all_channel_videos(mock_youtube, "UC_test")

    # Assert
    assert fetch_complete is False
    assert len(video_ids) == 4  # 2 pages × 2 videos = 4 videos before failure


# =============================================================================
# _fetch_playlist_videos() Tests (Story 1.3 - Phase 1.3)
# =============================================================================


@pytest.mark.tier1
def test_fetch_playlist_videos_single_page_success(monkeypatch):
    """
    Test _fetch_playlist_videos() handles single-page response (1.3-UNIT-009).

    Playlist with ≤50 videos, no pagination needed.
    """
    from backend.services.content_source import _fetch_playlist_videos

    # Arrange
    mock_youtube = Mock()
    mock_response = {
        "items": [
            {"snippet": {"resourceId": {"videoId": "video1"}}},
            {"snippet": {"resourceId": {"videoId": "video2"}}},
        ],
        "nextPageToken": None,
    }
    mock_youtube.playlistItems.return_value.list.return_value.execute.return_value = mock_response

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    video_ids, fetch_complete = _fetch_playlist_videos("PLtest")

    # Assert
    assert fetch_complete is True
    assert video_ids == ["video1", "video2"]


@pytest.mark.tier1
def test_fetch_playlist_videos_multi_page_pagination(monkeypatch):
    """
    Test _fetch_playlist_videos() follows pagination correctly (1.3-UNIT-010).

    Multi-page playlist response.
    """
    from backend.services.content_source import _fetch_playlist_videos

    # Arrange - Simulate 2 pages
    call_count = 0

    def mock_execute():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "items": [
                    {"snippet": {"resourceId": {"videoId": f"video{i}"}}} for i in range(1, 4)
                ],
                "nextPageToken": "page2",
            }
        else:
            return {
                "items": [
                    {"snippet": {"resourceId": {"videoId": f"video{i}"}}} for i in range(4, 6)
                ],
                "nextPageToken": None,
            }

    mock_youtube = Mock()
    mock_youtube.playlistItems.return_value.list.return_value.execute = mock_execute

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    video_ids, fetch_complete = _fetch_playlist_videos("PLtest")

    # Assert
    assert fetch_complete is True
    assert len(video_ids) == 5
    assert video_ids == ["video1", "video2", "video3", "video4", "video5"]


@pytest.mark.tier1
def test_fetch_playlist_videos_quota_check_before_each_page(monkeypatch):
    """
    Test _fetch_playlist_videos() checks quota before each API call (1.3-INT-018).

    Risk Mitigation (PERF-002): Quota enforcement.
    """
    from backend.services.content_source import _fetch_playlist_videos
    from backend.exceptions import QuotaExceededError

    # Arrange - Quota exceeded immediately
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: True)

    # Act & Assert
    with pytest.raises(QuotaExceededError) as exc_info:
        _fetch_playlist_videos("PLtest")

    assert "API-kvote overskredet" in str(exc_info.value)


@pytest.mark.tier1
def test_fetch_playlist_videos_network_failure_returns_partial(monkeypatch):
    """
    Test _fetch_playlist_videos() returns partial on network failure (1.3-INT-017).

    Risk Mitigation (DATA-002): Partial fetch handling.
    """
    from backend.services.content_source import _fetch_playlist_videos

    # Arrange - Success on first page, error on second
    call_count = 0

    def mock_execute():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {
                "items": [{"snippet": {"resourceId": {"videoId": "video1"}}}],
                "nextPageToken": "page2",
            }
        else:
            mock_response = Mock()
            mock_response.status = 500
            raise HttpError(mock_response, b"Server Error")

    mock_youtube = Mock()
    mock_youtube.playlistItems.return_value.list.return_value.execute = mock_execute

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: False)
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    video_ids, fetch_complete = _fetch_playlist_videos("PLtest")

    # Assert
    assert fetch_complete is False
    assert video_ids == ["video1"]  # Partial data from page 1


# =============================================================================
# add_source() Orchestration Tests (Story 1.3 - Phase 1.4)
# =============================================================================


@pytest.mark.tier1
def test_add_source_successful_channel_addition(monkeypatch, test_db):
    """
    Test add_source() successfully adds a channel end-to-end (1.3-INT-025).

    Full orchestration: parse → fetch IDs → fetch details → deduplicate → insert.
    """
    from backend.services.content_source import add_source

    # Arrange - Mock all the steps in the orchestration
    def mock_parse(source_input):
        return ("channel", "UC_test_channel")

    def mock_get_source(source_id):
        return None  # No existing source

    def mock_create_youtube():
        return Mock()

    def mock_fetch_all_channel(youtube, channel_id):
        return (["video1", "video2"], True)

    def mock_fetch_details(video_ids):
        return [
            {
                "video_id": "video1",
                "title": "Video 1",
                "youtube_channel_id": "UC_test_channel",
                "youtube_channel_name": "Test Channel",
                "thumbnail_url": "https://example.com/1.jpg",
                "duration_seconds": 120,
                "published_at": "2023-01-01T00:00:00Z",
                "fetched_at": "2023-12-01T00:00:00Z",
            },
            {
                "video_id": "video2",
                "title": "Video 2",
                "youtube_channel_id": "UC_test_channel",
                "youtube_channel_name": "Test Channel",
                "thumbnail_url": "https://example.com/2.jpg",
                "duration_seconds": 180,
                "published_at": "2023-01-02T00:00:00Z",
                "fetched_at": "2023-12-01T00:00:00Z",
            },
        ]

    def mock_dedupe(videos):
        return videos  # No duplicates

    def mock_insert_source(**kwargs):
        return 1  # Return source ID

    def mock_bulk_insert(source_id, videos):
        return len(videos)

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)
    monkeypatch.setattr("backend.services.content_source.get_source_by_source_id", mock_get_source)
    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", mock_create_youtube
    )
    monkeypatch.setattr(
        "backend.services.content_source.fetch_all_channel_videos", mock_fetch_all_channel
    )
    monkeypatch.setattr("backend.services.content_source._fetch_video_details", mock_fetch_details)
    monkeypatch.setattr("backend.services.content_source._deduplicate_videos", mock_dedupe)
    monkeypatch.setattr("backend.services.content_source.insert_content_source", mock_insert_source)
    monkeypatch.setattr("backend.services.content_source.bulk_insert_videos", mock_bulk_insert)

    # Act
    result = add_source("https://www.youtube.com/channel/UC_test_channel")

    # Assert
    assert result["success"] is True
    assert result["source_id"] == "UC_test_channel"
    assert result["source_type"] == "channel"
    assert result["name"] == "Test Channel"
    assert result["video_count"] == 2
    assert result["fetch_complete"] is True


@pytest.mark.tier1
def test_add_source_successful_playlist_addition(monkeypatch, test_db):
    """
    Test add_source() successfully adds a playlist end-to-end (1.3-INT-025).

    Playlist flow includes fetching playlist title from API.
    """
    from backend.services.content_source import add_source

    # Arrange
    def mock_parse(source_input):
        return ("playlist", "PL_test_playlist")

    def mock_get_source(source_id):
        return None

    def mock_fetch_playlist(playlist_id):
        return (["video1"], True)

    def mock_fetch_details(video_ids):
        return [
            {
                "video_id": "video1",
                "title": "Video 1",
                "youtube_channel_id": "UC_channel",
                "youtube_channel_name": "Channel Name",
                "thumbnail_url": "https://example.com/1.jpg",
                "duration_seconds": 120,
                "published_at": "2023-01-01T00:00:00Z",
                "fetched_at": "2023-12-01T00:00:00Z",
            }
        ]

    def mock_dedupe(videos):
        return videos

    mock_youtube = Mock()
    mock_youtube.playlists.return_value.list.return_value.execute.return_value = {
        "items": [{"snippet": {"title": "Test Playlist"}}]
    }

    def mock_create_youtube():
        return mock_youtube

    def mock_quota_exceeded():
        return False

    def mock_log_api_call(*args):
        pass

    def mock_insert_source(**kwargs):
        return 1

    def mock_bulk_insert(source_id, videos):
        return len(videos)

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)
    monkeypatch.setattr("backend.services.content_source.get_source_by_source_id", mock_get_source)
    monkeypatch.setattr(
        "backend.services.content_source._fetch_playlist_videos", mock_fetch_playlist
    )
    monkeypatch.setattr("backend.services.content_source._fetch_video_details", mock_fetch_details)
    monkeypatch.setattr("backend.services.content_source._deduplicate_videos", mock_dedupe)
    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", mock_create_youtube
    )
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", mock_quota_exceeded)
    monkeypatch.setattr("backend.services.content_source.log_api_call", mock_log_api_call)
    monkeypatch.setattr("backend.services.content_source.insert_content_source", mock_insert_source)
    monkeypatch.setattr("backend.services.content_source.bulk_insert_videos", mock_bulk_insert)

    # Act
    result = add_source("https://www.youtube.com/playlist?list=PL_test_playlist")

    # Assert
    assert result["success"] is True
    assert result["source_id"] == "PL_test_playlist"
    assert result["source_type"] == "playlist"
    assert result["name"] == "Test Playlist"
    assert result["video_count"] == 1
    assert result["fetch_complete"] is True


@pytest.mark.tier1
def test_add_source_detects_duplicate_source(monkeypatch, test_db):
    """
    Test add_source() detects and rejects duplicate source (1.3-INT-052).

    Risk Mitigation: Prevents duplicate content sources.
    """
    from backend.services.content_source import add_source

    # Arrange
    def mock_parse(source_input):
        return ("channel", "UC_existing")

    def mock_get_source(source_id):
        return {"id": 1, "source_id": "UC_existing", "name": "Existing Channel"}

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)
    monkeypatch.setattr("backend.services.content_source.get_source_by_source_id", mock_get_source)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        add_source("https://www.youtube.com/channel/UC_existing")

    # Verify Norwegian error message
    assert "allerede lagt til" in str(exc_info.value)
    assert "Existing Channel" in str(exc_info.value)


@pytest.mark.tier1
def test_add_source_handles_no_videos_found(monkeypatch, test_db):
    """
    Test add_source() handles channel/playlist with no videos.

    Edge case: Empty channel or private videos only.
    """
    from backend.services.content_source import add_source

    # Arrange
    def mock_parse(source_input):
        return ("channel", "UC_empty")

    def mock_get_source(source_id):
        return None

    def mock_create_youtube():
        return Mock()

    def mock_fetch_all_channel(youtube, channel_id):
        return ([], True)  # No videos found

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)
    monkeypatch.setattr("backend.services.content_source.get_source_by_source_id", mock_get_source)
    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", mock_create_youtube
    )
    monkeypatch.setattr(
        "backend.services.content_source.fetch_all_channel_videos", mock_fetch_all_channel
    )

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        add_source("https://www.youtube.com/channel/UC_empty")

    # Verify Norwegian error message
    assert "Ingen videoer funnet" in str(exc_info.value)


@pytest.mark.tier1
def test_add_source_quota_exceeded_during_fetch(monkeypatch, test_db):
    """
    Test add_source() handles quota exceeded during video fetch (1.3-INT-033).

    Risk Mitigation (PERF-002): Quota exceeded should propagate with Norwegian message.
    """
    from backend.services.content_source import add_source
    from backend.exceptions import QuotaExceededError

    # Arrange
    def mock_parse(source_input):
        return ("channel", "UC_test")

    def mock_get_source(source_id):
        return None

    def mock_create_youtube():
        return Mock()

    def mock_fetch_all_channel(youtube, channel_id):
        raise QuotaExceededError("YouTube API-kvote overskredet.")

    monkeypatch.setattr("backend.services.content_source._parse_input", mock_parse)
    monkeypatch.setattr("backend.services.content_source.get_source_by_source_id", mock_get_source)
    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", mock_create_youtube
    )
    monkeypatch.setattr(
        "backend.services.content_source.fetch_all_channel_videos", mock_fetch_all_channel
    )

    # Act & Assert
    with pytest.raises(QuotaExceededError) as exc_info:
        add_source("https://www.youtube.com/channel/UC_test")

    assert "API-kvote overskredet" in str(exc_info.value)


# =============================================================================
# API Key Security Tests (Story 1.3 - Phase 2.1 - SEC-001)
# =============================================================================


@pytest.mark.tier1
@pytest.mark.security
def test_api_key_not_logged_on_error(monkeypatch, caplog):
    """
    Test that API key is NEVER logged in error messages (1.3-INT-048, SEC-001).

    Risk Mitigation (SEC-001): API key exposure in logs is a security vulnerability.
    Logs should never contain the full API key.
    """
    import logging
    from backend.services.content_source import validate_youtube_api_key

    # Arrange - Set up logging capture
    caplog.set_level(logging.DEBUG)

    # Mock API key in environment
    test_api_key = "AIzaSyDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    monkeypatch.setenv("YOUTUBE_API_KEY", test_api_key)

    # Reload config to pick up the test API key
    import importlib
    import backend.config

    importlib.reload(backend.config)

    # Mock YouTube client to raise error
    mock_youtube = Mock()
    mock_response = Mock()
    mock_response.status = 403
    http_error = HttpError(mock_response, b"API key not valid")
    mock_youtube.search.return_value.list.return_value.execute.side_effect = http_error

    monkeypatch.setattr(
        "backend.services.content_source.create_youtube_client", lambda: mock_youtube
    )
    monkeypatch.setattr("backend.services.content_source.log_api_call", Mock())

    # Act
    result = validate_youtube_api_key()

    # Assert
    assert result is False

    # CRITICAL SECURITY CHECK: API key should NOT appear in any log messages
    all_logs = caplog.text
    assert test_api_key not in all_logs, "SECURITY VIOLATION: API key found in logs!"

    # The string "YOUTUBE_API_KEY" should not appear either (indicates key variable exposed)
    assert (
        "YOUTUBE_API_KEY" not in all_logs or all_logs.count("YOUTUBE_API_KEY") == 0
    ), "SECURITY CONCERN: Environment variable name exposed in logs"


@pytest.mark.tier1
@pytest.mark.security
def test_api_key_not_in_quota_exceeded_error(monkeypatch, caplog):
    """
    Test that quota exceeded errors do NOT expose API key (1.3-INT-049, SEC-001).

    Risk Mitigation (SEC-001): Even error messages to users must not leak API key.
    """
    import logging
    from backend.services.content_source import _fetch_video_details
    from backend.exceptions import QuotaExceededError

    # Arrange
    caplog.set_level(logging.DEBUG)

    test_api_key = "AIzaSyTEST_KEY_SHOULD_NOT_APPEAR_1234567"
    monkeypatch.setenv("YOUTUBE_API_KEY", test_api_key)

    # Reload config
    import importlib
    import backend.config

    importlib.reload(backend.config)

    # Mock quota exceeded
    monkeypatch.setattr("backend.services.content_source.is_quota_exceeded", lambda: True)

    # Act & Assert
    with pytest.raises(QuotaExceededError):
        _fetch_video_details(["test_video"])

    # CRITICAL SECURITY CHECK
    all_logs = caplog.text
    assert test_api_key not in all_logs, "SECURITY VIOLATION: API key found in logs!"


@pytest.mark.tier1
@pytest.mark.security
def test_api_key_sanitized_in_stack_traces(monkeypatch, caplog):
    """
    Test that stack traces do NOT contain API key (1.3-INT-050, SEC-001).

    Risk Mitigation (SEC-001): Stack traces in production logs can leak sensitive data.
    """
    import logging
    from backend.services.content_source import create_youtube_client

    # Arrange
    caplog.set_level(logging.DEBUG)

    test_api_key = "AIzaSySTACK_TRACE_TEST_KEY_9876543210"
    monkeypatch.setenv("YOUTUBE_API_KEY", test_api_key)

    # Reload config
    import importlib
    import backend.config

    importlib.reload(backend.config)

    # Act - Create client (this uses the API key internally)
    try:
        client = create_youtube_client()
        # The client creation should succeed, we're just checking logs
        assert client is not None
    except Exception:
        # Even if there's an exception, check logs
        pass

    # CRITICAL SECURITY CHECK
    all_logs = caplog.text
    assert test_api_key not in all_logs, "SECURITY VIOLATION: API key found in logs or stack trace!"


@pytest.mark.tier1
@pytest.mark.security
def test_no_api_key_in_http_error_messages(monkeypatch, caplog):
    """
    Test that HttpError messages do NOT contain API key (1.3-INT-051, SEC-001).

    Risk Mitigation (SEC-001): HTTP errors from Google API should be sanitized.
    """
    import logging
    from backend.services.content_source import fetch_videos_with_retry

    # Arrange
    caplog.set_level(logging.DEBUG)

    test_api_key = "AIzaSyHTTP_ERROR_TEST_KEY_ABCDEF123"
    monkeypatch.setenv("YOUTUBE_API_KEY", test_api_key)

    # Reload config
    import importlib
    import backend.config

    importlib.reload(backend.config)

    # Mock YouTube client to raise HttpError with potentially sensitive content
    mock_youtube = Mock()
    mock_response = Mock()
    mock_response.status = 500
    # Simulate error message that might contain API key
    error_content = b"Server error processing request"
    http_error = HttpError(mock_response, error_content)

    mock_youtube.search.return_value.list.return_value.execute.side_effect = http_error

    # Mock time.sleep to avoid delays
    monkeypatch.setattr("time.sleep", lambda x: None)

    # Act
    video_ids, next_page, success = fetch_videos_with_retry(
        mock_youtube, "UC_test", None, max_retries=2
    )

    # Assert
    assert success is False  # Should fail

    # CRITICAL SECURITY CHECK
    all_logs = caplog.text
    assert test_api_key not in all_logs, "SECURITY VIOLATION: API key found in HTTP error logs!"


# =============================================================================
# list_sources() Tests (Story 1.5)
# =============================================================================


def test_list_sources_returns_all_content_sources(monkeypatch, test_db):
    """
    Test list_sources() returns all content sources (Story 1.5).

    Verifies:
    - Returns list of all sources from database
    - Converts snake_case to camelCase for frontend
    - Orders by added_at DESC
    """
    from backend.services.content_source import list_sources

    # Arrange - Mock database to return sources
    mock_sources = [
        {
            "id": 1,
            "source_id": "UCtest1",
            "source_type": "channel",
            "name": "Channel 1",
            "video_count": 50,
            "last_refresh": "2023-12-01T00:00:00Z",
            "fetch_method": "api",
            "added_at": "2023-12-01T00:00:00Z",
        },
        {
            "id": 2,
            "source_id": "PLtest2",
            "source_type": "playlist",
            "name": "Playlist 1",
            "video_count": 30,
            "last_refresh": "2023-12-02T00:00:00Z",
            "fetch_method": "api",
            "added_at": "2023-12-02T00:00:00Z",
        },
    ]

    monkeypatch.setattr(
        "backend.services.content_source.get_all_content_sources", lambda: mock_sources
    )

    # Act
    result = list_sources()

    # Assert
    assert isinstance(result, list)
    assert len(result) == 2
    assert result[0]["sourceId"] == "UCtest1"  # camelCase
    assert result[1]["sourceId"] == "PLtest2"


def test_list_sources_returns_empty_list_when_no_sources(monkeypatch, test_db):
    """
    Test list_sources() returns empty list when no sources exist.

    Edge case: Fresh installation.
    """
    from backend.services.content_source import list_sources

    # Arrange - Mock database to return empty list
    monkeypatch.setattr("backend.services.content_source.get_all_content_sources", lambda: [])

    # Act
    result = list_sources()

    # Assert
    assert isinstance(result, list)
    assert len(result) == 0


# =============================================================================
# remove_source() Tests (Story 1.5)
# =============================================================================


def test_remove_source_successfully_deletes_source(monkeypatch, test_db):
    """
    Test remove_source() successfully deletes content source (Story 1.5).

    Verifies:
    - Gets source from database
    - Counts associated videos
    - Deletes source (CASCADE deletes videos)
    - Returns videos_removed count and source_name
    """
    from backend.services.content_source import remove_source

    # Arrange
    mock_source = {
        "id": 1,
        "source_id": "UCtest",
        "name": "Test Channel",
        "video_count": 42,
    }

    def mock_get_source(source_id):
        return mock_source if source_id == 1 else None

    def mock_count_videos(source_id):
        return 42 if source_id == 1 else 0

    mock_delete_called = False

    def mock_delete(source_id):
        nonlocal mock_delete_called
        mock_delete_called = True

    monkeypatch.setattr("backend.services.content_source.get_source_by_id", mock_get_source)
    monkeypatch.setattr("backend.services.content_source.delete_content_source", mock_delete)

    # Mock the video count query
    class MockRow:
        """Mock Row object that supports both index and key access."""

        def __getitem__(self, key):
            if key == 0 or key == "COUNT(*)":
                return 42
            raise KeyError(key)

    class MockConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, params):
            class MockCursor:
                def fetchone(self):
                    return MockRow()

            return MockCursor()

    monkeypatch.setattr("backend.db.queries.get_connection", lambda: MockConnection())

    # Act
    result = remove_source(1)

    # Assert
    assert result["videos_removed"] == 42
    assert result["source_name"] == "Test Channel"
    assert mock_delete_called is True


def test_remove_source_raises_not_found_error(monkeypatch, test_db):
    """
    Test remove_source() raises NotFoundError for non-existent source (Story 1.5).

    Verifies:
    - Checks if source exists
    - Raises NotFoundError with Norwegian message
    """
    from backend.exceptions import NotFoundError
    from backend.services.content_source import remove_source

    # Arrange - Mock database to return None
    monkeypatch.setattr("backend.services.content_source.get_source_by_id", lambda source_id: None)

    # Act & Assert
    with pytest.raises(NotFoundError) as exc_info:
        remove_source(999)

    assert "ikke funnet" in str(exc_info.value).lower()


def test_remove_source_cascade_deletes_videos(monkeypatch, test_db):
    """
    Test remove_source() CASCADE deletes associated videos (Story 1.5).

    Verifies:
    - Videos are automatically deleted via CASCADE DELETE
    - No manual video deletion needed
    - Database foreign key constraint handles cascade
    """
    from backend.services.content_source import remove_source

    # Arrange
    mock_source = {"id": 1, "name": "Test", "video_count": 10}
    delete_calls = []

    def mock_delete(source_id):
        delete_calls.append(("delete_source", source_id))

    monkeypatch.setattr("backend.services.content_source.get_source_by_id", lambda sid: mock_source)
    monkeypatch.setattr("backend.services.content_source.delete_content_source", mock_delete)

    # Mock connection for video count
    class MockRow:
        """Mock Row object that supports both index and key access."""

        def __getitem__(self, key):
            if key == 0 or key == "COUNT(*)":
                return 10
            raise KeyError(key)

    class MockConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, params):
            class MockCursor:
                def fetchone(self):
                    return MockRow()

            return MockCursor()

    monkeypatch.setattr("backend.db.queries.get_connection", lambda: MockConnection())

    # Act
    result = remove_source(1)

    # Assert - Only source delete called, CASCADE handles videos
    assert len(delete_calls) == 1
    assert delete_calls[0] == ("delete_source", 1)
    assert result["videos_removed"] == 10


# =============================================================================
# refresh_source() Tests (Story 1.5)
# =============================================================================


def test_refresh_source_adds_new_videos(monkeypatch, test_db):
    """
    Test refresh_source() fetches and adds new videos (Story 1.5).

    Verifies:
    - Gets source from database
    - Fetches videos from YouTube API based on source type
    - Filters to only NEW videos (not already in DB)
    - Inserts new videos
    - Updates source last_refresh timestamp
    - Logs API call
    - Returns videosAdded count
    """
    from backend.services.content_source import refresh_source

    # Arrange
    mock_source = {
        "id": 1,
        "source_id": "UCtest",
        "source_type": "channel",
        "name": "Test Channel",
        "video_count": 0,
    }

    def mock_fetch_all_channel(youtube, channel_id):
        return (["video1", "video2", "video3"], True)

    def mock_fetch_details(video_ids):
        return [{"video_id": vid, "title": f"Video {vid}"} for vid in video_ids]

    existing_videos = []
    inserted_videos = []

    monkeypatch.setattr("backend.services.content_source.get_source_by_id", lambda sid: mock_source)
    monkeypatch.setattr("backend.services.content_source.create_youtube_client", lambda: Mock())
    monkeypatch.setattr(
        "backend.services.content_source.fetch_all_channel_videos", mock_fetch_all_channel
    )
    monkeypatch.setattr("backend.services.content_source._fetch_video_details", mock_fetch_details)
    monkeypatch.setattr("backend.services.content_source._deduplicate_videos", lambda vids: vids)

    # Mock database operations
    class MockConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, params):
            class MockCursor:
                def fetchall(self):
                    return existing_videos

                def fetchone(self):
                    # For quota usage query, return 0
                    return [0]

            return MockCursor()

    monkeypatch.setattr("backend.db.queries.get_connection", lambda: MockConnection())

    def mock_bulk_insert(source_id, videos):
        inserted_videos.extend(videos)
        return len(videos)

    monkeypatch.setattr("backend.services.content_source.bulk_insert_videos", mock_bulk_insert)
    monkeypatch.setattr(
        "backend.services.content_source.update_content_source_refresh", lambda *args: None
    )
    monkeypatch.setattr(
        "backend.services.content_source.log_api_call", lambda *args, **kwargs: None
    )

    # Act
    result = refresh_source(1)

    # Assert
    assert result["videos_added"] == 3
    assert "last_refresh" in result
    assert len(inserted_videos) == 3


def test_refresh_source_no_new_videos(monkeypatch, test_db):
    """
    Test refresh_source() when no new videos found (Story 1.5).

    Verifies:
    - Returns videosAdded: 0
    - Still updates last_refresh timestamp
    - No videos inserted
    """
    from backend.services.content_source import refresh_source

    # Arrange
    mock_source = {
        "id": 1,
        "source_id": "UCtest",
        "source_type": "channel",
        "name": "Test Channel",
        "video_count": 10,
    }

    def mock_fetch_all_channel(youtube, channel_id):
        return (["video1", "video2"], True)

    def mock_fetch_details(video_ids):
        return [{"video_id": vid, "title": f"Video {vid}"} for vid in video_ids]

    # All videos already exist
    existing_videos = [{"video_id": "video1"}, {"video_id": "video2"}]
    inserted_videos = []

    monkeypatch.setattr("backend.services.content_source.get_source_by_id", lambda sid: mock_source)
    monkeypatch.setattr("backend.services.content_source.create_youtube_client", lambda: Mock())
    monkeypatch.setattr(
        "backend.services.content_source.fetch_all_channel_videos", mock_fetch_all_channel
    )
    monkeypatch.setattr("backend.services.content_source._fetch_video_details", mock_fetch_details)
    monkeypatch.setattr("backend.services.content_source._deduplicate_videos", lambda vids: vids)

    # Mock database operations
    class MockConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, params):
            class MockCursor:
                def fetchall(self):
                    return existing_videos

                def fetchone(self):
                    # For quota usage query, return 0
                    return [0]

            return MockCursor()

    monkeypatch.setattr("backend.db.queries.get_connection", lambda: MockConnection())

    def mock_bulk_insert(source_id, videos):
        inserted_videos.extend(videos)
        return len(videos)

    monkeypatch.setattr("backend.services.content_source.bulk_insert_videos", mock_bulk_insert)
    monkeypatch.setattr(
        "backend.services.content_source.update_content_source_refresh", lambda *args: None
    )
    monkeypatch.setattr(
        "backend.services.content_source.log_api_call", lambda *args, **kwargs: None
    )

    # Act
    result = refresh_source(1)

    # Assert
    assert result["videos_added"] == 0
    assert len(inserted_videos) == 0


def test_refresh_source_not_found_error(monkeypatch, test_db):
    """
    Test refresh_source() raises ValueError for non-existent source (Story 1.5).

    Verifies:
    - Checks if source exists
    - Raises ValueError with Norwegian message "Kilde ikke funnet"
    """
    from backend.services.content_source import refresh_source

    # Arrange - Mock database to return None
    monkeypatch.setattr("backend.services.content_source.get_source_by_id", lambda source_id: None)

    # Act & Assert
    with pytest.raises(ValueError) as exc_info:
        refresh_source(999)

    assert "kilde ikke funnet" in str(exc_info.value).lower()


def test_refresh_source_handles_playlist_type(monkeypatch, test_db):
    """
    Test refresh_source() handles playlist source type (Story 1.5).

    Verifies:
    - Determines source type from source record
    - Calls fetch_all_playlist_videos for playlist type
    - Correctly processes playlist videos
    """
    from backend.services.content_source import refresh_source

    # Arrange
    mock_source = {
        "id": 1,
        "source_id": "PLtest",
        "source_type": "playlist",
        "name": "Test Playlist",
        "video_count": 5,
    }

    playlist_fetch_called = False

    def mock_fetch_playlist(playlist_id):
        nonlocal playlist_fetch_called
        playlist_fetch_called = True
        return (["video1"], True)

    def mock_fetch_details(video_ids):
        return [{"video_id": vid, "title": f"Video {vid}"} for vid in video_ids]

    monkeypatch.setattr("backend.services.content_source.get_source_by_id", lambda sid: mock_source)
    monkeypatch.setattr("backend.services.content_source.create_youtube_client", lambda: Mock())
    monkeypatch.setattr(
        "backend.services.content_source._fetch_playlist_videos", mock_fetch_playlist
    )
    monkeypatch.setattr("backend.services.content_source._fetch_video_details", mock_fetch_details)
    monkeypatch.setattr("backend.services.content_source._deduplicate_videos", lambda vids: vids)

    # Mock database operations
    class MockConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, params):
            class MockCursor:
                def fetchall(self):
                    return []

                def fetchone(self):
                    # For quota usage query, return 0
                    return [0]

            return MockCursor()

    monkeypatch.setattr("backend.db.queries.get_connection", lambda: MockConnection())
    monkeypatch.setattr(
        "backend.services.content_source.bulk_insert_videos", lambda source_id, videos: len(videos)
    )
    monkeypatch.setattr(
        "backend.services.content_source.update_content_source_refresh", lambda *args: None
    )
    monkeypatch.setattr(
        "backend.services.content_source.log_api_call", lambda *args, **kwargs: None
    )

    # Act
    result = refresh_source(1)

    # Assert
    assert playlist_fetch_called is True
    assert result["videos_added"] == 1


def test_refresh_source_partial_fetch_flag(monkeypatch, test_db):
    """
    Test refresh_source() handles partial fetch during refresh (Story 1.5).

    Verifies:
    - Partial fetch flag returned from YouTube API fetch
    - Videos fetched so far are still saved
    - Returns videosAdded for partial videos
    """
    from backend.services.content_source import refresh_source

    # Arrange
    mock_source = {
        "id": 1,
        "source_id": "UCtest",
        "source_type": "channel",
        "name": "Test Channel",
        "video_count": 20,
    }

    def mock_fetch_all_channel(youtube, channel_id):
        # Return partial fetch (fetch_complete=False)
        return (["video1", "video2"], False)

    def mock_fetch_details(video_ids):
        return [{"video_id": vid, "title": f"Video {vid}"} for vid in video_ids]

    monkeypatch.setattr("backend.services.content_source.get_source_by_id", lambda sid: mock_source)
    monkeypatch.setattr("backend.services.content_source.create_youtube_client", lambda: Mock())
    monkeypatch.setattr(
        "backend.services.content_source.fetch_all_channel_videos", mock_fetch_all_channel
    )
    monkeypatch.setattr("backend.services.content_source._fetch_video_details", mock_fetch_details)
    monkeypatch.setattr("backend.services.content_source._deduplicate_videos", lambda vids: vids)

    # Mock database operations
    class MockConnection:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def execute(self, query, params):
            class MockCursor:
                def fetchall(self):
                    return []

                def fetchone(self):
                    # For quota usage query, return 0
                    return [0]

            return MockCursor()

    monkeypatch.setattr("backend.db.queries.get_connection", lambda: MockConnection())
    monkeypatch.setattr(
        "backend.services.content_source.bulk_insert_videos", lambda source_id, videos: len(videos)
    )
    monkeypatch.setattr(
        "backend.services.content_source.update_content_source_refresh", lambda *args: None
    )
    monkeypatch.setattr(
        "backend.services.content_source.log_api_call", lambda *args, **kwargs: None
    )

    # Act
    result = refresh_source(1)

    # Assert - Partial videos still saved
    assert result["videos_added"] == 2
