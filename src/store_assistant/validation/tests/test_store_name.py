# ABOUTME: Tests for cleaning user-typed store names and normalizing them for lookups.
# ABOUTME: Covers trimming, length limits and case/whitespace-insensitive normalization.
import pytest

from store_assistant.validation.store_name import (
    InvalidStoreNameError,
    clean_store_name,
    is_generic_store_reference,
    normalize_store_name,
    strip_generic_label,
)


def test_clean_store_name_trims_surrounding_whitespace() -> None:
    assert clean_store_name("  Trader Joe's ") == "Trader Joe's"


@pytest.mark.parametrize("raw", ["", "   ", "\t\n"])
def test_clean_store_name_rejects_blank_names(raw: str) -> None:
    with pytest.raises(InvalidStoreNameError) as exc_info:
        clean_store_name(raw)

    assert exc_info.value.problem == "empty"


def test_clean_store_name_accepts_100_characters() -> None:
    name = "a" * 100

    assert clean_store_name(f"  {name}  ") == name


def test_clean_store_name_rejects_101_characters() -> None:
    with pytest.raises(InvalidStoreNameError) as exc_info:
        clean_store_name("a" * 101)

    assert exc_info.value.problem == "too_long"


@pytest.mark.parametrize("raw", ["Trader Joe's", "  trader   JOE'S ", "TRADER\tJOE'S"])
def test_normalize_store_name_ignores_case_and_spacing(raw: str) -> None:
    assert normalize_store_name(raw) == "trader joe's"


@pytest.mark.parametrize(
    "name", ["a store", "The Store", "the shop", "some place", "store", "my store"]
)
def test_generic_references_are_detected(name: str) -> None:
    assert is_generic_store_reference(name) is True


@pytest.mark.parametrize("name", ["Trader Joe's", "The Home Depot", "Costco", "Corner Store Deli"])
def test_real_names_are_not_generic(name: str) -> None:
    assert is_generic_store_reference(name) is False


@pytest.mark.parametrize(
    ("name", "stripped"),
    [
        ("store abc", "abc"),
        ("Store ABC", "ABC"),
        ("abc store", "abc"),
        ("the shop abc", "abc"),
        ("The Container Store", "Container"),
        ("Store 24", "24"),
    ],
)
def test_generic_label_is_stripped(name: str, stripped: str) -> None:
    assert strip_generic_label(name) == stripped


@pytest.mark.parametrize("name", ["Costco", "Trader Joe's", "store", "the store", "a shop"])
def test_names_without_a_removable_label_give_none(name: str) -> None:
    assert strip_generic_label(name) is None
