# ABOUTME: Guard test keeping the lookup passphrase confined to config and the turn handler.
# ABOUTME: Fails if any other module reads the passphrase setting or its environment variable.
import ast
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
ALLOWED_FILES = {
    PACKAGE_ROOT / "config.py",
    PACKAGE_ROOT / "conversation" / "turns.py",
}
PASSPHRASE_ATTRIBUTE = "store_lookup_passphrase"
PASSPHRASE_ENV_VAR = "STORE_LOOKUP_PASSPHRASE"


def _is_test_code(path: Path) -> bool:
    return "tests" in path.relative_to(PACKAGE_ROOT).parts or path.name == "conftest.py"


def _names_passphrase(node: ast.Attribute | ast.Constant) -> bool:
    if isinstance(node, ast.Attribute):
        return node.attr == PASSPHRASE_ATTRIBUTE
    return node.value == PASSPHRASE_ENV_VAR


def find_passphrase_references(root: Path) -> list[str]:
    """List `file:line` locations outside the allowed files that touch the passphrase."""
    offenders = []
    for path in sorted(root.rglob("*.py")):
        if path in ALLOWED_FILES or _is_test_code(path):
            continue
        for node in ast.walk(ast.parse(path.read_text(), filename=str(path))):
            if isinstance(node, ast.Attribute | ast.Constant) and _names_passphrase(node):
                offenders.append(f"{path.relative_to(root)}:{node.lineno}")
    return offenders


def test_passphrase_is_only_read_by_config_and_turn_handler() -> None:
    offenders = find_passphrase_references(PACKAGE_ROOT)

    assert offenders == [], f"Passphrase referenced outside allowed modules: {offenders}"
