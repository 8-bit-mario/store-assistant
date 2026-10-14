# ABOUTME: Graph node that ends the conversation: writes a short summary, saves it, marks the end.
# ABOUTME: The summary is built only from the recorded actions, so it states facts, not guesses.
from collections.abc import Sequence
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.config import get_config
from langgraph.runtime import Runtime

from store_assistant.agent.classify import LLM_OUTAGE_ERRORS
from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.llm_prompts import (
    SUMMARY_REQUEST_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT,
    trace_metadata,
)
from store_assistant.agent.state import OFF_TOPIC_LIMIT, Action, ActionKind, AssistantState
from store_assistant.storage.summaries import EndReason

END_REASON_TEXT: dict[EndReason, str] = {
    "user_done": "the user said they were finished",
    "off_topic": "the assistant ended the conversation after repeated off-topic messages",
}
SUMMARY_TRACE_METADATA = trace_metadata(
    summary_system=SUMMARY_SYSTEM_PROMPT, summary_request=SUMMARY_REQUEST_TEMPLATE
)
ACTION_TEXT: dict[ActionKind, str] = {
    "saved": "saved {store} ({phone})",
    "updated": "updated {store} to {phone}",
    "kept_existing": "kept {store} at {phone}",
    "lookup_found": "looked up {store} ({phone})",
    "lookup_not_found": "looked up {store}, which was not saved",
    "lookup_cancelled_passphrase": "had the lookup for {store} cancelled after wrong passphrases",
    "cancelled_by_user": "cancelled an operation on {store}",
    "cancelled_timeout": "let an operation on {store} time out",
    "off_topic_message": "sent an off-topic message",
}


def summarize_and_end(state: AssistantState, runtime: Runtime[GraphDeps]) -> dict[str, Any]:
    """Summarize the conversation, save the summary and mark the conversation as ended."""
    end_reason: EndReason = (
        "off_topic" if state.get("off_topic_streak", 0) >= OFF_TOPIC_LIMIT else "user_done"
    )
    actions = state.get("actions", [])
    request = render_summary_request(actions, end_reason)
    try:
        reply = runtime.context.model.invoke(
            [SystemMessage(SUMMARY_SYSTEM_PROMPT), HumanMessage(request)],
            config={"metadata": SUMMARY_TRACE_METADATA},
        )
        summary = str(reply.content).strip()
    except LLM_OUTAGE_ERRORS:
        summary = fallback_summary(actions, end_reason)
    thread_id = get_config()["configurable"]["thread_id"]
    runtime.context.summaries.add(thread_id, summary, end_reason)
    return {"messages": [AIMessage(summary)], "end_reason": end_reason, "ended": True}


def fallback_summary(actions: Sequence[Action], end_reason: EndReason) -> str:
    """A plain summary of the recorded actions, used when the LLM cannot write one."""
    ending = f"It ended because {END_REASON_TEXT[end_reason]}."
    if not actions:
        return f"Nothing was saved or looked up. {ending}"
    phrases = [
        ACTION_TEXT[a["kind"]].format(store=a["store_name"] or "a store", phone=a["phone"])
        for a in actions
    ]
    return f"The user {'; '.join(phrases)}. {ending}"


def render_summary_request(actions: Sequence[Action], end_reason: EndReason) -> str:
    """Lay out the recorded actions and end reason for the summary prompt."""
    action_lines = "\n".join(
        f"- {a['kind']}: store={a['store_name'] or '-'}, phone={a['phone'] or '-'}" for a in actions
    )
    return SUMMARY_REQUEST_TEMPLATE.format(
        actions=action_lines or "none",
        end_reason=end_reason,
        end_reason_text=END_REASON_TEXT[end_reason],
    )
