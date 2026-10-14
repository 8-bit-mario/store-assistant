# ABOUTME: Tests for opening the app database and creating its schema.
# ABOUTME: Checks tables, constraints and idempotent schema creation on real SQLite files.
import sqlite3
from pathlib import Path

import pytest

from store_assistant.storage.database import connect, create_schema


def _table_names(conn: sqlite3.Connection) -> set[str]:
    rows = conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()
    return {row["name"] for row in rows}


def test_connect_creates_both_tables(db: sqlite3.Connection) -> None:
    assert {"stores", "conversation_summaries"} <= _table_names(db)


def test_connect_creates_missing_parent_directory(tmp_path: Path) -> None:
    conn = connect(tmp_path / "nested" / "dir" / "app.sqlite")
    conn.close()

    assert (tmp_path / "nested" / "dir" / "app.sqlite").exists()


def test_create_schema_is_idempotent(db: sqlite3.Connection) -> None:
    create_schema(db)

    assert {"stores", "conversation_summaries"} <= _table_names(db)


def test_normalized_store_name_is_unique(db: sqlite3.Connection) -> None:
    insert = (
        "INSERT INTO stores (name, name_normalized, phone, created_at, updated_at) "
        "VALUES (?, ?, ?, '2026-10-13T00:00:00+00:00', '2026-10-13T00:00:00+00:00')"
    )
    db.execute(insert, ("Costco", "costco", "+15552345678"))

    with pytest.raises(sqlite3.IntegrityError):
        db.execute(insert, ("COSTCO", "costco", "+15558765432"))


def test_end_reason_is_restricted(db: sqlite3.Connection) -> None:
    with pytest.raises(sqlite3.IntegrityError):
        db.execute(
            "INSERT INTO conversation_summaries (thread_id, summary, end_reason, created_at) "
            "VALUES ('t1', 'text', 'bored', '2026-10-13T00:00:00+00:00')"
        )
