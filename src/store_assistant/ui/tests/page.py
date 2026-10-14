# ABOUTME: Helpers for driving the Streamlit page headlessly with AppTest in the UI tests.
# ABOUTME: Opens the page, types and submits input, and reads back the chat lines.
import logging
from pathlib import Path

from streamlit.testing.v1 import AppTest

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
APP_TIMEOUT_SECONDS = 120
SCRIPT_CONTEXT_LOGGER = "streamlit.runtime.scriptrunner_utils.script_run_context"
KNOWN_APPTEST_WARNING = "missing ScriptRunContext"


class RecordingHandler(logging.Handler):
    """Keeps log records in memory instead of printing them."""

    def __init__(self) -> None:
        super().__init__()
        self.records: list[logging.LogRecord] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.records.append(record)


def open_page(thread_id: str | None = None) -> AppTest:
    """Load the page the way a browser would, optionally at a conversation's URL."""
    app_test = _quiet_app_test()
    if thread_id is not None:
        app_test.query_params["thread"] = thread_id
    return app_test.run()


def thread_of(app: AppTest) -> str:
    """The conversation id the page put in its URL."""
    value = app.query_params["thread"]
    return str(value[0] if isinstance(value, list) else value)


def _quiet_app_test() -> AppTest:
    """Build an AppTest, checking that Streamlit logs only its known constructor warning."""
    handler = RecordingHandler()
    logger = logging.getLogger(SCRIPT_CONTEXT_LOGGER)
    handlers, propagate = logger.handlers, logger.propagate
    logger.handlers, logger.propagate = [handler], False
    try:
        app_test = AppTest.from_file(str(APP_PATH), default_timeout=APP_TIMEOUT_SECONDS)
    finally:
        logger.handlers, logger.propagate = handlers, propagate
    assert all(KNOWN_APPTEST_WARNING in record.getMessage() for record in handler.records)
    return app_test


def say(app: AppTest, text: str) -> AppTest:
    """Type a chat message and submit it."""
    return app.chat_input[0].set_value(text).run()


def enter_passphrase(app: AppTest, text: str) -> AppTest:
    """Type into the password field and submit it."""
    app.text_input(key="passphrase").input(text)
    return app.button(key="submit_passphrase").click().run()


def chat_lines(app: AppTest) -> list[tuple[str, str]]:
    """The (role, text) pairs currently shown in the chat."""
    return [(message.name, message.markdown[0].value) for message in app.chat_message]
