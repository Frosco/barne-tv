"""
Test health endpoint.

Verifies the FastAPI health check endpoint returns correct response.
"""

from datetime import datetime, timezone
from fastapi.testclient import TestClient
from backend.main import app


def test_health_endpoint_returns_ok():
    """
    Test that health endpoint returns success response with database connectivity.

    Story 5.3 AC 17: Health endpoint must verify database connectivity.
    Story 5.4 AC 1-2: Health endpoint must include timestamp in ISO 8601 UTC format.
    """
    # Arrange
    # Story 2.3: TestClient needs base_url for TrustedHostMiddleware
    client = TestClient(app, base_url="http://localhost")

    # Act
    before_request = datetime.now(timezone.utc)
    response = client.get("/health")
    after_request = datetime.now(timezone.utc)

    # Assert
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] == "connected"
    assert "timestamp" in data

    # Verify timestamp is valid ISO 8601 UTC format and recent
    timestamp = datetime.fromisoformat(data["timestamp"])
    assert before_request <= timestamp <= after_request
    assert timestamp.tzinfo is not None  # Must have timezone info


def test_health_endpoint_returns_json():
    """Test that health endpoint returns JSON content type."""
    # Arrange
    # Story 2.3: TestClient needs base_url for TrustedHostMiddleware
    client = TestClient(app, base_url="http://localhost")

    # Act
    response = client.get("/health")

    # Assert
    assert response.headers["content-type"] == "application/json"
