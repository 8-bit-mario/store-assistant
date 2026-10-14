# ABOUTME: Graph node answering greetings, thanks and "what can you do?" questions.
# ABOUTME: Replies with a fixed description of what the assistant can do.
from typing import Any

from langchain_core.messages import AIMessage

from store_assistant.agent.state import AssistantState

CAPABILITY_REPLY = (
    "I can save a store's name and phone number, and look up a saved store's number "
    "(that needs the passphrase). Tell me what you'd like to do, or say \"I'm done\" to finish."
)


def answer_capability(state: AssistantState) -> dict[str, Any]:
    """Explain what the assistant can do."""
    return {"messages": [AIMessage(CAPABILITY_REPLY)]}
