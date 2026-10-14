# ABOUTME: Tests for interpreting short yes/no replies to confirmation prompts.
# ABOUTME: Unclear replies return None so the caller can ask again.
import pytest

from store_assistant.agent.answers import parse_yes_no


@pytest.mark.parametrize("text", ["yes", "Y", " yeah ", "sure", "Replace", "yes please", "ok"])
def test_affirmative_replies(text: str) -> None:
    assert parse_yes_no(text) is True


@pytest.mark.parametrize("text", ["no", "N", "nope", "keep", "keep it", "no thanks"])
def test_negative_replies(text: str) -> None:
    assert parse_yes_no(text) is False


@pytest.mark.parametrize("text", ["maybe", "", "what?", "yes and no"])
def test_unclear_replies(text: str) -> None:
    assert parse_yes_no(text) is None
