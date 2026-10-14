# ABOUTME: Tests that .env.example lists exactly the variables the app reads, with usable values.
# ABOUTME: Keeps the template a new user copies to .env in step with config.py.
from pathlib import Path

from dotenv import dotenv_values

from store_assistant.config import REQUIRED_VARIABLES, load_settings

ENV_EXAMPLE = Path(__file__).resolve().parents[3] / ".env.example"
OPTIONAL_VARIABLES = (
    "STORE_ASSISTANT_DATA_DIR",
    "STORE_ASSISTANT_CHECK_IN_SECONDS",
    "STORE_ASSISTANT_EXPIRE_SECONDS",
)


def _example() -> dict[str, str]:
    return {name: value or "" for name, value in dotenv_values(ENV_EXAMPLE).items()}


def test_example_lists_every_variable_the_app_reads() -> None:
    assert set(_example()) == {*REQUIRED_VARIABLES, *OPTIONAL_VARIABLES}


def test_example_loads_once_the_blank_secrets_are_filled_in() -> None:
    environ = {name: value or "filled-in" for name, value in _example().items()}

    settings = load_settings(environ)

    assert settings.openai_model == "gpt-5.4-mini"
