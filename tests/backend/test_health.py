"""
Test health endpoint.

Verifies the FastAPI health check endpoint returns correct response.
"""

from fastapi.testclient import TestClient
from backend.main import app


def test_health_endpoint_returns_ok():
    """
    Test that health endpoint returns success response with database connectivity.

    Story 5.3 AC 17: Health endpoint must verify database connectivity.
    """
    # Arrange
    # Story 2.3: TestClient needs base_url for TrustedHostMiddleware
    client = TestClient(app, base_url="http://localhost")

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "connected"}


def test_health_endpoint_returns_json():
    """Test that health endpoint returns JSON content type."""
    # Arrange
    # Story 2.3: TestClient needs base_url for TrustedHostMiddleware
    client = TestClient(app, base_url="http://localhost")

    # Act
    response = client.get("/health")

    # Assert
    assert response.headers["content-type"] == "application/json"
