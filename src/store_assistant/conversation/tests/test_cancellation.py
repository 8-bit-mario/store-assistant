# ABOUTME: Tests for cancel keyword detection and the inactivity timing rule.
# ABOUTME: Uses fixed timestamps so threshold boundaries are checked without waiting.
from datetime import UTC, datetime, timedelta

import pytest

from store_assistant.conversation.cancellation import inactivity_status, is_cancel_request

ASKED_AT = datetime(2026, 10, 13, 12, 0, 0, tzinfo=UTC)
CHECK_IN_AFTER = timedelta(seconds=60)
EXPIRE_AFTER = timedelta(seconds=90)


@pytest.mark.parametrize("text", ["cancel", " Cancel ", "STOP!", "never mind", "nevermind."])
def test_cancel_keywords_are_recognized(text: str) -> None:
    assert is_cancel_request(text) is True


@pytest.mark.parametrize("text", ["cancel my order at Costco", "don't stop", "", "Costco"])
def test_other_text_is_not_a_cancel_request(text: str) -> None:
    assert is_cancel_request(text) is False


@pytest.mark.parametrize(
    ("elapsed_seconds", "status"),
    [
        (0, "active"),
        (59, "active"),
        (60, "check_in"),
        (89, "check_in"),
        (90, "expired"),
        (600, "expired"),
    ],
)
def test_inactivity_status_at_boundaries(elapsed_seconds: int, status: str) -> None:
    now = ASKED_AT + timedelta(seconds=elapsed_seconds)

    assert inactivity_status(ASKED_AT, now, CHECK_IN_AFTER, EXPIRE_AFTER) == status


def test_inactivity_status_with_short_thresholds() -> None:
    one, two = timedelta(seconds=1), timedelta(seconds=2)

    assert inactivity_status(ASKED_AT, ASKED_AT + one, one, two) == "check_in"
    assert inactivity_status(ASKED_AT, ASKED_AT + two, one, two) == "expired"


def test_naive_datetimes_are_rejected() -> None:
    naive = datetime(2026, 10, 13, 12, 0, 0)

    with pytest.raises(ValueError):
        inactivity_status(naive, ASKED_AT, CHECK_IN_AFTER, EXPIRE_AFTER)
    with pytest.raises(ValueError):
        inactivity_status(ASKED_AT, naive, CHECK_IN_AFTER, EXPIRE_AFTER)
