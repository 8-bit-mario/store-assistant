# ABOUTME: Tests the off-topic node's replies and the action it records for the closing summary.
# ABOUTME: Pure checks on the node's output for each point in the off-topic streak; no LLM call.
import pytest

from store_assistant.agent.nodes.off_topic import (
    OFF_TOPIC_REDIRECT,
    OFF_TOPIC_WARNING,
    handle_off_topic,
)
from store_assistant.agent.state import OFF_TOPIC_LIMIT, AssistantState

OFF_TOPIC_ACTION = {"kind": "off_topic_message", "store_name": None, "phone": None}


def _state_with_streak(streak: int) -> AssistantState:
    return {"messages": [], "actions": [], "off_topic_streak": streak}


@pytest.mark.parametrize("streak", range(1, OFF_TOPIC_LIMIT + 1))
def test_every_off_topic_message_is_recorded_as_an_action(streak: int) -> None:
    update = handle_off_topic(_state_with_streak(streak))

    assert update["actions"] == [OFF_TOPIC_ACTION]


def test_first_off_topic_message_gets_the_redirect_only() -> None:
    update = handle_off_topic(_state_with_streak(1))

    assert update["messages"][0].content == OFF_TOPIC_REDIRECT


def test_message_before_the_limit_adds_the_warning() -> None:
    update = handle_off_topic(_state_with_streak(OFF_TOPIC_LIMIT - 1))

    assert update["messages"][0].content == f"{OFF_TOPIC_REDIRECT} {OFF_TOPIC_WARNING}"


def test_message_at_the_limit_leaves_the_reply_to_the_summary() -> None:
    update = handle_off_topic(_state_with_streak(OFF_TOPIC_LIMIT))

    assert "messages" not in update
