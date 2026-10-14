# ABOUTME: Asks the user for input mid-operation via LangGraph interrupts and records the exchange.
# ABOUTME: Passphrase answers arrive only as a verdict; the transcript records a placeholder.
from typing import Literal, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.types import interrupt

from store_assistant.clock import utc_now

PromptKind = Literal["store_name", "phone", "confirm_overwrite", "passphrase"]

PASSPHRASE_PLACEHOLDER = "[passphrase entered]"
CANCEL_REPLY = {
    "user": "Okay, I cancelled {what}.",
    "timeout": "No response, so I cancelled {what}.",
}

CancelReason = Literal["user", "timeout"]


class OperationCancelled(Exception):
    """Raised inside a node when the user cancels or the prompt times out."""

    def __init__(self, reason: CancelReason) -> None:
        self.reason = reason
        super().__init__(f"Operation cancelled ({reason})")


class ExchangeLine(TypedDict):
    """One line of an in-progress operation, as shown to the user."""

    role: Literal["assistant", "user"]
    text: str


class PromptPayload(TypedDict):
    """What the graph surfaces when it pauses for input."""

    kind: PromptKind
    prompt: str
    exchange: list[ExchangeLine]
    asked_at: str


class Operation:
    """Collects the prompts and answers of one save or lookup operation."""

    def __init__(self) -> None:
        self.messages: list[AnyMessage] = []

    def ask(self, kind: PromptKind, prompt: str) -> str:
        """Pause the graph until the user answers the prompt, then return the answer."""
        answer = str(self._pause(kind, prompt)["answer"])
        self.messages += [AIMessage(prompt), HumanMessage(answer)]
        return answer

    def ask_passphrase(self, prompt: str) -> bool:
        """Pause until the turn handler reports whether the user's passphrase was correct."""
        passphrase_ok = bool(self._pause("passphrase", prompt)["passphrase_ok"])
        self.messages += [AIMessage(prompt), HumanMessage(PASSPHRASE_PLACEHOLDER)]
        return passphrase_ok

    def cancelled_messages(self, reason: CancelReason, what: str) -> list[AnyMessage]:
        """The operation's transcript closed with a note that it was cancelled."""
        return [*self.messages, AIMessage(CANCEL_REPLY[reason].format(what=what))]

    def _pause(self, kind: PromptKind, prompt: str) -> dict[str, object]:
        payload: PromptPayload = {
            "kind": kind,
            "prompt": prompt,
            "exchange": self._exchange(),
            "asked_at": utc_now().isoformat(),
        }
        resumed: dict[str, object] = interrupt(payload)
        if resumed.get("cancelled"):
            self.messages.append(AIMessage(prompt))
            if typed := resumed.get("text"):
                self.messages.append(HumanMessage(str(typed)))
            raise OperationCancelled("timeout" if resumed.get("reason") == "timeout" else "user")
        return resumed

    def _exchange(self) -> list[ExchangeLine]:
        return [
            {"role": "user" if m.type == "human" else "assistant", "text": str(m.content)}
            for m in self.messages
        ]
