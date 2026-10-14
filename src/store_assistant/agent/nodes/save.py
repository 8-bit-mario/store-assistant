# ABOUTME: Graph node that saves a store, prompting for a missing or invalid name or phone.
# ABOUTME: The database write happens only after the last prompt, so resumes never duplicate it.
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.runtime import Runtime

from store_assistant.agent.answers import parse_yes_no
from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.nodes.prompts import Operation, OperationCancelled
from store_assistant.agent.nodes.store_details import collect_store_name
from store_assistant.agent.state import Action, AssistantState, cancelled_action
from store_assistant.storage.stores import Store
from store_assistant.validation.phone import InvalidPhoneError, normalize_us_phone

ASK_PHONE = "What's the phone number for {name}?"
EXAMPLE_PHONE = "(555) 234-5678"
ASK_OVERWRITE = "{name} is already saved with {old}. Replace it with {new}?"


def save_store(state: AssistantState, runtime: Runtime[GraphDeps]) -> dict[str, Any]:
    """Collect a valid store name and phone, then save the store."""
    classification = state.get("classification") or {"store_name": None, "phone": None}
    operation = Operation()
    name = classification["store_name"]
    try:
        name = collect_store_name(operation, name)
        phone = _collect_phone(operation, name, classification["phone"])
        return _save(operation, runtime, name, phone)
    except OperationCancelled as cancelled:
        what = f"saving {name}" if name else "saving the store"
        return {
            "messages": operation.cancelled_messages(cancelled.reason, what),
            "actions": [cancelled_action(cancelled.reason, name)],
        }


def _save(
    operation: Operation, runtime: Runtime[GraphDeps], name: str, phone: str
) -> dict[str, Any]:
    stores = runtime.context.stores
    existing = stores.find_by_name(name)
    if existing is None:
        store = stores.add(name, phone)
        action: Action = {"kind": "saved", "store_name": store.name, "phone": store.phone}
        reply = f"Saved {store.name} — {store.phone}."
    elif _confirm_overwrite(operation, existing, phone):
        store = stores.update_phone(name, phone)
        action = {"kind": "updated", "store_name": store.name, "phone": store.phone}
        reply = f"Updated {store.name} — {store.phone}."
    else:
        action = {"kind": "kept_existing", "store_name": existing.name, "phone": existing.phone}
        reply = f"Kept {existing.name} — {existing.phone}."
    return {"messages": [*operation.messages, AIMessage(reply)], "actions": [action]}


def _confirm_overwrite(operation: Operation, existing: Store, phone: str) -> bool:
    prompt = ASK_OVERWRITE.format(name=existing.name, old=existing.phone, new=phone)
    while True:
        decision = parse_yes_no(operation.ask("confirm_overwrite", prompt))
        if decision is not None:
            return decision
        prompt = f"Please answer yes or no. {prompt}"


def _collect_phone(operation: Operation, name: str, given: str | None) -> str:
    candidate, prompt = given, ASK_PHONE.format(name=name)
    while True:
        if candidate is None:
            candidate = operation.ask("phone", prompt)
        try:
            return normalize_us_phone(candidate)
        except InvalidPhoneError as error:
            candidate = None
            prompt = (
                f"That doesn't look like a valid phone number: {error.reason}. "
                f"Please enter a US number like {EXAMPLE_PHONE}."
            )
