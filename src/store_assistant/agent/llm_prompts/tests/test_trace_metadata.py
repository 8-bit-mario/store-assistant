# ABOUTME: Tests the trace metadata that tags an LLM call with short hashes of its prompt texts.
# ABOUTME: Pure checks; no LLM call.
import hashlib

from store_assistant.agent.llm_prompts import trace_metadata


def _short_sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:12]


def test_each_prompt_is_tagged_with_a_short_hash_of_its_text() -> None:
    metadata = trace_metadata(greeter="Hello.\n", farewell="Bye.\n")

    assert metadata == {
        "greeter_prompt_sha": _short_sha("Hello.\n"),
        "farewell_prompt_sha": _short_sha("Bye.\n"),
    }
