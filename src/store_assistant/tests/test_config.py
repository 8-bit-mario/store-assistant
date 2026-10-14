# ABOUTME: Tests for loading and validating application settings from an environment mapping.
# ABOUTME: Covers required variables, optional defaults, and secret-safe error messages.
from datetime import timedelta
from pathlib import Path

import pytest

from store_assistant.config import MissingSettingError, SettingError, load_settings

SECRET = "sentinel-secret-value-123"


def _complete_environ() -> dict[str, str]:
    return {
        "OPENAI_API_KEY": SECRET,
        "OPENAI_MODEL": "gpt-test-model",
        "STORE_LOOKUP_PASSPHRASE": SECRET,
        "LANGSMITH_API_KEY": SECRET,
        "LANGSMITH_TRACING": "true",
        "LANGSMITH_PROJECT": "store-assistant",
    }


def test_load_settings_reads_required_values() -> None:
    settings = load_settings(_complete_environ())

    assert settings.openai_model == "gpt-test-model"
    assert settings.store_lookup_passphrase == SECRET


def test_load_settings_applies_optional_defaults() -> None:
    settings = load_settings(_complete_environ())

    assert settings.data_dir == Path("data")
    assert settings.check_in_after == timedelta(seconds=60)
    assert settings.expire_after == timedelta(seconds=90)


def test_load_settings_reads_optional_overrides() -> None:
    environ = _complete_environ() | {
        "STORE_ASSISTANT_DATA_DIR": "/tmp/somewhere",
        "STORE_ASSISTANT_CHECK_IN_SECONDS": "1",
        "STORE_ASSISTANT_EXPIRE_SECONDS": "2",
    }

    settings = load_settings(environ)

    assert settings.data_dir == Path("/tmp/somewhere")
    assert settings.check_in_after == timedelta(seconds=1)
    assert settings.expire_after == timedelta(seconds=2)


def test_missing_variable_is_named() -> None:
    environ = _complete_environ()
    del environ["OPENAI_MODEL"]

    with pytest.raises(MissingSettingError, match="OPENAI_MODEL"):
        load_settings(environ)


def test_all_missing_variables_are_named() -> None:
    environ = _complete_environ()
    del environ["OPENAI_MODEL"]
    del environ["LANGSMITH_PROJECT"]

    with pytest.raises(MissingSettingError) as exc_info:
        load_settings(environ)

    assert exc_info.value.names == ["OPENAI_MODEL", "LANGSMITH_PROJECT"]
    assert "OPENAI_MODEL" in str(exc_info.value)
    assert "LANGSMITH_PROJECT" in str(exc_info.value)


def test_empty_value_counts_as_missing() -> None:
    environ = _complete_environ() | {"STORE_LOOKUP_PASSPHRASE": "   "}

    with pytest.raises(MissingSettingError, match="STORE_LOOKUP_PASSPHRASE"):
        load_settings(environ)


def test_missing_setting_error_never_contains_values() -> None:
    environ = _complete_environ()
    del environ["OPENAI_MODEL"]

    with pytest.raises(MissingSettingError) as exc_info:
        load_settings(environ)

    assert SECRET not in str(exc_info.value)


def test_settings_repr_hides_passphrase() -> None:
    settings = load_settings(_complete_environ())

    assert SECRET not in repr(settings)


@pytest.mark.parametrize(
    ("check_in", "expire"),
    [("abc", "90"), ("60", "1.5"), ("0", "90"), ("-5", "90"), ("60", "60"), ("90", "60")],
)
def test_invalid_inactivity_thresholds_are_rejected(check_in: str, expire: str) -> None:
    environ = _complete_environ() | {
        "STORE_ASSISTANT_CHECK_IN_SECONDS": check_in,
        "STORE_ASSISTANT_EXPIRE_SECONDS": expire,
    }

    with pytest.raises(SettingError):
        load_settings(environ)
