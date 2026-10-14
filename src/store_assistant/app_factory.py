# ABOUTME: Composition root wiring settings, SQLite files, the LLM and the graph together.
# ABOUTME: Used by the Streamlit app and by tests so both run the same assembly.
import sqlite3
from contextlib import ExitStack

from langgraph.checkpoint.sqlite import SqliteSaver

from store_assistant.agent.classify import build_chat_model
from store_assistant.agent.deps import GraphDeps
from store_assistant.agent.graph import build_graph
from store_assistant.clock import Clock, utc_now
from store_assistant.config import Settings
from store_assistant.conversation.turns import TurnHandler
from store_assistant.storage.database import connect
from store_assistant.storage.stores import StoreRepository
from store_assistant.storage.summaries import SummaryRepository

APP_DB_FILENAME = "store_assistant.sqlite"
CHECKPOINT_DB_FILENAME = "checkpoints.sqlite"


def build_turn_handler(
    settings: Settings, resources: ExitStack, clock: Clock = utc_now
) -> TurnHandler:
    """
    Assemble a ready-to-use turn handler.

    Args:
        settings: Application settings.
        resources: Owns the database connections; closing it closes them.
        clock: Time source for inactivity checks.

    Returns:
        A turn handler backed by the app database and the checkpoint database.
    """
    app_db = connect(settings.data_dir / APP_DB_FILENAME)
    resources.callback(app_db.close)
    checkpoint_db = sqlite3.connect(
        settings.data_dir / CHECKPOINT_DB_FILENAME, check_same_thread=False
    )
    resources.callback(checkpoint_db.close)

    deps = GraphDeps(
        model=build_chat_model(settings),
        stores=StoreRepository(app_db),
        summaries=SummaryRepository(app_db),
    )
    return TurnHandler(build_graph(SqliteSaver(checkpoint_db)), deps, settings, clock)
