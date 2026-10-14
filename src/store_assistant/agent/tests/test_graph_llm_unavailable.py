# ABOUTME: Tests that the graph keeps the conversation usable when the LLM cannot be reached.
# ABOUTME: Uses a real chat model pointed at a closed local port, so every call fails to connect.
import sqlite3

from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig

from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.graph import AssistantGraph
from store_assistant.agent.nodes.classify import LLM_UNAVAILABLE_REPLY
from store_assistant.agent.nodes.summarize import fallback_summary
from store_assistant.agent.state import Action, AssistantState
from store_assistant.storage.summaries import SummaryRepository

THREAD: RunnableConfig = {"configurable": {"thread_id": "thread-1"}}


def _send(graph: AssistantGraph, deps: GraphDeps, text: str) -> None:
    turn: AssistantState = {"messages": [HumanMessage(text)]}
    graph.invoke(turn, THREAD, context=deps)


def test_unreachable_llm_asks_the_user_to_send_again(
    graph: AssistantGraph, unreachable_deps: GraphDeps
) -> None:
    _send(graph, unreachable_deps, "save Costco, number 555-876-5432")

    state = graph.get_state(THREAD).values
    assert state["messages"][-1].content == LLM_UNAVAILABLE_REPLY
    assert state["classification"] is None
    assert not state.get("ended", False)


def test_unreachable_llm_leaves_the_off_topic_streak_unchanged(
    graph: AssistantGraph, unreachable_deps: GraphDeps
) -> None:
    graph.update_state(THREAD, {"off_topic_streak": 2})

    _send(graph, unreachable_deps, "what's the weather?")

    assert graph.get_state(THREAD).values["off_topic_streak"] == 2


def test_unreachable_llm_still_ends_with_a_saved_fallback_summary(
    graph: AssistantGraph, unreachable_deps: GraphDeps, db: sqlite3.Connection
) -> None:
    actions: list[Action] = [{"kind": "saved", "store_name": "Costco", "phone": "+15558765432"}]
    done: AssistantState = {
        "messages": [HumanMessage("I'm done")],
        "actions": actions,
        "classification": {"intent": "done", "store_name": None, "phone": None},
    }
    graph.update_state(THREAD, done, as_node="classify")

    graph.invoke(None, THREAD, context=unreachable_deps)

    state = graph.get_state(THREAD).values
    saved = SummaryRepository(db).find_by_thread("thread-1")
    assert state["ended"] is True
    assert saved is not None
    assert saved.summary == fallback_summary(actions, "user_done")
    assert state["messages"][-1].content == saved.summary
