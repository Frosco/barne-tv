"""
Integration tests for warning endpoints (Story 4.2).

Tests POST /api/warnings/log and GET /admin/warnings endpoints.
"""

import pytest
from datetime import datetime, timezone, timedelta


@pytest.mark.integration
def test_log_warning_success(test_client, test_db):
    """
    Test successful warning logging via POST /api/warnings/log.

    No authentication required (child interface is public).
    """
    # Arrange
    warning_data = {
        "warningType": "10min",
        "shownAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    # Act
    response = test_client.post("/api/warnings/log", json=warning_data)

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True

    # Verify warning logged in database
    cursor = test_db.execute("SELECT * FROM limit_warnings")
    warnings = cursor.fetchall()
    assert len(warnings) == 1
    assert warnings[0]["warning_type"] == "10min"


@pytest.mark.integration
def test_log_warning_invalid_type(test_client):
    """
    Test warning logging with invalid warning type.

    Should reject invalid types (must be '10min', '5min', or '2min').
    """
    # Arrange
    warning_data = {
        "warningType": "15min",  # Invalid type
        "shownAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }

    # Act
    response = test_client.post("/api/warnings/log", json=warning_data)

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "Advarseltype må være" in data["message"]


@pytest.mark.integration
def test_log_warning_invalid_timestamp_format(test_client):
    """
    Test warning logging with invalid timestamp format.

    Should reject non-ISO 8601 timestamps.
    """
    # Arrange
    warning_data = {
        "warningType": "10min",
        "shownAt": "not-a-valid-timestamp",  # Clearly invalid
    }

    # Act
    response = test_client.post("/api/warnings/log", json=warning_data)

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "tidsstempel-format" in data["message"]


@pytest.mark.integration
def test_get_warnings_requires_auth(test_client):
    """
    Test GET /admin/warnings requires authentication.

    Should return 401 if no valid session.
    """
    # Act
    response = test_client.get("/admin/warnings")

    # Assert
    assert response.status_code == 401
    data = response.json()
    # FastAPI returns 'detail' key for HTTPException
    assert "detail" in data


@pytest.mark.integration
def test_get_warnings_success(test_client, test_db):
    """
    Test successful warning retrieval for admin.

    Requires authentication.
    """
    # Arrange: Create admin session
    from backend.auth import create_session

    session_id = create_session()

    # Log some warnings to database
    from backend.db.queries import log_warning

    today = datetime.now(timezone.utc)
    log_warning("10min", today.isoformat().replace("+00:00", "Z"), conn=test_db)
    log_warning(
        "5min", (today + timedelta(minutes=5)).isoformat().replace("+00:00", "Z"), conn=test_db
    )

    # Act
    response = test_client.get(
        "/admin/warnings",
        cookies={"session_id": session_id},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert "warnings" in data
    assert len(data["warnings"]) == 2
    assert data["warnings"][0]["warningType"] == "10min"
    assert data["warnings"][1]["warningType"] == "5min"
    assert "date" in data


@pytest.mark.integration
def test_get_warnings_with_specific_date(test_client, test_db):
    """
    Test warning retrieval with specific date parameter.
    """
    # Arrange: Create admin session
    from backend.auth import create_session

    session_id = create_session()

    # Log warnings on different days
    from backend.db.queries import log_warning

    today = datetime.now(timezone.utc)
    yesterday = today - timedelta(days=1)

    log_warning("10min", today.isoformat().replace("+00:00", "Z"), conn=test_db)
    log_warning("5min", yesterday.isoformat().replace("+00:00", "Z"), conn=test_db)

    # Act: Query for yesterday's warnings
    yesterday_str = yesterday.date().isoformat()
    response = test_client.get(
        f"/admin/warnings?date={yesterday_str}",
        cookies={"session_id": session_id},
    )

    # Assert: Should only return yesterday's warning
    assert response.status_code == 200
    data = response.json()
    assert len(data["warnings"]) == 1
    assert data["warnings"][0]["warningType"] == "5min"
    assert data["date"] == yesterday_str


@pytest.mark.integration
def test_get_warnings_invalid_date_format(test_client):
    """
    Test warning retrieval with invalid date format.
    """
    # Arrange: Create admin session
    from backend.auth import create_session

    session_id = create_session()

    # Act
    response = test_client.get(
        "/admin/warnings?date=01-03-2025",  # Invalid format
        cookies={"session_id": session_id},
    )

    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert "datoformat" in data["message"]


@pytest.mark.integration
def test_get_warnings_empty_day(test_client):
    """
    Test warning retrieval for day with no warnings.

    Should return empty array, not error.
    """
    # Arrange: Create admin session
    from backend.auth import create_session

    session_id = create_session()

    # Act: Query for a day with no warnings
    future_date = (datetime.now(timezone.utc) + timedelta(days=10)).date().isoformat()
    response = test_client.get(
        f"/admin/warnings?date={future_date}",
        cookies={"session_id": session_id},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["warnings"] == []
    assert data["date"] == future_date


@pytest.mark.integration
def test_warning_ordering_chronological(test_client, test_db):
    """
    Test warnings are returned in chronological order (oldest first).
    """
    # Arrange: Create admin session
    from backend.auth import create_session

    session_id = create_session()

    # Log warnings in reverse chronological order
    from backend.db.queries import log_warning

    today = datetime.now(timezone.utc)
    time_5min = (today - timedelta(minutes=5)).isoformat().replace("+00:00", "Z")
    time_10min = (today - timedelta(minutes=10)).isoformat().replace("+00:00", "Z")
    time_2min = (today - timedelta(minutes=2)).isoformat().replace("+00:00", "Z")

    log_warning("5min", time_5min, conn=test_db)
    log_warning("10min", time_10min, conn=test_db)
    log_warning("2min", time_2min, conn=test_db)

    # Act
    response = test_client.get(
        "/admin/warnings",
        cookies={"session_id": session_id},
    )

    # Assert: Should be ordered by shownAt ascending (oldest first)
    assert response.status_code == 200
    data = response.json()
    assert len(data["warnings"]) == 3
    assert data["warnings"][0]["warningType"] == "10min"  # Oldest
    assert data["warnings"][1]["warningType"] == "5min"
    assert data["warnings"][2]["warningType"] == "2min"  # Newest
