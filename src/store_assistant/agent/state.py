# ABOUTME: Typed state shared by every node of the store assistant graph.
# ABOUTME: Also defines the LLM classification result and the action records used for summaries.
import operator
from typing import Annotated, Literal, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages

from store_assistant.storage.summaries import EndReason

Intent = Literal["save", "lookup", "done", "off_topic", "on_topic_chat"]

ActionKind = Literal[
    "saved",
    "updated",
    "kept_existing",
    "lookup_found",
    "lookup_not_found",
    "lookup_cancelled_passphrase",
    "cancelled_by_user",
    "cancelled_timeout",
    "off_topic_message",
]

OFF_TOPIC_LIMIT = 3


class Classification(TypedDict):
    """What the LLM understood from the user's latest message."""

    intent: Intent
    store_name: str | None
    phone: str | None


class Action(TypedDict):
    """A fact about what happened, kept so the summary states facts rather than guesses."""

    kind: ActionKind
    store_name: str | None
    phone: str | None


class AssistantState(TypedDict):
    """Conversation state persisted by the checkpointer between turns."""

    messages: Annotated[list[AnyMessage], add_messages]
    actions: NotRequired[Annotated[list[Action], operator.add]]
    off_topic_streak: NotRequired[int]
    classification: NotRequired[Classification | None]
    end_reason: NotRequired[EndReason | None]
    ended: NotRequired[bool]


def cancelled_action(reason: Literal["user", "timeout"], store_name: str | None) -> Action:
    """The action recorded when an operation is cancelled by the user or by inactivity."""
    kind: ActionKind = "cancelled_timeout" if reason == "timeout" else "cancelled_by_user"
    return {"kind": kind, "store_name": store_name, "phone": None}
