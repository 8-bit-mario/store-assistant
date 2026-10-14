# ABOUTME: Tests the turn handler end to end over the real graph, LLM and SQLite files.
# ABOUTME: Covers starting threads, sending messages and redrawing a thread's transcript.
import pytest

from store_assistant.agent.nodes.capability import CAPABILITY_REPLY
from store_assistant.conversation.turns import TurnHandler

pytestmark = pytest.mark.llm


def test_start_returns_distinct_thread_ids(turns: TurnHandler) -> None:
    assert turns.start() != turns.start()


def test_send_returns_full_transcript(turns: TurnHandler) -> None:
    thread_id = turns.start()

    result = turns.send(thread_id, "hi, what can you do?")

    assert [m.type for m in result.messages] == ["human", "ai"]
    assert result.messages[0].content == "hi, what can you do?"
    assert result.messages[-1].content == CAPABILITY_REPLY


def test_view_redraws_the_same_transcript(turns: TurnHandler) -> None:
    thread_id = turns.start()
    sent = turns.send(thread_id, "hi")

    viewed = turns.view(thread_id)

    assert viewed.messages == sent.messages


def test_view_of_new_thread_is_empty(turns: TurnHandler) -> None:
    assert turns.view(turns.start()).messages == []


def test_threads_are_isolated(turns: TurnHandler) -> None:
    first, second = turns.start(), turns.start()
    turns.send(first, "hi")

    assert turns.view(second).messages == []
