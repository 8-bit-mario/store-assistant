# ABOUTME: Graph node that classifies the latest user message and tracks the off-topic streak.
# ABOUTME: Its classification drives the routing to the next node; an LLM outage ends the turn.
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from store_assistant.agent.classify import LLM_OUTAGE_ERRORS, classify
from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.routing import next_off_topic_streak
from store_assistant.agent.state import AssistantState

LLM_UNAVAILABLE_REPLY = (
    "Sorry, I couldn't reach the language model just now. Please send that message again."
)


def classify_message(state: AssistantState, runtime: Runtime[GraphDeps]) -> dict[str, Any]:
    """Classify the latest message and update the consecutive off-topic count."""
    try:
        classification = classify(runtime.context.model, state["messages"])
    except LLM_OUTAGE_ERRORS:
        return {"classification": None, "messages": [AIMessage(LLM_UNAVAILABLE_REPLY)]}
    streak = next_off_topic_streak(classification["intent"], state.get("off_topic_streak", 0))
    return {"classification": classification, "off_topic_streak": streak}
