# ABOUTME: Rules for cancelling an in-progress operation: cancel keywords and inactivity timing.
# ABOUTME: Pure functions; the caller supplies the clock and the thresholds.
from datetime import datetime, timedelta
from typing import Literal

CANCEL_KEYWORDS = frozenset({"cancel", "stop", "never mind", "nevermind"})

InactivityStatus = Literal["active", "check_in", "expired"]


def is_cancel_request(text: str) -> bool:
    """Return True if the whole reply is a cancel keyword, ignoring case and end punctuation."""
    return text.strip().rstrip(".!").strip().lower() in CANCEL_KEYWORDS


def inactivity_status(
    asked_at: datetime,
    now: datetime,
    check_in_after: timedelta,
    expire_after: timedelta,
) -> InactivityStatus:
    """
    Decide how long-unanswered a prompt is.

    Args:
        asked_at: When the prompt was shown (timezone-aware).
        now: The current time (timezone-aware).
        check_in_after: Silence after which the user is asked if they are still there.
        expire_after: Silence after which the operation is cancelled.

    Returns:
        "active", "check_in" or "expired".

    Raises:
        ValueError: If either datetime is naive.
    """
    if asked_at.tzinfo is None or now.tzinfo is None:
        raise ValueError("inactivity_status needs timezone-aware datetimes")
    elapsed = now - asked_at
    if elapsed >= expire_after:
        return "expired"
    if elapsed >= check_in_after:
        return "check_in"
    return "active"
