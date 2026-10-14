# ABOUTME: End-to-end test of the Streamlit app when the LLM cannot be reached.
# ABOUTME: Points the real OpenAI client at a closed local port and drives the page headlessly.
import pytest

from store_assistant.agent.nodes.classify import LLM_UNAVAILABLE_REPLY
from store_assistant.tests.support import UNREACHABLE_LLM_BASE_URL
from store_assistant.ui.tests.page import chat_lines, open_page, say


def test_unreachable_llm_shows_a_retry_reply_and_keeps_the_chat_open(
    app_environment: None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("OPENAI_BASE_URL", UNREACHABLE_LLM_BASE_URL)
    app = open_page()

    say(app, "save Costco, number 555-876-5432")

    assert not app.exception
    assert chat_lines(app)[-1] == ("assistant", LLM_UNAVAILABLE_REPLY)
    assert len(app.chat_input) == 1
