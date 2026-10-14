# ABOUTME: End-to-end test of the inactivity check-in and timeout on the Streamlit page.
# ABOUTME: Uses 1s/2s thresholds from the environment and waits in real time.
import sqlite3
import time

import pytest

from store_assistant.storage.stores import StoreRepository
from store_assistant.ui.inactivity import CHECK_IN_NOTICE
from store_assistant.ui.tests.page import chat_lines, open_page, say

pytestmark = pytest.mark.llm


def test_unanswered_prompt_checks_in_then_cancels(
    app_environment: None, monkeypatch: pytest.MonkeyPatch, db: sqlite3.Connection
) -> None:
    monkeypatch.setenv("STORE_ASSISTANT_CHECK_IN_SECONDS", "1")
    monkeypatch.setenv("STORE_ASSISTANT_EXPIRE_SECONDS", "2")
    page = open_page()
    say(page, "I want to save a store")
    say(page, "Costco")

    time.sleep(1.2)
    page.run()
    assert any(CHECK_IN_NOTICE in warning.value for warning in page.warning)

    time.sleep(1.0)
    page.run()
    assert "No response" in chat_lines(page)[-1][1]
    assert not any(CHECK_IN_NOTICE in warning.value for warning in page.warning)
    assert StoreRepository(db).find_by_name("Costco") is None
