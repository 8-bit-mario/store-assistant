# ABOUTME: Dependencies handed to graph nodes through LangGraph's per-run context.
# ABOUTME: Holds the chat model and repositories; never holds the lookup passphrase.
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel

from store_assistant.storage.stores import StoreRepository
from store_assistant.storage.summaries import SummaryRepository


@dataclass(frozen=True)
class GraphDeps:
    """What nodes need to talk to the LLM and the database."""

    model: BaseChatModel
    stores: StoreRepository
    summaries: SummaryRepository
