# ABOUTME: Fixtures shared by the agent's graph tests.
# ABOUTME: Provides the compiled graph and dependencies whose chat model can never connect.
import sqlite3

import pytest
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.sqlite import SqliteSaver
from pydantic import SecretStr

from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.graph import AssistantGraph, build_graph
from store_assistant.config import Settings
from store_assistant.storage.stores import StoreRepository
from store_assistant.storage.summaries import SummaryRepository
from store_assistant.tests.support import UNREACHABLE_LLM_BASE_URL


@pytest.fixture
def graph(checkpointer: SqliteSaver) -> AssistantGraph:
    """The compiled assistant graph over the test's checkpoint database."""
    return build_graph(checkpointer)


@pytest.fixture
def unreachable_deps(settings: Settings, db: sqlite3.Connection) -> GraphDeps:
    """Real dependencies, except the chat model points at a closed local port."""
    unreachable = ChatOpenAI(
        model=settings.openai_model,
        base_url=UNREACHABLE_LLM_BASE_URL,
        api_key=SecretStr("unused"),
        max_retries=0,
    )
    return GraphDeps(
        model=unreachable,
        stores=StoreRepository(db),
        summaries=SummaryRepository(db),
    )
