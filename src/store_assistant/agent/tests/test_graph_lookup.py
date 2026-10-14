# ABOUTME: Tests the passphrase-gated lookup flow, including that the secret is never persisted.
# ABOUTME: Drives the real graph and LLM through the turn handler with a pre-saved store.
import sqlite3
from collections.abc import Callable
from pathlib import Path
from typing import Any

import pytest

from store_assistant.conversation.turns import TurnHandler
from store_assistant.storage.stores import StoreRepository
from store_assistant.tests.support import TEST_PASSPHRASE

pytestmark = pytest.mark.llm

WRONG_ATTEMPT = "wrong-attempt-qx9"


@pytest.fixture(autouse=True)
def saved_store(db: sqlite3.Connection) -> None:
    StoreRepository(db).add("Trader Joe's", "+15552345678")


ThreadState = Callable[[str], dict[str, Any]]


def _actions(thread_state: ThreadState, thread_id: str) -> list[str]:
    return [a["kind"] for a in thread_state(thread_id).get("actions", [])]


def test_correct_passphrase_reveals_phone(turns: TurnHandler, thread_state: ThreadState) -> None:
    thread_id = turns.start()

    asked = turns.send(thread_id, "what's the number for Trader Joe's?")
    result = turns.send(thread_id, TEST_PASSPHRASE)

    assert asked.pending is not None and asked.pending.kind == "passphrase"
    assert result.pending is None
    assert "+15552345678" in result.messages[-1].content
    assert _actions(thread_state, thread_id) == ["lookup_found"]


def test_missing_store_name_is_asked_first(turns: TurnHandler) -> None:
    thread_id = turns.start()

    asked = turns.send(thread_id, "I want to look up a store")
    then = turns.send(thread_id, "Trader Joe's")

    assert asked.pending is not None and asked.pending.kind == "store_name"
    assert then.pending is not None and then.pending.kind == "passphrase"


def test_wrong_then_correct_passphrase_reveals_phone(turns: TurnHandler) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "what's the number for Trader Joe's?")

    retry = turns.send(thread_id, WRONG_ATTEMPT)
    result = turns.send(thread_id, TEST_PASSPHRASE)

    assert retry.pending is not None and retry.pending.kind == "passphrase"
    assert "+15552345678" in result.messages[-1].content


def test_three_wrong_passphrases_cancel_the_lookup(
    turns: TurnHandler, thread_state: ThreadState
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "what's the number for Trader Joe's?")
    turns.send(thread_id, WRONG_ATTEMPT)
    turns.send(thread_id, WRONG_ATTEMPT)

    result = turns.send(thread_id, WRONG_ATTEMPT)

    assert result.pending is None
    assert result.ended is False
    assert "+15552345678" not in " ".join(str(m.content) for m in result.messages)
    assert _actions(thread_state, thread_id) == ["lookup_cancelled_passphrase"]


def test_unknown_store_is_reported_as_not_found(
    turns: TurnHandler, thread_state: ThreadState
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "what's the number for Costco?")

    result = turns.send(thread_id, TEST_PASSPHRASE)

    assert result.pending is None
    assert "Costco" in result.messages[-1].content
    assert _actions(thread_state, thread_id) == ["lookup_not_found"]


def test_passphrase_and_attempts_are_never_persisted(turns: TurnHandler, tmp_path: Path) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "what's the number for Trader Joe's?")
    turns.send(thread_id, WRONG_ATTEMPT)
    turns.send(thread_id, TEST_PASSPHRASE)

    stored = b"".join(path.read_bytes() for path in tmp_path.iterdir() if path.is_file())
    assert TEST_PASSPHRASE.encode() not in stored
    assert WRONG_ATTEMPT.encode() not in stored
    # The scan sees conversation content (including SQLite WAL files), so absence is meaningful.
    assert b"what's the number for Trader Joe's?" in stored


@pytest.mark.parametrize("before", [[], ["I want to save a store", "Costco"]])
def test_passphrase_typed_outside_a_passphrase_prompt_is_never_persisted(
    turns: TurnHandler, tmp_path: Path, before: list[str]
) -> None:
    thread_id = turns.start()
    for text in before:
        turns.send(thread_id, text)

    result = turns.send(thread_id, TEST_PASSPHRASE)

    stored = b"".join(path.read_bytes() for path in tmp_path.iterdir() if path.is_file())
    assert TEST_PASSPHRASE.encode() not in stored
    assert all(TEST_PASSPHRASE not in str(m.content) for m in result.messages)


@pytest.mark.parametrize("request_text", ["look up store abc", "find abc store"])
def test_lookup_finds_store_saved_without_the_word_store(
    turns: TurnHandler, db: sqlite3.Connection, request_text: str
) -> None:
    StoreRepository(db).add("abc", "+15558765432")
    thread_id = turns.start()
    turns.send(thread_id, request_text)

    result = turns.send(thread_id, TEST_PASSPHRASE)

    assert "+15558765432" in result.messages[-1].content
