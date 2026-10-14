# ABOUTME: Tests that saving an existing store name asks before replacing its phone.
# ABOUTME: Drives the real graph and LLM through the turn handler with a pre-saved store.
import sqlite3

import pytest

from store_assistant.conversation.turns import TurnHandler
from store_assistant.storage.stores import StoreRepository

pytestmark = pytest.mark.llm

ORIGINAL_PHONE = "+15552345678"


@pytest.fixture
def stores(db: sqlite3.Connection) -> StoreRepository:
    repository = StoreRepository(db)
    repository.add("Costco", ORIGINAL_PHONE)
    return repository


def _save_costco_again(turns: TurnHandler, thread_id: str) -> None:
    result = turns.send(thread_id, "save Costco with number 555-876-5432")
    assert result.pending is not None
    assert result.pending.kind == "confirm_overwrite"


def test_yes_replaces_the_phone(turns: TurnHandler, stores: StoreRepository) -> None:
    thread_id = turns.start()
    _save_costco_again(turns, thread_id)

    result = turns.send(thread_id, "yes")

    costco = stores.find_by_name("Costco")
    assert costco is not None and costco.phone == "+15558765432"
    assert result.pending is None


def test_no_keeps_the_original_phone(turns: TurnHandler, stores: StoreRepository) -> None:
    thread_id = turns.start()
    _save_costco_again(turns, thread_id)

    result = turns.send(thread_id, "no")

    costco = stores.find_by_name("Costco")
    assert costco is not None and costco.phone == ORIGINAL_PHONE
    assert result.pending is None


def test_unclear_answer_asks_again(turns: TurnHandler, stores: StoreRepository) -> None:
    thread_id = turns.start()
    _save_costco_again(turns, thread_id)

    result = turns.send(thread_id, "maybe")

    assert result.pending is not None
    assert result.pending.kind == "confirm_overwrite"
    costco = stores.find_by_name("Costco")
    assert costco is not None and costco.phone == ORIGINAL_PHONE


def test_name_differing_by_case_and_spacing_asks_too(
    turns: TurnHandler, stores: StoreRepository
) -> None:
    thread_id = turns.start()

    result = turns.send(thread_id, "save  COSTCO  with number 555-876-5432")

    assert result.pending is not None
    assert result.pending.kind == "confirm_overwrite"
