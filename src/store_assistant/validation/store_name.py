# ABOUTME: Cleans user-typed store names and derives the normalized key used for lookups.
# ABOUTME: Names that differ only by case or spacing share one normalized key.
from typing import Literal

MAX_STORE_NAME_LENGTH = 100
GENERIC_STORE_WORDS = frozenset(
    {"a", "an", "the", "some", "this", "that", "my", "store", "shop", "place", "business"}
)

LEADING_LABEL_WORDS = frozenset({"the", "a", "an", "store", "shop"})
TRAILING_LABEL_WORDS = frozenset({"store", "shop"})

StoreNameProblem = Literal["empty", "too_long"]

PROBLEM_REASONS: dict[StoreNameProblem, str] = {
    "empty": "the store name can't be empty",
    "too_long": f"the store name can be at most {MAX_STORE_NAME_LENGTH} characters",
}


class InvalidStoreNameError(ValueError):
    """Raised when a store name is blank or too long."""

    def __init__(self, problem: StoreNameProblem) -> None:
        self.problem = problem
        self.reason = PROBLEM_REASONS[problem]
        super().__init__(f"Invalid store name: {self.reason}")


def clean_store_name(raw: str) -> str:
    """
    Trim a store name and check it is usable.

    Args:
        raw: The name as the user typed it.

    Returns:
        The trimmed name, keeping the user's capitalization.

    Raises:
        InvalidStoreNameError: If the name is blank or longer than 100 characters.
    """
    name = raw.strip()
    if not name:
        raise InvalidStoreNameError("empty")
    if len(name) > MAX_STORE_NAME_LENGTH:
        raise InvalidStoreNameError("too_long")
    return name


def normalize_store_name(name: str) -> str:
    """
    Build the lookup key for a store name.

    Example:
        >>> normalize_store_name("  Trader   JOE'S ")
        "trader joe's"
    """
    return " ".join(name.split()).lower()


def is_generic_store_reference(name: str) -> bool:
    """
    Detect phrases like "a store" or "the shop" that refer to a store without naming it.

    Example:
        >>> is_generic_store_reference("the store")
        True
    """
    return set(normalize_store_name(name).split()) <= GENERIC_STORE_WORDS


def strip_generic_label(name: str) -> str | None:
    """
    Remove generic words around a name, as in "store abc" or "abc store".

    Returns:
        The name without the label, or None when there is no label or nothing else is left.

    Example:
        >>> strip_generic_label("store ABC")
        'ABC'
    """
    words = name.split()
    while words and words[0].lower() in LEADING_LABEL_WORDS:
        words = words[1:]
    while words and words[-1].lower() in TRAILING_LABEL_WORDS:
        words = words[:-1]
    stripped = " ".join(words)
    return stripped if stripped and stripped != " ".join(name.split()) else None
