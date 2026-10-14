# ABOUTME: Fixtures for driving the Streamlit app headlessly with AppTest.
# ABOUTME: Points the app at the test's tmp_path and test passphrase, and releases cached resources.
from collections.abc import Iterator
from pathlib import Path

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

from store_assistant.tests.support import TEST_PASSPHRASE
from store_assistant.ui.tests.page import open_page


@pytest.fixture
def app_environment(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[None]:
    """Point the app at this test's data directory and passphrase; release it afterwards."""
    monkeypatch.setenv("STORE_ASSISTANT_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("STORE_LOOKUP_PASSPHRASE", TEST_PASSPHRASE)
    yield
    st.cache_resource.clear()


@pytest.fixture
def app(app_environment: None) -> AppTest:
    """The Streamlit page after its first run."""
    return open_page()
