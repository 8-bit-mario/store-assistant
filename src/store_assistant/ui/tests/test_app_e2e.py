# ABOUTME: End-to-end tests of the Streamlit app with the real LLM and SQLite files.
# ABOUTME: Drives the page headlessly and checks what is shown and what is saved.
import sqlite3

import pytest
from streamlit.proto.TextInput_pb2 import TextInput
from streamlit.testing.v1 import AppTest

from store_assistant.agent.nodes.capability import CAPABILITY_REPLY
from store_assistant.storage.stores import StoreRepository
from store_assistant.tests.support import TEST_PASSPHRASE
from store_assistant.ui.tests.page import chat_lines, enter_passphrase, say
from store_assistant.ui.transcript import PASSPHRASE_MASK

pytestmark = pytest.mark.llm


def test_greeting_gets_capability_reply(app: AppTest) -> None:
    say(app, "hi, what can you do?")

    assert chat_lines(app)[-1] == ("assistant", CAPABILITY_REPLY)


def test_save_flow_saves_the_store(app: AppTest, db: sqlite3.Connection) -> None:
    say(app, "I want to save a store")
    say(app, "Costco")
    say(app, "555-876-5432")

    saved = StoreRepository(db).find_by_name("Costco")
    assert saved is not None and saved.phone == "+15558765432"
    assert "+15558765432" in chat_lines(app)[-1][1]


def test_lookup_uses_a_password_field(app: AppTest, db: sqlite3.Connection) -> None:
    StoreRepository(db).add("Costco", "+15552345678")
    say(app, "what's the number for Costco?")

    assert len(app.chat_input) == 0
    assert app.text_input(key="passphrase").proto.type == TextInput.Type.PASSWORD

    enter_passphrase(app, TEST_PASSPHRASE)

    lines = chat_lines(app)
    assert "+15552345678" in lines[-1][1]
    assert ("user", PASSPHRASE_MASK) in lines
    assert all(TEST_PASSPHRASE not in text for _, text in lines)


def test_cancel_button_stops_the_operation(app: AppTest, db: sqlite3.Connection) -> None:
    say(app, "I want to save a store")
    say(app, "Costco")

    app.button(key="cancel").click().run()

    assert StoreRepository(db).find_by_name("Costco") is None
    assert "cancelled" in chat_lines(app)[-1][1]
    assert len(app.button) == 0 or all(b.key != "cancel" for b in app.button)


def test_typed_cancel_shows_the_users_word_then_the_cancellation(app: AppTest) -> None:
    say(app, "I want to save a store")

    say(app, "never mind")

    assert chat_lines(app)[-2:] == [
        ("user", "never mind"),
        ("assistant", "Okay, I cancelled saving the store."),
    ]
