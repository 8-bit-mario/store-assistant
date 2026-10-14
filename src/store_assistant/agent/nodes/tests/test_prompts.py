# ABOUTME: Tests how an operation records its transcript when the user answers or cancels.
# ABOUTME: Runs Operation in a minimal real graph so interrupts and resumes behave as in the app.
from typing import Annotated, Any, TypedDict

from langchain_core.messages import AIMessage, AnyMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.types import Command

from store_assistant.agent.nodes.prompts import Operation, OperationCancelled

QUESTION = "What's the name of the store?"
CONFIG: Any = {"configurable": {"thread_id": "t"}}


class _State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def _ask_one_question(state: _State) -> dict[str, Any]:
    operation = Operation()
    try:
        operation.ask("store_name", QUESTION)
    except OperationCancelled as cancelled:
        return {"messages": operation.cancelled_messages(cancelled.reason, "saving the store")}
    return {"messages": operation.messages}


def _resume_after_question(resume: dict[str, object]) -> list[AnyMessage]:
    builder = StateGraph(_State)
    builder.add_node("ask", _ask_one_question)
    builder.add_edge(START, "ask")
    builder.add_edge("ask", END)
    graph = builder.compile(checkpointer=InMemorySaver())
    graph.invoke({"messages": []}, CONFIG)
    return list(graph.invoke(Command(resume=resume), CONFIG)["messages"])


def test_typed_cancel_word_is_recorded_as_the_users_reply() -> None:
    messages = _resume_after_question({"cancelled": True, "reason": "user", "text": "never mind"})

    assert [(type(m), m.content) for m in messages] == [
        (AIMessage, QUESTION),
        (HumanMessage, "never mind"),
        (AIMessage, "Okay, I cancelled saving the store."),
    ]


def test_cancel_without_typed_text_records_no_user_reply() -> None:
    messages = _resume_after_question({"cancelled": True, "reason": "timeout"})

    assert [(type(m), m.content) for m in messages] == [
        (AIMessage, QUESTION),
        (AIMessage, "No response, so I cancelled saving the store."),
    ]
