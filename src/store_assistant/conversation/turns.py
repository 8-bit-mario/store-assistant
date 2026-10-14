# ABOUTME: Runs one conversation turn at a time against the agent graph, for any UI.
# ABOUTME: Checks passphrases here so the graph, traces and checkpoints only see a verdict.
import uuid
from dataclasses import dataclass
from datetime import datetime

from langchain_core.messages import AnyMessage, HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.types import Command, StateSnapshot

from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.graph import AssistantGraph
from store_assistant.agent.nodes.prompts import (
    PASSPHRASE_PLACEHOLDER,
    CancelReason,
    ExchangeLine,
    PromptKind,
    PromptPayload,
)
from store_assistant.agent.state import AssistantState
from store_assistant.clock import Clock, utc_now
from store_assistant.config import Settings
from store_assistant.conversation.cancellation import (
    InactivityStatus,
    inactivity_status,
    is_cancel_request,
)
from store_assistant.security.passphrase import is_correct_passphrase

RUN_NAME = "store-assistant-turn"


class ConversationEndedError(Exception):
    """Raised when input is sent to a conversation that has already ended."""


@dataclass(frozen=True)
class PendingPrompt:
    """A question the graph is waiting on the user to answer."""

    kind: PromptKind
    prompt: str
    exchange: list[ExchangeLine]
    asked_at: datetime


@dataclass(frozen=True)
class TurnResult:
    """What a UI needs to draw a conversation after a turn."""

    messages: list[AnyMessage]
    pending: PendingPrompt | None
    ended: bool


class TurnHandler:
    """Sends user input into the graph and reports the resulting conversation state."""

    def __init__(
        self,
        graph: AssistantGraph,
        deps: GraphDeps,
        settings: Settings,
        clock: Clock = utc_now,
    ) -> None:
        self._graph = graph
        self._deps = deps
        self._settings = settings
        self._clock = clock

    def start(self) -> str:
        """Create an id for a new conversation thread."""
        return str(uuid.uuid4())

    def send(self, thread_id: str, text: str) -> TurnResult:
        """
        Run one turn with the user's message and return the updated conversation.

        At a passphrase prompt only the verdict reaches the graph. Anywhere else, text equal
        to the passphrase is replaced with a placeholder so the secret is never stored.

        Raises:
            ConversationEndedError: If the conversation has already ended.
        """
        current = self.view(thread_id)
        if current.ended:
            raise ConversationEndedError(f"Conversation {thread_id} has ended")
        passphrase_typed = is_correct_passphrase(text, self._settings.store_lookup_passphrase)
        if current.pending is not None and current.pending.kind == "passphrase":
            self._resume(thread_id, {"passphrase_ok": passphrase_typed})
            return self.view(thread_id)
        if passphrase_typed:
            text = PASSPHRASE_PLACEHOLDER
        if current.pending is not None and is_cancel_request(text):
            self._resume(thread_id, {"cancelled": True, "reason": "user", "text": text})
        elif current.pending is not None:
            self._resume(thread_id, {"answer": text})
        else:
            turn: AssistantState = {"messages": [HumanMessage(text)]}
            self._graph.invoke(turn, self._config(thread_id), context=self._deps)
        return self.view(thread_id)

    def cancel_operation(self, thread_id: str, reason: CancelReason) -> TurnResult:
        """Cancel the operation waiting on the user, if any, and return the conversation."""
        if self._saved(thread_id).pending is not None:
            self._resume(thread_id, {"cancelled": True, "reason": reason})
        return self._saved(thread_id)

    def inactivity(self, thread_id: str) -> InactivityStatus | None:
        """How long the pending prompt has gone unanswered, or None if nothing is pending."""
        pending = self._saved(thread_id).pending
        if pending is None:
            return None
        return inactivity_status(
            pending.asked_at,
            self._clock(),
            self._settings.check_in_after,
            self._settings.expire_after,
        )

    def view(self, thread_id: str) -> TurnResult:
        """Return the conversation for redrawing, first cancelling a prompt that has expired."""
        if self.inactivity(thread_id) == "expired":
            return self.cancel_operation(thread_id, "timeout")
        return self._saved(thread_id)

    def _saved(self, thread_id: str) -> TurnResult:
        snapshot = self._graph.get_state(self._config(thread_id))
        values = snapshot.values
        return TurnResult(
            messages=list(values.get("messages", [])),
            pending=_pending_prompt(snapshot),
            ended=bool(values.get("ended", False)),
        )

    def _resume(self, thread_id: str, value: dict[str, object]) -> None:
        self._graph.invoke(Command(resume=value), self._config(thread_id), context=self._deps)

    def _config(self, thread_id: str) -> RunnableConfig:
        return {
            "configurable": {"thread_id": thread_id},
            "metadata": {"thread_id": thread_id},
            "run_name": RUN_NAME,
        }


def _pending_prompt(snapshot: StateSnapshot) -> PendingPrompt | None:
    if not snapshot.interrupts:
        return None
    payload: PromptPayload = snapshot.interrupts[0].value
    return PendingPrompt(
        kind=payload["kind"],
        prompt=payload["prompt"],
        exchange=payload["exchange"],
        asked_at=datetime.fromisoformat(payload["asked_at"]),
    )
