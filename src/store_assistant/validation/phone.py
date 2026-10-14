# ABOUTME: Validates US (NANP) phone numbers typed in common formats.
# ABOUTME: Normalizes valid numbers to E.164 (+1NPANXXXXXX) and explains invalid ones.
import re
from typing import Literal

PhoneProblem = Literal["characters", "digit_count", "area_code", "exchange"]

ALLOWED_PHONE_PATTERN = re.compile(r"\+?[\d\s().-]*")

PROBLEM_REASONS: dict[PhoneProblem, str] = {
    "characters": "it can only contain digits, spaces, dashes, dots, parentheses and a leading +",
    "digit_count": "a US number needs 10 digits, optionally preceded by 1",
    "area_code": "the area code can't start with 0 or 1",
    "exchange": "the 3 digits after the area code can't start with 0 or 1",
}


class InvalidPhoneError(ValueError):
    """Raised when text is not a valid US phone number."""

    def __init__(self, problem: PhoneProblem) -> None:
        self.problem = problem
        self.reason = PROBLEM_REASONS[problem]
        super().__init__(f"Invalid phone number: {self.reason}")


def normalize_us_phone(raw: str) -> str:
    """
    Validate a US phone number and return it in E.164 form.

    Args:
        raw: The number as the user typed it.

    Returns:
        The number as "+1" followed by 10 digits.

    Raises:
        InvalidPhoneError: If the text is not a valid US number.

    Example:
        >>> normalize_us_phone("(555) 234-5678")
        '+15552345678'
    """
    text = raw.strip()
    if not ALLOWED_PHONE_PATTERN.fullmatch(text):
        raise InvalidPhoneError("characters")

    digits = re.sub(r"\D", "", text)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        raise InvalidPhoneError("digit_count")
    if digits[0] in "01":
        raise InvalidPhoneError("area_code")
    if digits[3] in "01":
        raise InvalidPhoneError("exchange")
    return f"+1{digits}"
