# ABOUTME: Prompts shared by the save and lookup flows for collecting store details.
# ABOUTME: Keeps asking until the user gives a usable store name.
from store_assistant.agent.nodes.prompts import Operation
from store_assistant.validation.store_name import InvalidStoreNameError, clean_store_name

ASK_NAME = "What's the name of the store?"


def collect_store_name(operation: Operation, given: str | None) -> str:
    """Return a clean store name, asking the user while it is missing or invalid."""
    candidate, prompt = given, ASK_NAME
    while True:
        if candidate is None:
            candidate = operation.ask("store_name", prompt)
        try:
            return clean_store_name(candidate)
        except InvalidStoreNameError as error:
            candidate, prompt = None, f"Sorry, {error.reason}. {ASK_NAME}"
