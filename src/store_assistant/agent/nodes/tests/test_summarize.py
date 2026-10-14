# ABOUTME: Tests the summary node's rendering: the LLM request and the templated fallback.
# ABOUTME: Pure rendering checks over recorded actions and the end reason; no LLM call.
from typing import get_args

import pytest

from store_assistant.agent.nodes.summarize import fallback_summary, render_summary_request
from store_assistant.agent.state import Action, ActionKind


def test_fallback_lists_each_action_and_how_the_conversation_ended() -> None:
    actions: list[Action] = [
        {"kind": "saved", "store_name": "Costco", "phone": "+15558765432"},
        {"kind": "lookup_not_found", "store_name": "Kroger", "phone": None},
    ]

    summary = fallback_summary(actions, "user_done")

    assert summary == (
        "The user saved Costco (+15558765432); looked up Kroger, which was not saved. "
        "It ended because the user said they were finished."
    )


def test_fallback_without_actions_says_nothing_happened() -> None:
    summary = fallback_summary([], "off_topic")

    assert summary == (
        "Nothing was saved or looked up. It ended because the assistant ended the "
        "conversation after repeated off-topic messages."
    )


STORE_ACTION_KINDS = [kind for kind in get_args(ActionKind) if kind != "off_topic_message"]


@pytest.mark.parametrize("kind", STORE_ACTION_KINDS)
def test_fallback_names_the_store_for_every_store_action_kind(kind: ActionKind) -> None:
    action: Action = {"kind": kind, "store_name": "Costco", "phone": "+15558765432"}

    assert "Costco" in fallback_summary([action], "user_done")


def test_fallback_handles_a_cancelled_operation_without_a_store_name() -> None:
    action: Action = {"kind": "cancelled_by_user", "store_name": None, "phone": None}

    summary = fallback_summary([action], "user_done")

    assert summary.startswith("The user cancelled an operation on a store. ")


def test_fallback_mentions_each_off_topic_message() -> None:
    actions: list[Action] = [
        {"kind": "saved", "store_name": "Costco", "phone": "+15558765432"},
        {"kind": "off_topic_message", "store_name": None, "phone": None},
    ]

    summary = fallback_summary(actions, "user_done")

    assert summary.startswith("The user saved Costco (+15558765432); sent an off-topic message. ")


def test_request_lists_each_action_with_its_facts() -> None:
    actions: list[Action] = [
        {"kind": "saved", "store_name": "Costco", "phone": "+15558765432"},
        {"kind": "lookup_not_found", "store_name": "Kroger", "phone": None},
    ]

    request = render_summary_request(actions, "user_done")

    assert "saved: store=Costco, phone=+15558765432" in request
    assert "lookup_not_found: store=Kroger, phone=-" in request
    assert "user_done" in request


def test_request_lists_off_topic_messages_as_actions() -> None:
    off_topic: Action = {"kind": "off_topic_message", "store_name": None, "phone": None}

    request = render_summary_request([off_topic, off_topic], "user_done")

    assert request.count("- off_topic_message: store=-, phone=-") == 2


def test_request_without_actions_says_none() -> None:
    request = render_summary_request([], "off_topic")

    assert "<actions>\nnone\n</actions>" in request
    assert "off_topic" in request
