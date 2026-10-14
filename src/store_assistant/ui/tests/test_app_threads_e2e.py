# ABOUTME: End-to-end tests for conversation threads in the Streamlit app's URL.
# ABOUTME: Covers resuming by URL, starting a new conversation, and read-only ended threads.
import pytest
from streamlit.testing.v1 import AppTest

from store_assistant.ui.tests.page import chat_lines, open_page, say, thread_of

pytestmark = pytest.mark.llm


def test_first_visit_puts_a_thread_in_the_url(app: AppTest) -> None:
    assert thread_of(app)


def test_reopening_the_url_restores_the_conversation(app: AppTest) -> None:
    say(app, "hi")
    thread_id = thread_of(app)

    reopened = open_page(thread_id)

    assert thread_of(reopened) == thread_id
    assert chat_lines(reopened) == chat_lines(app)
    assert chat_lines(reopened)[0] == ("user", "hi")


def test_new_conversation_starts_an_empty_thread(app: AppTest) -> None:
    say(app, "hi")
    first_thread = thread_of(app)

    app.sidebar.button(key="new_conversation").click().run()

    assert thread_of(app) != first_thread
    assert chat_lines(app) == []


def test_ended_conversation_is_read_only(app: AppTest) -> None:
    say(app, "I'm done")

    assert len(app.chat_input) == 0
    assert any("ended" in info.value for info in app.info)
    assert chat_lines(app)[-1][0] == "assistant"


def test_ended_conversation_stays_read_only_when_reopened(app: AppTest) -> None:
    say(app, "I'm done")

    reopened = open_page(thread_of(app))

    assert len(reopened.chat_input) == 0
    assert chat_lines(reopened) == chat_lines(app)
