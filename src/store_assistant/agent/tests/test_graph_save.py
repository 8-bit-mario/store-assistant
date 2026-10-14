# ABOUTME: Tests the save-store flow: prompting for missing details, phone reprompts and persisting.
# ABOUTME: Drives the real graph and LLM through the turn handler and checks the stores table.
import sqlite3

import pytest

from store_assistant.conversation.turns import TurnHandler
from store_assistant.storage.stores import StoreRepository

pytestmark = pytest.mark.llm


def test_one_shot_save_persists_normalized_phone(
    turns: TurnHandler, db: sqlite3.Connection
) -> None:
    thread_id = turns.start()

    result = turns.send(thread_id, "save Trader Joe's, the number is (555) 234-5678")

    saved = StoreRepository(db).find_by_name("Trader Joe's")
    assert saved is not None
    assert saved.phone == "+15552345678"
    assert result.pending is None
    assert "+15552345678" in result.messages[-1].content


def test_missing_details_are_prompted_and_invalid_phone_reprompted(
    turns: TurnHandler, db: sqlite3.Connection
) -> None:
    thread_id = turns.start()

    first = turns.send(thread_id, "I want to save a store")
    second = turns.send(thread_id, "Costco")
    third = turns.send(thread_id, "12345")
    final = turns.send(thread_id, "(555) 876-5432")

    assert first.pending is not None and first.pending.kind == "store_name"
    assert second.pending is not None and second.pending.kind == "phone"
    assert third.pending is not None and third.pending.kind == "phone"
    assert third.pending.prompt != second.pending.prompt
    assert final.pending is None
    saved = StoreRepository(db).find_by_name("Costco")
    assert saved is not None
    assert saved.phone == "+15558765432"


def test_nothing_is_saved_while_a_prompt_is_pending(
    turns: TurnHandler, db: sqlite3.Connection
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "I want to save a store")

    pending = turns.send(thread_id, "Costco")

    assert pending.pending is not None
    assert StoreRepository(db).find_by_name("Costco") is None


def test_transcript_records_the_whole_exchange(turns: TurnHandler) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "I want to save a store")
    turns.send(thread_id, "Costco")
    turns.send(thread_id, "12345")

    result = turns.send(thread_id, "(555) 876-5432")

    user_texts = [m.content for m in result.messages if m.type == "human"]
    assert user_texts == ["I want to save a store", "Costco", "12345", "(555) 876-5432"]
    assert "+15558765432" in result.messages[-1].content


def test_pending_prompt_carries_the_exchange_so_far(turns: TurnHandler) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "I want to save a store")

    result = turns.send(thread_id, "Costco")

    assert result.pending is not None
    assert [(e["role"], e["text"]) for e in result.pending.exchange][-1] == ("user", "Costco")


def test_too_long_store_name_is_reprompted(turns: TurnHandler) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "I want to save a store")

    result = turns.send(thread_id, "x" * 101)

    assert result.pending is not None
    assert result.pending.kind == "store_name"
