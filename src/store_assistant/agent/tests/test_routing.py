# ABOUTME: Tests for the pure routing rules that pick the next graph node.
# ABOUTME: Covers every intent and the off-topic streak limit.
import pytest
from langgraph.graph import END

from store_assistant.agent.routing import (
    next_off_topic_streak,
    route_after_classify,
    route_after_off_topic,
)
from store_assistant.agent.state import AssistantState, Intent


def _state_with_intent(intent: Intent) -> AssistantState:
    return {
        "messages": [],
        "actions": [],
        "classification": {"intent": intent, "store_name": None, "phone": None},
    }


@pytest.mark.parametrize(
    ("intent", "node"),
    [
        ("save", "save_store"),
        ("lookup", "lookup_store"),
        ("on_topic_chat", "answer_capability"),
        ("off_topic", "handle_off_topic"),
        ("done", "summarize_and_end"),
    ],
)
def test_each_intent_routes_to_its_node(intent: Intent, node: str) -> None:
    assert route_after_classify(_state_with_intent(intent)) == node


def test_missing_classification_ends_the_turn() -> None:
    state: AssistantState = {"messages": [], "actions": [], "classification": None}

    assert route_after_classify(state) == END


@pytest.mark.parametrize(
    ("intent", "current", "expected"),
    [
        ("off_topic", 0, 1),
        ("off_topic", 2, 3),
        ("save", 2, 0),
        ("lookup", 1, 0),
        ("on_topic_chat", 2, 0),
        ("done", 1, 0),
    ],
)
def test_off_topic_streak_counts_consecutive_messages(
    intent: Intent, current: int, expected: int
) -> None:
    assert next_off_topic_streak(intent, current) == expected


def test_off_topic_below_limit_ends_the_turn() -> None:
    state: AssistantState = {"messages": [], "actions": [], "off_topic_streak": 2}

    assert route_after_off_topic(state) == END


def test_off_topic_at_limit_ends_the_conversation() -> None:
    state: AssistantState = {"messages": [], "actions": [], "off_topic_streak": 3}

    assert route_after_off_topic(state) == "summarize_and_end"
