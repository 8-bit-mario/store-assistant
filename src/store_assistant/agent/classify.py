# ABOUTME: Uses the LLM to classify the user's latest message and extract store details.
# ABOUTME: Returns a strict structured result; phone text is extracted raw and validated in code.
from collections.abc import Sequence
from typing import cast

from langchain_core.exceptions import (
    ModelAPIError,
    ModelConnectionError,
    ModelRateLimitError,
    ModelTimeoutError,
)
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import BaseMessage, SystemMessage
from langchain_openai import ChatOpenAI

from store_assistant.agent.llm_prompts import CLASSIFY_SYSTEM_PROMPT, trace_metadata
from store_assistant.agent.state import Classification
from store_assistant.config import Settings
from store_assistant.validation.store_name import is_generic_store_reference

HISTORY_WINDOW = 6
LLM_TIMEOUT_SECONDS = 30
LLM_OUTAGE_ERRORS = (ModelAPIError, ModelConnectionError, ModelRateLimitError, ModelTimeoutError)


def build_chat_model(settings: Settings) -> ChatOpenAI:
    """Create the chat model used for classification and summaries."""
    return ChatOpenAI(model=settings.openai_model, temperature=0, timeout=LLM_TIMEOUT_SECONDS)


def classify(model: BaseChatModel, messages: Sequence[BaseMessage]) -> Classification:
    """
    Classify the latest user message, using recent history for context.

    Args:
        model: The chat model.
        messages: Conversation transcript ending with the user's latest message.

    Returns:
        The intent plus any store name and raw phone text found in the latest message.
    """
    structured = model.with_structured_output(Classification, method="json_schema", strict=True)
    prompt = [SystemMessage(CLASSIFY_SYSTEM_PROMPT), *messages[-HISTORY_WINDOW:]]
    metadata = trace_metadata(classify_system=CLASSIFY_SYSTEM_PROMPT)
    result = cast(Classification, structured.invoke(prompt, config={"metadata": metadata}))
    return {
        "intent": result["intent"],
        "store_name": _named_store_or_none(result["store_name"]),
        "phone": _blank_to_none(result["phone"]),
    }


def _named_store_or_none(value: str | None) -> str | None:
    """Generic references such as "the store" are not names."""
    name = _blank_to_none(value)
    return None if name is None or is_generic_store_reference(name) else name


def _blank_to_none(value: str | None) -> str | None:
    """The model sometimes returns "" instead of null for a missing value."""
    return value.strip() or None if value is not None else None
