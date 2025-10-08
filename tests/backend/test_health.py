"""
Test health endpoint.

Verifies the FastAPI health check endpoint returns correct response.
"""

from fastapi.testclient import TestClient
from backend.main import app


def test_health_endpoint_returns_ok():
    """Test that health endpoint returns success response."""
    # Arrange
    client = TestClient(app)

    # Act
    response = client.get("/health")

    # Assert
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_endpoint_returns_json():
    """Test that health endpoint returns JSON content type."""
    # Arrange
    client = TestClient(app)

    # Act
    response = client.get("/health")

    # Assert
    assert response.headers["content-type"] == "application/json"
