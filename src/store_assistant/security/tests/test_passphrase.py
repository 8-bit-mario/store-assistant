# ABOUTME: Tests for the constant-time passphrase comparison that gates store lookups.
# ABOUTME: Covers exact matches, near misses, whitespace handling and misconfiguration.
import pytest

from store_assistant.security.passphrase import is_correct_passphrase

EXPECTED = "zebra-quartz-71"


@pytest.mark.parametrize("attempt", ["zebra-quartz-71", "  zebra-quartz-71\n"])
def test_matching_attempt_is_accepted(attempt: str) -> None:
    assert is_correct_passphrase(attempt, EXPECTED) is True


@pytest.mark.parametrize("attempt", ["zebra-quartz-72", "Zebra-Quartz-71", "", "zebra"])
def test_non_matching_attempt_is_rejected(attempt: str) -> None:
    assert is_correct_passphrase(attempt, EXPECTED) is False


def test_non_ascii_passphrase_matches() -> None:
    assert is_correct_passphrase("café-ñandú", "café-ñandú") is True


def test_blank_expected_passphrase_is_a_configuration_error() -> None:
    with pytest.raises(ValueError):
        is_correct_passphrase("anything", "  ")
