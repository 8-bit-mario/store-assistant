# ABOUTME: Every prompt sent to the LLM, one module per prompt; git holds their history.
# ABOUTME: Written for GPT-5-family models: sectioned, each rule stated once, no contradictions.
import hashlib

from store_assistant.agent.llm_prompts.classify_system import CLASSIFY_SYSTEM_PROMPT
from store_assistant.agent.llm_prompts.summary_request import SUMMARY_REQUEST_TEMPLATE
from store_assistant.agent.llm_prompts.summary_system import SUMMARY_SYSTEM_PROMPT

__all__ = [
    "CLASSIFY_SYSTEM_PROMPT",
    "SUMMARY_REQUEST_TEMPLATE",
    "SUMMARY_SYSTEM_PROMPT",
    "trace_metadata",
]


def trace_metadata(**prompts: str) -> dict[str, str]:
    """
    Tag a trace with a short hash of each prompt's text, so it shows exactly which text was sent.

    Example:
        >>> trace_metadata(classify_system=CLASSIFY_SYSTEM_PROMPT)
        {'classify_system_prompt_sha': '...'}
    """
    return {
        f"{name}_prompt_sha": hashlib.sha256(text.encode()).hexdigest()[:12]
        for name, text in prompts.items()
    }
