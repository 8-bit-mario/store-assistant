# ABOUTME: Tests for US phone number validation and E.164 normalization.
# ABOUTME: Table-driven cases for accepted formats and each rejection reason.
import pytest

from store_assistant.validation.phone import InvalidPhoneError, normalize_us_phone


@pytest.mark.parametrize(
    "raw",
    [
        "(555) 234-5678",
        "555-234-5678",
        "555.234.5678",
        "5552345678",
        "+1 555 234 5678",
        "1-555-234-5678",
        "  555 234 5678  ",
    ],
)
def test_accepted_formats_normalize_to_e164(raw: str) -> None:
    assert normalize_us_phone(raw) == "+15552345678"


@pytest.mark.parametrize(
    ("raw", "problem"),
    [
        ("", "digit_count"),
        ("555-1234", "digit_count"),
        ("25552345678", "digit_count"),
        ("+44 20 7946 0958", "digit_count"),
        ("555-234-56789", "digit_count"),
        ("abc", "characters"),
        ("555-CALL-NOW", "characters"),
        ("555+234+5678", "characters"),
        ("123-456-7890", "area_code"),
        ("055-234-5678", "area_code"),
        ("555-034-5678", "exchange"),
        ("555-134-5678", "exchange"),
    ],
)
def test_invalid_numbers_report_their_problem(raw: str, problem: str) -> None:
    with pytest.raises(InvalidPhoneError) as exc_info:
        normalize_us_phone(raw)

    assert exc_info.value.problem == problem
    assert exc_info.value.reason
