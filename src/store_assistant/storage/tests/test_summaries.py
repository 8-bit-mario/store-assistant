# ABOUTME: Tests for saving and finding conversation summaries in a real SQLite database.
# ABOUTME: Covers round-trips, misses and the end_reason constraint.
import sqlite3
from datetime import UTC, datetime
from typing import Any

import pytest

from store_assistant.storage.summaries import SummaryRepository

FIXED_NOW = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


@pytest.fixture
def summaries(db: sqlite3.Connection) -> SummaryRepository:
    return SummaryRepository(db, clock=lambda: FIXED_NOW)


def test_added_summary_is_found_by_thread(summaries: SummaryRepository) -> None:
    summaries.add("thread-1", "User saved Costco.", "user_done")

    found = summaries.find_by_thread("thread-1")

    assert found is not None
    assert found.thread_id == "thread-1"
    assert found.summary == "User saved Costco."
    assert found.end_reason == "user_done"
    assert found.created_at == "2026-10-13T12:00:00+00:00"


def test_summaries_are_isolated_by_thread(summaries: SummaryRepository) -> None:
    summaries.add("thread-1", "First.", "user_done")
    summaries.add("thread-2", "Second.", "off_topic")

    found = summaries.find_by_thread("thread-2")

    assert found is not None
    assert found.summary == "Second."
    assert found.end_reason == "off_topic"


def test_find_unknown_thread_returns_none(summaries: SummaryRepository) -> None:
    assert summaries.find_by_thread("missing") is None


def test_invalid_end_reason_is_rejected(summaries: SummaryRepository) -> None:
    bad_reason: Any = "bored"

    with pytest.raises(sqlite3.IntegrityError):
        summaries.add("thread-1", "text", bad_reason)
