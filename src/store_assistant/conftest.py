# ABOUTME: Shared pytest setup: loads .env and routes test traces to a separate LangSmith project.
# ABOUTME: Holds fixtures used across the package's test suites.
import dataclasses
import os
import sqlite3
from collections.abc import Callable, Iterator
from contextlib import ExitStack
from pathlib import Path
from typing import Any

import pytest
from dotenv import load_dotenv
from langgraph.checkpoint.sqlite import SqliteSaver

from store_assistant.agent.graph import build_graph
from store_assistant.app_factory import APP_DB_FILENAME, CHECKPOINT_DB_FILENAME, build_turn_handler
from store_assistant.config import Settings, get_settings
from store_assistant.conversation.turns import TurnHandler
from store_assistant.storage.database import connect
from store_assistant.tests.support import TEST_PASSPHRASE

TEST_LANGSMITH_PROJECT = "store-assistant-tests"


def pytest_configure(config: pytest.Config) -> None:
    """Load credentials before tests run and keep test traces out of the demo project."""
    load_dotenv()
    os.environ["LANGSMITH_PROJECT"] = TEST_LANGSMITH_PROJECT


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    """The app database private to one test; the same file the `turns` fixture writes to."""
    return tmp_path / APP_DB_FILENAME


@pytest.fixture
def db(db_path: Path) -> Iterator[sqlite3.Connection]:
    """An open app database with the schema created, closed after the test."""
    conn = connect(db_path)
    yield conn
    conn.close()


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    """Real settings from .env, with a test passphrase and data files kept in tmp_path."""
    return dataclasses.replace(
        get_settings(), data_dir=tmp_path, store_lookup_passphrase=TEST_PASSPHRASE
    )


@pytest.fixture
def checkpointer(tmp_path: Path) -> Iterator[SqliteSaver]:
    """A real SQLite checkpointer in the test's tmp_path, closed after the test."""
    conn = sqlite3.connect(tmp_path / "checkpoints.sqlite", check_same_thread=False)
    yield SqliteSaver(conn)
    conn.close()


@pytest.fixture
def turns(settings: Settings) -> Iterator[TurnHandler]:
    """A fully wired turn handler over real databases in tmp_path, closed after the test."""
    with ExitStack() as resources:
        yield build_turn_handler(settings, resources)


@pytest.fixture
def thread_state(tmp_path: Path) -> Iterator[Callable[[str], dict[str, Any]]]:
    """Reads a thread's saved graph state straight from the test's checkpoint database."""
    conn = sqlite3.connect(tmp_path / CHECKPOINT_DB_FILENAME, check_same_thread=False)
    graph = build_graph(SqliteSaver(conn))

    def read(thread_id: str) -> dict[str, Any]:
        return graph.get_state({"configurable": {"thread_id": thread_id}}).values

    yield read
    conn.close()
