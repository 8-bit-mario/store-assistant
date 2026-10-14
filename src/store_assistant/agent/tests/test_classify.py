# ABOUTME: Tests that the real LLM classifies user messages into intents and extracts details.
# ABOUTME: Calls OpenAI; asserts on intents and extracted fields, never on wording.
import pytest
from langchain_core.messages import AIMessage, HumanMessage

from store_assistant.agent.classify import build_chat_model, classify
from store_assistant.agent.state import Intent
from store_assistant.config import Settings

pytestmark = pytest.mark.llm


@pytest.mark.parametrize(
    ("text", "intent"),
    [
        ("save Trader Joe's 555-234-5678", "save"),
        ("I want to add a store", "save"),
        ("what's the number for Costco", "lookup"),
        ("can you find Kroger for me?", "lookup"),
        ("I'm done", "done"),
        ("I'm good", "done"),
        ("that's all, bye", "done"),
        ("who won the world cup?", "off_topic"),
        ("write me a poem about cats", "off_topic"),
        ("hi", "on_topic_chat"),
        ("what can you do?", "on_topic_chat"),
        ("thanks!", "on_topic_chat"),
        ("thanks, I'm good", "done"),
        ("that's all", "done"),
        ("hi! save Kroger 555-123-4567", "save"),
        ("tell me a joke", "off_topic"),
        ("what's the weather today?", "off_topic"),
    ],
)
def test_classifies_intent(settings: Settings, text: str, intent: Intent) -> None:
    model = build_chat_model(settings)

    result = classify(model, [HumanMessage(text)])

    assert result["intent"] == intent


def test_extracts_store_name_and_raw_phone(settings: Settings) -> None:
    model = build_chat_model(settings)

    result = classify(model, [HumanMessage("save Trader Joe's, the number is (555) 234-5678")])

    assert result["intent"] == "save"
    assert result["store_name"] == "Trader Joe's"
    assert result["phone"] == "(555) 234-5678"


def test_extracts_store_name_for_lookup(settings: Settings) -> None:
    model = build_chat_model(settings)

    result = classify(model, [HumanMessage("what's the phone number for Costco?")])

    assert result["intent"] == "lookup"
    assert result["store_name"] == "Costco"
    assert result["phone"] is None


def test_uses_earlier_messages_for_follow_ups(settings: Settings) -> None:
    model = build_chat_model(settings)
    history = [
        HumanMessage("what's the number for Costco?"),
        AIMessage("Costco: +15552345678."),
        HumanMessage("and Kroger?"),
    ]

    result = classify(model, history)

    assert result["intent"] == "lookup"
    assert result["store_name"] == "Kroger"


@pytest.mark.parametrize(
    "text",
    ["I want to look up a store", "I want to save a store", "find the store for me", "add a shop"],
)
def test_generic_store_words_are_not_a_store_name(settings: Settings, text: str) -> None:
    model = build_chat_model(settings)

    result = classify(model, [HumanMessage(text)])

    assert result["store_name"] is None


def test_save_extracts_phone_exactly_as_typed(settings: Settings) -> None:
    model = build_chat_model(settings)

    result = classify(model, [HumanMessage("save Kroger 555-123-4567")])

    assert result["intent"] == "save"
    assert result["store_name"] == "Kroger"
    assert result["phone"] == "555-123-4567"
