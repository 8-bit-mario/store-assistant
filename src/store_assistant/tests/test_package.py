# ABOUTME: Smoke tests for the store_assistant package: it imports, and its wheel holds no tests.
# ABOUTME: Guards the src layout and packaging configuration.
import importlib
import subprocess
import zipfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_package_imports() -> None:
    """The installed package resolves to the src layout."""
    package = importlib.import_module("store_assistant")

    assert package.__file__ is not None
    assert package.__file__.endswith("src/store_assistant/__init__.py")


def test_wheel_ships_the_app_without_tests(tmp_path: Path) -> None:
    subprocess.run(
        ["uv", "build", "--wheel", "--offline", "--quiet", "--out-dir", str(tmp_path)],
        cwd=REPO_ROOT,
        check=True,
    )
    [wheel] = tmp_path.glob("*.whl")
    names = zipfile.ZipFile(wheel).namelist()

    assert "store_assistant/agent/graph.py" in names
    assert [name for name in names if "/tests/" in name or name.endswith("conftest.py")] == []
