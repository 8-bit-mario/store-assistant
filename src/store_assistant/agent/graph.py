# ABOUTME: Assembles the store assistant state machine: classify, then route to a handler node.
# ABOUTME: Nodes receive GraphDeps as run context; state is persisted by the given checkpointer.
from collections.abc import Hashable

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.nodes.capability import answer_capability
from store_assistant.agent.nodes.classify import classify_message
from store_assistant.agent.nodes.lookup import lookup_store
from store_assistant.agent.nodes.off_topic import handle_off_topic
from store_assistant.agent.nodes.save import save_store
from store_assistant.agent.nodes.summarize import summarize_and_end
from store_assistant.agent.routing import route_after_classify, route_after_off_topic
from store_assistant.agent.state import AssistantState

AssistantGraph = CompiledStateGraph[AssistantState, GraphDeps, AssistantState, AssistantState]

INTENT_ROUTES: dict[Hashable, str] = {
    "save_store": "save_store",
    "lookup_store": "lookup_store",
    "answer_capability": "answer_capability",
    "handle_off_topic": "handle_off_topic",
    "summarize_and_end": "summarize_and_end",
    END: END,
}
OFF_TOPIC_ROUTES: dict[Hashable, str] = {END: END, "summarize_and_end": "summarize_and_end"}


def build_graph(
    checkpointer: BaseCheckpointSaver[str],
) -> AssistantGraph:
    """Build and compile the assistant graph."""
    builder = StateGraph(AssistantState, context_schema=GraphDeps)
    builder.add_node("classify", classify_message)
    builder.add_node("answer_capability", answer_capability)
    builder.add_node("handle_off_topic", handle_off_topic)
    builder.add_node("save_store", save_store)
    builder.add_node("lookup_store", lookup_store)
    builder.add_node("summarize_and_end", summarize_and_end)

    builder.add_edge(START, "classify")
    builder.add_conditional_edges("classify", route_after_classify, INTENT_ROUTES)
    builder.add_edge("answer_capability", END)
    builder.add_edge("save_store", END)
    builder.add_edge("lookup_store", END)
    builder.add_conditional_edges("handle_off_topic", route_after_off_topic, OFF_TOPIC_ROUTES)
    builder.add_edge("summarize_and_end", END)
    return builder.compile(checkpointer=checkpointer)
