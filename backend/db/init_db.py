"""
Database initialization script.
Run once on first setup or to reset database.

Usage: python backend/db/init_db.py <admin_password>
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

DATABASE_PATH = os.getenv("DATABASE_PATH", "/opt/youtube-viewer/data/app.db")
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def init_database():
    """Initialize database with schema.

    Note: Uses manual connection management as this is a bootstrap script
    that runs before the backend module is configured.
    """
    os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        # Enable WAL mode
        conn.execute("PRAGMA journal_mode=WAL")

        with open(SCHEMA_PATH) as f:
            schema_sql = f.read()

        conn.executescript(schema_sql)
        conn.commit()
        print(f"Database initialized at {DATABASE_PATH}")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def set_admin_password(password: str):
    """Set initial admin password with proper JSON encoding.

    Args:
        password: Plain text admin password to hash and store

    TIER 1 Rule 4: Must use bcrypt hashing via passlib

    Note: Uses manual connection management as this is a bootstrap script.
    """
    from passlib.hash import bcrypt

    hashed = bcrypt.hash(password)

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        conn.execute(
            "UPDATE settings SET value = ?, updated_at = datetime('now') WHERE key = 'admin_password_hash'",
            (json.dumps(hashed),),  # Proper JSON encoding
        )
        conn.commit()
        print("Admin password set")
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python init_db.py <admin_password>")
        sys.exit(1)

    init_database()
    set_admin_password(sys.argv[1])
