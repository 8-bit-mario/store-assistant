# ABOUTME: Compares a passphrase attempt with the configured secret in constant time.
# ABOUTME: Used only by the turn handler so the secret never enters the agent graph.
import hmac


def is_correct_passphrase(attempt: str, expected: str) -> bool:
    """
    Check a passphrase attempt without leaking timing information.

    Args:
        attempt: What the user typed; surrounding whitespace is ignored.
        expected: The configured passphrase.

    Returns:
        True if the attempt matches exactly (case-sensitive).

    Raises:
        ValueError: If the configured passphrase is blank.
    """
    if not expected.strip():
        raise ValueError("The configured lookup passphrase is blank")
    return hmac.compare_digest(attempt.strip().encode(), expected.strip().encode())
