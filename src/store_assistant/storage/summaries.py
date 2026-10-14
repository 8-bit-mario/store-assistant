# ABOUTME: Saves and finds the summary written when a conversation ends.
# ABOUTME: One summary per thread, linked to LangGraph and LangSmith by thread_id.
import sqlite3
from dataclasses import dataclass
from typing import Literal

from store_assistant.clock import Clock, utc_now

EndReason = Literal["user_done", "off_topic"]


@dataclass(frozen=True)
class ConversationSummary:
    """A saved end-of-conversation summary."""

    conversation_summary_id: int
    thread_id: str
    summary: str
    end_reason: EndReason
    created_at: str


class SummaryRepository:
    """Conversation summaries in the app database."""

    def __init__(self, conn: sqlite3.Connection, clock: Clock = utc_now) -> None:
        self._conn = conn
        self._clock = clock

    def add(self, thread_id: str, summary: str, end_reason: EndReason) -> ConversationSummary:
        """Save the summary of a finished conversation."""
        cursor = self._conn.execute(
            "INSERT INTO conversation_summaries (thread_id, summary, end_reason, created_at) "
            "VALUES (?, ?, ?, ?)",
            (thread_id, summary, end_reason, self._clock().isoformat()),
        )
        row = self._conn.execute(
            "SELECT * FROM conversation_summaries WHERE conversation_summary_id = ?",
            (cursor.lastrowid,),
        ).fetchone()
        return ConversationSummary(**dict(row))

    def find_by_thread(self, thread_id: str) -> ConversationSummary | None:
        """Find the summary saved for a conversation thread."""
        row = self._conn.execute(
            "SELECT * FROM conversation_summaries WHERE thread_id = ? "
            "ORDER BY conversation_summary_id DESC LIMIT 1",
            (thread_id,),
        ).fetchone()
        return ConversationSummary(**dict(row)) if row else None
