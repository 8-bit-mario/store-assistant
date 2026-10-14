# ABOUTME: Streamlit chat page for the store assistant (uv run streamlit run <this file>).
# ABOUTME: Shows the conversation, asks for passphrases in a password field, and offers Cancel.
from contextlib import ExitStack
from dataclasses import dataclass

import streamlit as st

from store_assistant.app_factory import build_turn_handler
from store_assistant.config import Settings, get_settings
from store_assistant.conversation.turns import TurnHandler, TurnResult
from store_assistant.ui.inactivity import inactivity_notice
from store_assistant.ui.transcript import transcript_lines


@dataclass(frozen=True)
class OpenApp:
    """A turn handler plus the resources (database connections) it holds open."""

    turns: TurnHandler
    resources: ExitStack


def _release(app: OpenApp) -> None:
    app.resources.close()


@st.cache_resource(on_release=_release, show_spinner=False)
def open_app(data_dir: str, _settings: Settings) -> OpenApp:
    """One shared app per data directory for the life of the server."""
    resources = ExitStack()
    return OpenApp(build_turn_handler(_settings, resources), resources)


def render_conversation(result: TurnResult) -> None:
    """Draw every line of the conversation, including a question awaiting an answer."""
    for role, text in transcript_lines(result):
        with st.chat_message(role):
            st.markdown(text)


def render_input(turns: TurnHandler, thread_id: str, result: TurnResult) -> None:
    """Draw the right input for the moment: password field, chat box, and Cancel."""
    pending = result.pending
    if pending is not None and pending.kind == "passphrase":
        with st.form("passphrase_form", clear_on_submit=True):
            passphrase = st.text_input("Passphrase", type="password", key="passphrase")
            submitted = st.form_submit_button("Submit", key="submit_passphrase")
        if submitted:
            turns.send(thread_id, passphrase)
            st.rerun()
    elif text := st.chat_input("Type a message"):
        turns.send(thread_id, text)
        st.rerun()
    if pending is not None and st.button("Cancel", key="cancel"):
        turns.cancel_operation(thread_id, "user")
        st.rerun()


def current_thread_id(turns: TurnHandler) -> str:
    """The conversation named in the URL, starting a new one when the URL has none."""
    thread_id = st.query_params.get("thread")
    if not thread_id:
        thread_id = turns.start()
        st.query_params["thread"] = thread_id
    return thread_id


def render_sidebar(turns: TurnHandler, thread_id: str) -> None:
    """Show the conversation id and a way to start over."""
    st.sidebar.caption(f"Conversation: {thread_id}")
    if st.sidebar.button("New conversation", key="new_conversation"):
        st.query_params["thread"] = turns.start()
        st.rerun()


@st.fragment(run_every="1s")
def watch_inactivity(turns: TurnHandler, thread_id: str) -> None:
    """While a question waits, check in after a pause and cancel once it expires."""
    status = turns.inactivity(thread_id)
    if status == "expired":
        turns.cancel_operation(thread_id, "timeout")
        st.rerun(scope="app")
    if notice := inactivity_notice(status):
        st.warning(notice)


def main() -> None:
    """Draw the page for the conversation in the URL."""
    settings = get_settings()
    turns = open_app(str(settings.data_dir), settings).turns
    thread_id = current_thread_id(turns)

    st.title("Store Assistant")
    render_sidebar(turns, thread_id)
    result = turns.view(thread_id)
    render_conversation(result)
    if result.ended:
        st.info("This conversation has ended. Start a new conversation from the sidebar.")
    else:
        render_input(turns, thread_id, result)
    if result.pending is not None:
        watch_inactivity(turns, thread_id)


main()
