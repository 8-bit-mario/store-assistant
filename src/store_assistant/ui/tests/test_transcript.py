# ABOUTME: Tests turning a conversation's state into the lines the chat UI displays.
# ABOUTME: Covers in-progress operations and masking of passphrase entries.
from datetime import UTC, datetime

from langchain_core.messages import AIMessage, HumanMessage

from store_assistant.agent.nodes.prompts import PASSPHRASE_PLACEHOLDER
from store_assistant.conversation.turns import PendingPrompt, TurnResult
from store_assistant.ui.transcript import PASSPHRASE_MASK, transcript_lines

ASKED_AT = datetime(2026, 10, 13, 12, 0, tzinfo=UTC)


def test_finished_turns_are_shown_in_order() -> None:
    result = TurnResult(
        messages=[HumanMessage("hi"), AIMessage("hello")], pending=None, ended=False
    )

    assert transcript_lines(result) == [("user", "hi"), ("assistant", "hello")]


def test_pending_operation_shows_its_exchange_then_the_prompt() -> None:
    pending = PendingPrompt(
        kind="phone",
        prompt="What's the phone number for Costco?",
        exchange=[
            {"role": "assistant", "text": "What's the name of the store?"},
            {"role": "user", "text": "Costco"},
        ],
        asked_at=ASKED_AT,
    )
    result = TurnResult(messages=[HumanMessage("save a store")], pending=pending, ended=False)

    assert transcript_lines(result) == [
        ("user", "save a store"),
        ("assistant", "What's the name of the store?"),
        ("user", "Costco"),
        ("assistant", "What's the phone number for Costco?"),
    ]


def test_passphrase_entries_are_masked() -> None:
    result = TurnResult(
        messages=[AIMessage("Please enter the passphrase."), HumanMessage(PASSPHRASE_PLACEHOLDER)],
        pending=None,
        ended=False,
    )

    assert transcript_lines(result)[-1] == ("user", PASSPHRASE_MASK)
