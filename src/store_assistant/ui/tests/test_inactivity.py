# ABOUTME: Tests which inactivity notice the chat page shows for each inactivity status.
# ABOUTME: Pure mapping; the timing itself is tested in the conversation layer.
import pytest

from store_assistant.conversation.cancellation import InactivityStatus
from store_assistant.ui.inactivity import CHECK_IN_NOTICE, inactivity_notice


def test_check_in_asks_if_the_user_is_still_there() -> None:
    assert inactivity_notice("check_in") == CHECK_IN_NOTICE


@pytest.mark.parametrize("status", ["active", "expired", None])
def test_other_statuses_show_no_notice(status: InactivityStatus | None) -> None:
    assert inactivity_notice(status) is None
