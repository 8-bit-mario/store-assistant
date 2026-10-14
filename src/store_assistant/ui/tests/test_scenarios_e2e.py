# ABOUTME: Full conversation scenarios through the Streamlit page with the real LLM.
# ABOUTME: Checks saved rows, summaries, and that the passphrase never appears anywhere.
import sqlite3
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from store_assistant.storage.stores import StoreRepository
from store_assistant.storage.summaries import SummaryRepository
from store_assistant.tests.support import TEST_PASSPHRASE
from store_assistant.ui.tests.page import chat_lines, enter_passphrase, say, thread_of

pytestmark = pytest.mark.llm


def _assert_passphrase_absent(app: AppTest, data_dir: Path) -> None:
    stored = b"".join(path.read_bytes() for path in data_dir.iterdir() if path.is_file())
    shown = " ".join(text for _, text in chat_lines(app))
    assert TEST_PASSPHRASE.encode() not in stored
    assert TEST_PASSPHRASE not in shown
    assert b"Trader Joe" in stored  # the scan reads real content, so absence is meaningful


def test_save_lookup_miss_and_finish(app: AppTest, db: sqlite3.Connection, tmp_path: Path) -> None:
    say(app, "save Trader Joe's, number (555) 234-5678")
    say(app, "what's the number for Trader Joe's?")
    enter_passphrase(app, TEST_PASSPHRASE)
    found_reply = chat_lines(app)[-1][1]
    say(app, "and Costco?")
    enter_passphrase(app, TEST_PASSPHRASE)
    miss_reply = chat_lines(app)[-1][1]
    say(app, "I'm done")

    summary = SummaryRepository(db).find_by_thread(thread_of(app))
    saved = StoreRepository(db).find_by_name("Trader Joe's")
    assert saved is not None and saved.phone == "+15552345678"
    assert "+15552345678" in found_reply
    assert "Costco" in miss_reply
    assert summary is not None and summary.end_reason == "user_done"
    assert len(app.chat_input) == 0
    _assert_passphrase_absent(app, tmp_path)


def test_repeated_off_topic_messages_end_the_conversation(
    app: AppTest, db: sqlite3.Connection
) -> None:
    say(app, "who won the world cup?")
    say(app, "tell me a joke")
    say(app, "what's the weather in Paris?")

    summary = SummaryRepository(db).find_by_thread(thread_of(app))
    assert summary is not None and summary.end_reason == "off_topic"
    assert len(app.chat_input) == 0


def test_summary_mentions_off_topic_messages_when_the_user_finishes(
    app: AppTest, db: sqlite3.Connection
) -> None:
    say(app, "save Costco, number (555) 876-5432")
    say(app, "who won the world cup?")
    say(app, "tell me a joke")
    say(app, "I'm done")

    summary = SummaryRepository(db).find_by_thread(thread_of(app))
    assert summary is not None and summary.end_reason == "user_done"
    assert "off-topic" in summary.summary
    assert chat_lines(app)[-1] == ("assistant", summary.summary)
