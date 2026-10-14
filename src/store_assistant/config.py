# ABOUTME: Loads application settings from the environment and fails fast when any are missing.
# ABOUTME: Error messages name variables only, never their values.
import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

REQUIRED_VARIABLES = (
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "STORE_LOOKUP_PASSPHRASE",
    "LANGSMITH_API_KEY",
    "LANGSMITH_TRACING",
    "LANGSMITH_PROJECT",
)
DEFAULT_DATA_DIR = "data"
DEFAULT_CHECK_IN_SECONDS = 60
DEFAULT_EXPIRE_SECONDS = 90


class SettingError(Exception):
    """Raised when the environment does not describe a usable configuration."""


class MissingSettingError(SettingError):
    """Raised when required environment variables are absent or empty."""

    def __init__(self, names: list[str]) -> None:
        self.names = names
        super().__init__(f"Missing required environment variables: {', '.join(names)}")


@dataclass(frozen=True)
class Settings:
    """Application settings; API keys stay in the environment for the client libraries."""

    openai_model: str
    store_lookup_passphrase: str = field(repr=False)
    data_dir: Path = Path(DEFAULT_DATA_DIR)
    check_in_after: timedelta = timedelta(seconds=DEFAULT_CHECK_IN_SECONDS)
    expire_after: timedelta = timedelta(seconds=DEFAULT_EXPIRE_SECONDS)


def _read_seconds(environ: Mapping[str, str], name: str, default: int) -> timedelta:
    raw = environ.get(name, "").strip()
    if not raw:
        return timedelta(seconds=default)
    if not raw.isdigit() or int(raw) <= 0:
        raise SettingError(f"{name} must be a positive whole number of seconds")
    return timedelta(seconds=int(raw))


def load_settings(environ: Mapping[str, str]) -> Settings:
    """
    Build settings from an environment mapping.

    Args:
        environ: Environment variables, typically `os.environ`.

    Returns:
        Validated settings.

    Raises:
        MissingSettingError: If any required variable is absent or blank.
        SettingError: If the inactivity thresholds are invalid.
    """
    missing = [name for name in REQUIRED_VARIABLES if not environ.get(name, "").strip()]
    if missing:
        raise MissingSettingError(missing)

    check_in_after = _read_seconds(
        environ, "STORE_ASSISTANT_CHECK_IN_SECONDS", DEFAULT_CHECK_IN_SECONDS
    )
    expire_after = _read_seconds(environ, "STORE_ASSISTANT_EXPIRE_SECONDS", DEFAULT_EXPIRE_SECONDS)
    if expire_after <= check_in_after:
        raise SettingError(
            "STORE_ASSISTANT_EXPIRE_SECONDS must be greater than STORE_ASSISTANT_CHECK_IN_SECONDS"
        )

    return Settings(
        openai_model=environ["OPENAI_MODEL"].strip(),
        store_lookup_passphrase=environ["STORE_LOOKUP_PASSPHRASE"],
        data_dir=Path(environ.get("STORE_ASSISTANT_DATA_DIR", "").strip() or DEFAULT_DATA_DIR),
        check_in_after=check_in_after,
        expire_after=expire_after,
    )


def get_settings() -> Settings:
    """Load `.env` into the process environment, then build settings from it."""
    load_dotenv()
    return load_settings(os.environ)
