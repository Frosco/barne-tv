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
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row

    # Load and execute schema
    schema_path = Path(__file__).parent.parent.parent / "backend" / "db" / "schema.sql"
    with open(schema_path, "r") as f:
        conn.executescript(f.read())

    yield conn

    conn.close()
