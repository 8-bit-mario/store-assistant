# ABOUTME: The clock type shared by components that record or compare times.
# ABOUTME: Production code uses utc_now; tests inject their own clock.
from collections.abc import Callable
from datetime import UTC, datetime

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    """Current time in UTC (timezone-aware)."""
    return datetime.now(UTC)
