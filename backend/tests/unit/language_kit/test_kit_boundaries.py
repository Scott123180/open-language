"""The kit reaches the app only through package roots (research R3, Principle V)."""

import ast
from pathlib import Path

KIT_DIR = Path(__file__).resolve().parents[3] / "language_kit"
ALLOWED_APP_MODULES = {"app.language_data", "app.practice_languages", "app.services.factory"}


def _app_imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    modules = [
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    ]
    modules += [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module]
    return [module for module in modules if module == "app" or module.startswith("app.")]


def test_the_kit_imports_only_app_package_roots():
    offenders = [
        f"{path.name}: {module}"
        for path in sorted(KIT_DIR.rglob("*.py"))
        for module in _app_imports(path)
        if module not in ALLOWED_APP_MODULES
    ]

    assert offenders == []
