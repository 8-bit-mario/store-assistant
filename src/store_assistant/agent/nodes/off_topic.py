# ABOUTME: Graph node steering the user back after an off-topic message, recorded for the summary.
# ABOUTME: Warns before the last allowed off-topic message; the limit itself ends the chat.
from typing import Any

from langchain_core.messages import AIMessage

from store_assistant.agent.state import OFF_TOPIC_LIMIT, Action, AssistantState

OFF_TOPIC_REDIRECT = "Sorry, I can only help with saving stores and looking up their phone numbers."
OFF_TOPIC_WARNING = "One more off-topic message and I'll wrap up."


def handle_off_topic(state: AssistantState) -> dict[str, Any]:
    """Record the message for the summary; redirect to store tasks, warning when one is left."""
    action: Action = {"kind": "off_topic_message", "store_name": None, "phone": None}
    streak = state.get("off_topic_streak", 0)
    if streak >= OFF_TOPIC_LIMIT:
        return {"actions": [action]}
    reply = OFF_TOPIC_REDIRECT
    if streak == OFF_TOPIC_LIMIT - 1:
        reply = f"{reply} {OFF_TOPIC_WARNING}"
    return {"messages": [AIMessage(reply)], "actions": [action]}
