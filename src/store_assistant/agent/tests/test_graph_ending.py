# ABOUTME: Tests that conversations end with a saved summary, by request or after off-topic strikes.
# ABOUTME: Drives the real graph and LLM through the turn handler and checks the summaries table.
import sqlite3
from collections.abc import Callable
from typing import Any

import pytest

from store_assistant.conversation.turns import ConversationEndedError, TurnHandler
from store_assistant.storage.summaries import SummaryRepository

pytestmark = pytest.mark.llm

ThreadState = Callable[[str], dict[str, Any]]


def test_saying_done_ends_with_saved_summary(turns: TurnHandler, db: sqlite3.Connection) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "hi")

    result = turns.send(thread_id, "I'm done, thanks")

    saved = SummaryRepository(db).find_by_thread(thread_id)
    assert result.ended is True
    assert saved is not None
    assert saved.end_reason == "user_done"
    assert saved.summary.strip()
    assert result.messages[-1].content == saved.summary


def test_ended_conversation_refuses_more_messages(turns: TurnHandler) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "I'm done")

    with pytest.raises(ConversationEndedError):
        turns.send(thread_id, "hi again")


def test_three_off_topic_messages_end_the_conversation(
    turns: TurnHandler, db: sqlite3.Connection
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "who won the world cup?")
    turns.send(thread_id, "write me a poem about cats")

    result = turns.send(thread_id, "what's the weather in Paris?")

    saved = SummaryRepository(db).find_by_thread(thread_id)
    assert result.ended is True
    assert saved is not None
    assert saved.end_reason == "off_topic"


def test_summary_counts_off_topic_messages(
    turns: TurnHandler, db: sqlite3.Connection, thread_state: ThreadState
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "who won the world cup?")
    turns.send(thread_id, "save Costco, number 555-876-5432")
    turns.send(thread_id, "tell me a joke")
    turns.send(thread_id, "write me a poem about cats")

    turns.send(thread_id, "I'm done")

    kinds = [a["kind"] for a in thread_state(thread_id)["actions"]]
    saved = SummaryRepository(db).find_by_thread(thread_id)
    assert kinds.count("off_topic_message") == 3
    assert saved is not None
    assert "off-topic" in saved.summary
    assert "3" in saved.summary or "three" in saved.summary.lower()


def test_on_topic_message_between_strikes_keeps_conversation_open(
    turns: TurnHandler, db: sqlite3.Connection
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "who won the world cup?")
    turns.send(thread_id, "write me a poem about cats")
    turns.send(thread_id, "what can you do?")
    turns.send(thread_id, "tell me a joke")

    result = turns.send(thread_id, "what's the weather in Paris?")

    assert result.ended is False
    assert SummaryRepository(db).find_by_thread(thread_id) is None


def test_summary_states_the_recorded_facts(turns: TurnHandler, db: sqlite3.Connection) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "save Costco, number 555-876-5432")

    turns.send(thread_id, "I'm done")

    saved = SummaryRepository(db).find_by_thread(thread_id)
    assert saved is not None
    assert "Costco" in saved.summary
    assert "+15558765432" in saved.summary


def test_summary_ignores_stores_only_mentioned_in_chat(
    turns: TurnHandler, db: sqlite3.Connection
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "my favourite store is Walmart, do you like it?")

    turns.send(thread_id, "I'm done")

    saved = SummaryRepository(db).find_by_thread(thread_id)
    assert saved is not None
    assert "Walmart" not in saved.summary
