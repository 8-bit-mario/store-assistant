# ABOUTME: Turns a conversation's saved state into the (role, text) lines the chat UI shows.
# ABOUTME: Includes the in-progress operation and masks passphrase entries.
from typing import Literal

from store_assistant.agent.nodes.prompts import PASSPHRASE_PLACEHOLDER
from store_assistant.conversation.turns import TurnResult

Role = Literal["user", "assistant"]
PASSPHRASE_MASK = "••••••"


def transcript_lines(result: TurnResult) -> list[tuple[Role, str]]:
    """Lines to display, oldest first, ending with any question awaiting an answer."""
    lines: list[tuple[Role, str]] = [
        ("user" if m.type == "human" else "assistant", str(m.content)) for m in result.messages
    ]
    if result.pending is not None:
        lines += [(line["role"], line["text"]) for line in result.pending.exchange]
        lines.append(("assistant", result.pending.prompt))
    return [(role, _masked(text)) for role, text in lines]


def _masked(text: str) -> str:
    return PASSPHRASE_MASK if text == PASSPHRASE_PLACEHOLDER else text
