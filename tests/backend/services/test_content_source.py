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
