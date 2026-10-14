# ABOUTME: Tests how the chat model is configured; builds the client without calling the LLM.
# ABOUTME: Guards against a hung request freezing a turn for the client's default ten minutes.
from store_assistant.agent.classify import build_chat_model
from store_assistant.config import Settings


def test_chat_model_gives_up_on_a_request_after_thirty_seconds(settings: Settings) -> None:
    assert build_chat_model(settings).request_timeout == 30
