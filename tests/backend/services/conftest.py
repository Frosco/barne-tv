"""Fixtures for backend services tests."""

import pytest
from contextlib import contextmanager


@pytest.fixture
def test_db_with_patch(test_db, monkeypatch):
    """
    Test database with get_connection monkey-patched.

    This fixture provides an in-memory test database AND patches the
    backend.db.queries.get_connection() function to use this database.

    Use this for integration tests that call service functions directly
    (like calculate_engagement_scores() or get_videos_for_grid()).

    Usage:
        def test_something(test_db_with_patch):
            test_db = test_db_with_patch
            # Set up test data
            test_db.execute("INSERT INTO ...")
            # Call service function (it will use test_db)
            result = calculate_engagement_scores(["video_1"])
    """
    from backend.db import queries

    @contextmanager
    def mock_get_connection():
        yield test_db

    monkeypatch.setattr(queries, "get_connection", mock_get_connection)

    return test_db
