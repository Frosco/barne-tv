"""
Integration test fixtures.

Provides pytest fixtures for integration testing with real YouTube API.
"""

import os

# Disable rate limiting for all integration tests (must be set before FastAPI imports)
os.environ["TESTING"] = "true"

import sqlite3
from pathlib import Path
import pytest
from contextlib import contextmanager
from fastapi.testclient import TestClient

from backend.main import app


@pytest.fixture
def test_db():
    """
    Create in-memory test database with full schema.

    Yields a SQLite connection with the complete database schema loaded.
    Database is automatically cleaned up after test completes.

    Usage:
        def test_something(test_db):
            cursor = test_db.execute("SELECT * FROM videos")
            assert cursor.fetchall() == []
    """
    conn = sqlite3.connect(":memory:", check_same_thread=False)
    conn.row_factory = sqlite3.Row

    # Load and execute schema
    schema_path = Path(__file__).parent.parent.parent / "backend" / "db" / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    yield conn

    conn.close()


@pytest.fixture
def test_client(test_db, monkeypatch):
    """
    Create FastAPI TestClient with test database monkey-patched.

    The test database connection is monkey-patched into the queries module,
    so all API calls and database queries use the in-memory test database.

    Usage:
        def test_api_endpoint(test_client, test_db):
            # Setup test data in test_db
            # ...
            response = test_client.get("/api/videos?count=9")
            assert response.status_code == 200
    """
    from backend.db import queries
    from backend import routes

    @contextmanager
    def mock_get_connection():
        """Return the test database connection."""
        yield test_db

    # Replace get_connection in both queries module and routes module
    monkeypatch.setattr(queries, "get_connection", mock_get_connection)
    monkeypatch.setattr(routes, "get_connection", mock_get_connection)

    # Create test client with base_url to satisfy TrustedHostMiddleware
    client = TestClient(app, base_url="http://localhost")

    yield client
