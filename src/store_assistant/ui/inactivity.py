# ABOUTME: Chooses the inactivity notice shown while an operation waits for the user.
# ABOUTME: The check-in notice is display-only and never enters the conversation state.
from store_assistant.conversation.cancellation import InactivityStatus

CHECK_IN_NOTICE = "Are you still there? I'll cancel this soon if there's no reply."


def inactivity_notice(status: InactivityStatus | None) -> str | None:
    """The notice for a status, or None when nothing should be shown."""
    return CHECK_IN_NOTICE if status == "check_in" else None
