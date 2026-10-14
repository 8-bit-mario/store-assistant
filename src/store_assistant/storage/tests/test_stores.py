# ABOUTME: Tests for saving, finding and updating stores in a real SQLite database.
# ABOUTME: Uses a fixed, steppable clock so timestamps are deterministic.
import sqlite3
from datetime import UTC, datetime, timedelta

import pytest

from store_assistant.storage.stores import (
    DuplicateStoreError,
    StoreNotFoundError,
    StoreRepository,
)

START = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)


class SteppingClock:
    """Returns START, then one minute later on each call."""

    def __init__(self) -> None:
        self.calls = 0

    def __call__(self) -> datetime:
        moment = START + timedelta(minutes=self.calls)
        self.calls += 1
        return moment


@pytest.fixture
def stores(db: sqlite3.Connection) -> StoreRepository:
    return StoreRepository(db, clock=SteppingClock())


def test_added_store_is_found_by_name(stores: StoreRepository) -> None:
    stores.add("Trader Joe's", "+15552345678")

    found = stores.find_by_name("Trader Joe's")

    assert found is not None
    assert found.name == "Trader Joe's"
    assert found.phone == "+15552345678"
    assert found.created_at == "2026-10-13T12:00:00+00:00"


def test_find_ignores_case_and_spacing(stores: StoreRepository) -> None:
    stores.add("Trader Joe's", "+15552345678")

    found = stores.find_by_name("  trader   JOE'S ")

    assert found is not None
    assert found.name == "Trader Joe's"


def test_find_unknown_store_returns_none(stores: StoreRepository) -> None:
    assert stores.find_by_name("Costco") is None


def test_adding_existing_name_raises(stores: StoreRepository) -> None:
    stores.add("Costco", "+15552345678")

    with pytest.raises(DuplicateStoreError):
        stores.add("COSTCO ", "+15558765432")


def test_update_phone_changes_phone_and_updated_at_only(stores: StoreRepository) -> None:
    stores.add("Costco", "+15552345678")

    updated = stores.update_phone("costco", "+15558765432")

    assert updated.phone == "+15558765432"
    assert updated.name == "Costco"
    assert updated.created_at == "2026-10-13T12:00:00+00:00"
    assert updated.updated_at == "2026-10-13T12:01:00+00:00"
    assert stores.find_by_name("Costco") == updated


def test_update_phone_of_unknown_store_raises(stores: StoreRepository) -> None:
    with pytest.raises(StoreNotFoundError):
        stores.update_phone("Costco", "+15558765432")


def test_stores_are_isolated_by_name(stores: StoreRepository) -> None:
    stores.add("Costco", "+15552345678")
    stores.add("Kroger", "+15558765432")

    costco = stores.find_by_name("Costco")

    assert costco is not None
    assert costco.phone == "+15552345678"


def test_find_matching_prefers_the_exact_name(stores: StoreRepository) -> None:
    stores.add("Store 24", "+15552345678")
    stores.add("24", "+15558765432")

    found = stores.find_matching("Store 24")

    assert found is not None and found.name == "Store 24"


def test_find_matching_falls_back_to_name_without_label(stores: StoreRepository) -> None:
    stores.add("abc", "+15552345678")

    found = stores.find_matching("store abc")

    assert found is not None and found.name == "abc"


def test_find_matching_returns_none_when_neither_exists(stores: StoreRepository) -> None:
    stores.add("Costco", "+15552345678")

    assert stores.find_matching("store abc") is None
