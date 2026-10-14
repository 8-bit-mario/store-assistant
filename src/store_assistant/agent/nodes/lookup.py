# ABOUTME: Graph node that looks up a store's phone after the user passes the passphrase check.
# ABOUTME: Allows three passphrase attempts per lookup, then cancels and keeps the chat going.
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.nodes.prompts import Operation, OperationCancelled
from store_assistant.agent.nodes.store_details import collect_store_name
from store_assistant.agent.state import Action, AssistantState, cancelled_action

MAX_PASSPHRASE_ATTEMPTS = 3
ASK_PASSPHRASE = "Please enter the passphrase to look up {name}."
WRONG_PASSPHRASE = "That passphrase is wrong. {left} attempt(s) left. Please enter the passphrase."
LOCKED_OUT = "That passphrase was wrong {limit} times, so I cancelled the lookup for {name}."
NOT_FOUND = (
    "I don't have a store named '{name}' saved. Want to save it, or look up a different name?"
)


def lookup_store(state: AssistantState, runtime: Runtime[GraphDeps]) -> dict[str, Any]:
    """Collect a store name, check the passphrase, then report the store's phone."""
    classification = state.get("classification") or {"store_name": None}
    operation = Operation()
    name = classification["store_name"]
    try:
        name = collect_store_name(operation, name)
        accepted = _passphrase_accepted(operation, name)
    except OperationCancelled as cancelled:
        what = f"looking up {name}" if name else "the lookup"
        return {
            "messages": operation.cancelled_messages(cancelled.reason, what),
            "actions": [cancelled_action(cancelled.reason, name)],
        }

    if not accepted:
        action: Action = {"kind": "lookup_cancelled_passphrase", "store_name": name, "phone": None}
        reply = LOCKED_OUT.format(limit=MAX_PASSPHRASE_ATTEMPTS, name=name)
    elif (store := runtime.context.stores.find_matching(name)) is None:
        action = {"kind": "lookup_not_found", "store_name": name, "phone": None}
        reply = NOT_FOUND.format(name=name)
    else:
        action = {"kind": "lookup_found", "store_name": store.name, "phone": store.phone}
        reply = f"{store.name}: {store.phone}."
    return {"messages": [*operation.messages, AIMessage(reply)], "actions": [action]}


def _passphrase_accepted(operation: Operation, name: str) -> bool:
    prompt = ASK_PASSPHRASE.format(name=name)
    for attempt in range(1, MAX_PASSPHRASE_ATTEMPTS + 1):
        if operation.ask_passphrase(prompt):
            return True
        prompt = WRONG_PASSPHRASE.format(left=MAX_PASSPHRASE_ATTEMPTS - attempt)
    return False
