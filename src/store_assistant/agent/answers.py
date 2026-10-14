# ABOUTME: Interprets short free-text replies to confirmation prompts.
# ABOUTME: Deterministic word matching, so confirmations never depend on the LLM.
YES_WORDS = frozenset({"yes", "y", "yeah", "yep", "sure", "ok", "okay", "replace"})
NO_WORDS = frozenset({"no", "n", "nope", "keep"})


def parse_yes_no(text: str) -> bool | None:
    """
    Read a reply as yes, no, or unclear.

    Returns:
        True for yes, False for no, None when the reply is unclear or mixed.

    Example:
        >>> parse_yes_no("yes please")
        True
    """
    words = set(text.lower().replace(",", " ").replace(".", " ").replace("!", " ").split())
    has_yes, has_no = bool(words & YES_WORDS), bool(words & NO_WORDS)
    if has_yes == has_no:
        return None
    return has_yes
