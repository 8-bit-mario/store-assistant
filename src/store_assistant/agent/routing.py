# ABOUTME: Pure routing rules deciding which graph node runs next.
# ABOUTME: Kept free of LLM calls so every branch is unit-testable.
from typing import Literal

from langgraph.graph import END

from store_assistant.agent.state import OFF_TOPIC_LIMIT, AssistantState, Intent

RouteName = Literal[
    "save_store", "lookup_store", "answer_capability", "handle_off_topic", "summarize_and_end"
]

INTENT_NODES: dict[Intent, RouteName] = {
    "save": "save_store",
    "lookup": "lookup_store",
    "on_topic_chat": "answer_capability",
    "off_topic": "handle_off_topic",
    "done": "summarize_and_end",
}


def route_after_classify(state: AssistantState) -> str:
    """Pick the node that handles the classified intent; end the turn if none was classified."""
    classification = state.get("classification")
    if classification is None:
        return END
    return INTENT_NODES[classification["intent"]]


def next_off_topic_streak(intent: Intent, current: int) -> int:
    """Count consecutive off-topic messages; any other intent resets the count."""
    return current + 1 if intent == "off_topic" else 0


def route_after_off_topic(state: AssistantState) -> str:
    """End the conversation once the off-topic streak reaches the limit."""
    if state.get("off_topic_streak", 0) >= OFF_TOPIC_LIMIT:
        return "summarize_and_end"
    return END
