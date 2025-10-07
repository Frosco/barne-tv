"""
Database query functions and connection management.

TIER 2 Rule 7: Always use context manager for database access.
"""

import sqlite3
from contextlib import contextmanager

from backend.config import DATABASE_PATH


@contextmanager
def get_connection():
    """
    Context manager for database connections.

    Usage:
        with get_connection() as conn:
            result = conn.execute("SELECT ...").fetchall()

    TIER 2 Rule 7: Always use context manager, even for reads.
    Provides automatic commit/rollback on errors.
    """
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
    conn.execute("PRAGMA foreign_keys = ON")  # Enforce foreign key constraints

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()
