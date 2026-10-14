# ABOUTME: Opens the app's SQLite database and creates the stores and summaries tables.
# ABOUTME: Connections autocommit each statement and are safe to share across Streamlit threads.
import sqlite3
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS stores (
    store_id        INTEGER PRIMARY KEY,
    name            TEXT NOT NULL,
    name_normalized TEXT NOT NULL UNIQUE,
    phone           TEXT NOT NULL,
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS conversation_summaries (
    conversation_summary_id INTEGER PRIMARY KEY,
    thread_id               TEXT NOT NULL,
    summary                 TEXT NOT NULL,
    end_reason              TEXT NOT NULL CHECK (end_reason IN ('user_done', 'off_topic')),
    created_at              TEXT NOT NULL
);
"""


def connect(path: Path) -> sqlite3.Connection:
    """
    Open the app database, creating its directory and schema if needed.

    Args:
        path: Location of the SQLite file.

    Returns:
        An autocommit connection whose rows support access by column name.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    create_schema(conn)
    return conn


def create_schema(conn: sqlite3.Connection) -> None:
    """Create the app tables if they do not exist yet."""
    conn.executescript(SCHEMA)
