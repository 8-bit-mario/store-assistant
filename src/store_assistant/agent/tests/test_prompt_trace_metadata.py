# ABOUTME: Tests that every LLM call tags its trace with short hashes of the prompts it sent.
# ABOUTME: Reads metadata through a real callback handler; an unreachable model keeps it offline.
from typing import Any
from uuid import UUID

from langchain_core.callbacks import BaseCallbackHandler
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.graph import AssistantGraph
from store_assistant.agent.llm_prompts import (
    CLASSIFY_SYSTEM_PROMPT,
    SUMMARY_REQUEST_TEMPLATE,
    SUMMARY_SYSTEM_PROMPT,
    trace_metadata,
)
from store_assistant.agent.state import AssistantState


class ChatModelMetadataRecorder(BaseCallbackHandler):
    """Keeps the run metadata of every chat model call, as a tracer would see it."""

    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    def on_chat_model_start(
        self,
        serialized: dict[str, Any],
        messages: list[list[BaseMessage]],
        *,
        run_id: UUID,
        parent_run_id: UUID | None = None,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        self.calls.append(metadata or {})


def _recording_config(recorder: ChatModelMetadataRecorder) -> RunnableConfig:
    return {"configurable": {"thread_id": "thread-1"}, "callbacks": [recorder]}


def test_classification_call_is_tagged_with_the_classify_prompt(
    graph: AssistantGraph, unreachable_deps: GraphDeps
) -> None:
    recorder = ChatModelMetadataRecorder()
    turn: AssistantState = {"messages": [HumanMessage("hi")]}

    graph.invoke(turn, _recording_config(recorder), context=unreachable_deps)

    [classify_call] = recorder.calls
    expected = trace_metadata(classify_system=CLASSIFY_SYSTEM_PROMPT)
    assert expected.items() <= classify_call.items()


def test_summary_call_is_tagged_with_both_summary_prompts(
    graph: AssistantGraph, unreachable_deps: GraphDeps
) -> None:
    recorder = ChatModelMetadataRecorder()
    config = _recording_config(recorder)
    done: AssistantState = {
        "messages": [HumanMessage("I'm done")],
        "actions": [],
        "classification": {"intent": "done", "store_name": None, "phone": None},
    }
    graph.update_state(config, done, as_node="classify")

    graph.invoke(None, config, context=unreachable_deps)

    [summary_call] = recorder.calls
    expected = trace_metadata(
        summary_system=SUMMARY_SYSTEM_PROMPT, summary_request=SUMMARY_REQUEST_TEMPLATE
    )
    assert expected.items() <= summary_call.items()
