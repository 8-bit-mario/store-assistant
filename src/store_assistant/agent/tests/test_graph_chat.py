# ABOUTME: Tests the compiled graph's chat and off-topic paths with a real LLM and checkpointer.
# ABOUTME: Asserts on persisted state and fixed reply texts, never on LLM wording.
import sqlite3

import pytest
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.checkpoint.sqlite import SqliteSaver

from store_assistant.agent.classify import build_chat_model
from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.graph import AssistantGraph, build_graph
from store_assistant.agent.nodes.capability import CAPABILITY_REPLY
from store_assistant.agent.nodes.off_topic import OFF_TOPIC_WARNING
from store_assistant.agent.state import AssistantState
from store_assistant.config import Settings
from store_assistant.storage.stores import StoreRepository
from store_assistant.storage.summaries import SummaryRepository

pytestmark = pytest.mark.llm

THREAD: RunnableConfig = {"configurable": {"thread_id": "thread-1"}}


@pytest.fixture
def deps(settings: Settings, db: sqlite3.Connection) -> GraphDeps:
    return GraphDeps(
        model=build_chat_model(settings),
        stores=StoreRepository(db),
        summaries=SummaryRepository(db),
    )


@pytest.fixture
def graph(checkpointer: SqliteSaver) -> AssistantGraph:
    return build_graph(checkpointer)


def _send(graph: AssistantGraph, deps: GraphDeps, text: str) -> None:
    turn: AssistantState = {"messages": [HumanMessage(text)]}
    graph.invoke(turn, THREAD, context=deps)


def test_capability_question_gets_capability_reply(
    graph: AssistantGraph,
    deps: GraphDeps,
) -> None:
    _send(graph, deps, "hi, what can you do?")

    state = graph.get_state(THREAD).values
    assert state["messages"][-1].content == CAPABILITY_REPLY
    assert state["off_topic_streak"] == 0


def test_second_off_topic_message_warns(
    graph: AssistantGraph,
    deps: GraphDeps,
) -> None:
    _send(graph, deps, "who won the world cup?")
    first_reply = graph.get_state(THREAD).values["messages"][-1].content
    _send(graph, deps, "write me a poem about cats")

    state = graph.get_state(THREAD).values
    assert state["off_topic_streak"] == 2
    assert OFF_TOPIC_WARNING not in first_reply
    assert OFF_TOPIC_WARNING in state["messages"][-1].content


def test_on_topic_message_resets_off_topic_streak(
    graph: AssistantGraph,
    deps: GraphDeps,
) -> None:
    _send(graph, deps, "who won the world cup?")
    _send(graph, deps, "write me a poem about cats")
    _send(graph, deps, "what can you do?")

    assert graph.get_state(THREAD).values["off_topic_streak"] == 0


def test_transcript_persists_across_turns(
    graph: AssistantGraph,
    deps: GraphDeps,
) -> None:
    _send(graph, deps, "hi")
    _send(graph, deps, "thanks")

    messages = graph.get_state(THREAD).values["messages"]
    assert [m.type for m in messages] == ["human", "ai", "human", "ai"]
    assert messages[0].content == "hi"
