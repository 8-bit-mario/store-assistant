# ABOUTME: Tests cancelling in-progress operations by keyword, by request and by inactivity.
# ABOUTME: Uses the real graph and LLM with a settable clock for the inactivity rules.
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from datetime import datetime, timedelta
from typing import Any

import pytest

from store_assistant.app_factory import build_turn_handler
from store_assistant.clock import utc_now
from store_assistant.config import Settings
from store_assistant.conversation.turns import TurnHandler
from store_assistant.storage.stores import StoreRepository
from store_assistant.tests.support import TEST_PASSPHRASE

pytestmark = pytest.mark.llm

ThreadState = Callable[[str], dict[str, Any]]


class SettableClock:
    """Real time until a test pins it to a moment."""

    def __init__(self) -> None:
        self.pinned: datetime | None = None

    def __call__(self) -> datetime:
        return self.pinned or utc_now()


@pytest.fixture
def clock() -> SettableClock:
    return SettableClock()


@pytest.fixture
def timed_turns(settings: Settings, clock: SettableClock) -> Iterator[TurnHandler]:
    with ExitStack() as resources:
        yield build_turn_handler(settings, resources, clock=clock)


def _actions(thread_state: ThreadState, thread_id: str) -> list[str]:
    return [a["kind"] for a in thread_state(thread_id).get("actions", [])]


def test_cancel_keyword_at_phone_prompt_cancels_without_saving(
    turns: TurnHandler, db: sqlite3.Connection, thread_state: ThreadState
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "I want to save a store")
    turns.send(thread_id, "Costco")

    result = turns.send(thread_id, "cancel")

    assert result.pending is None
    assert StoreRepository(db).find_by_name("Costco") is None
    assert _actions(thread_state, thread_id) == ["cancelled_by_user"]
    assert [m.content for m in result.messages[-2:]] == [
        "cancel",
        "Okay, I cancelled saving Costco.",
    ]


def test_cancel_operation_at_passphrase_prompt_skips_lookup(
    turns: TurnHandler, db: sqlite3.Connection, thread_state: ThreadState
) -> None:
    StoreRepository(db).add("Costco", "+15552345678")
    thread_id = turns.start()
    turns.send(thread_id, "what's the number for Costco?")

    result = turns.cancel_operation(thread_id, "user")

    assert result.pending is None
    assert "+15552345678" not in " ".join(str(m.content) for m in result.messages)
    assert _actions(thread_state, thread_id) == ["cancelled_by_user"]


def test_cancel_typed_at_passphrase_prompt_counts_as_wrong_attempt(turns: TurnHandler) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "what's the number for Costco?")

    result = turns.send(thread_id, "cancel")

    assert result.pending is not None
    assert result.pending.kind == "passphrase"


def test_cancel_operation_without_pending_prompt_changes_nothing(turns: TurnHandler) -> None:
    thread_id = turns.start()
    before = turns.send(thread_id, "hi")

    after = turns.cancel_operation(thread_id, "user")

    assert after == before


def test_inactivity_moves_from_active_to_check_in(
    timed_turns: TurnHandler, clock: SettableClock
) -> None:
    thread_id = timed_turns.start()
    asked = timed_turns.send(thread_id, "I want to save a store").pending
    assert asked is not None

    clock.pinned = asked.asked_at + timedelta(seconds=59)
    assert timed_turns.inactivity(thread_id) == "active"
    clock.pinned = asked.asked_at + timedelta(seconds=61)
    assert timed_turns.inactivity(thread_id) == "check_in"


def test_expired_operation_is_cancelled_when_viewed(
    timed_turns: TurnHandler, clock: SettableClock, thread_state: ThreadState
) -> None:
    thread_id = timed_turns.start()
    asked = timed_turns.send(thread_id, "I want to save a store").pending
    assert asked is not None

    clock.pinned = asked.asked_at + timedelta(seconds=91)
    result = timed_turns.view(thread_id)

    assert result.pending is None
    assert timed_turns.inactivity(thread_id) is None
    assert _actions(thread_state, thread_id) == ["cancelled_timeout"]


def test_reprompt_restarts_the_inactivity_timer(timed_turns: TurnHandler) -> None:
    thread_id = timed_turns.start()
    timed_turns.send(thread_id, "I want to save a store")
    first = timed_turns.send(thread_id, "Costco").pending

    second = timed_turns.send(thread_id, "12345").pending

    assert first is not None and second is not None
    assert second.asked_at > first.asked_at


def test_cancelling_keeps_the_off_topic_streak(
    turns: TurnHandler, thread_state: ThreadState
) -> None:
    thread_id = turns.start()
    turns.send(thread_id, "who won the world cup?")
    turns.send(thread_id, "I want to save a store")
    turns.send(thread_id, "cancel")

    assert thread_state(thread_id)["off_topic_streak"] == 0


def test_correct_passphrase_still_works_after_cancel_elsewhere(
    turns: TurnHandler, db: sqlite3.Connection
) -> None:
    StoreRepository(db).add("Costco", "+15552345678")
    thread_id = turns.start()
    turns.send(thread_id, "I want to save a store")
    turns.send(thread_id, "never mind")
    turns.send(thread_id, "what's the number for Costco?")

    result = turns.send(thread_id, TEST_PASSPHRASE)

    assert "+15552345678" in result.messages[-1].content
