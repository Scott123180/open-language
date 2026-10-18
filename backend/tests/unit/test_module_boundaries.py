"""T125: the podcasts and summary modules are reached only through their package roots.

Principle V (compartmentalisation): code outside `app.podcasts` and `app.conversation_summary`
imports their package root, never a submodule. Two files are exempt: `services/factory.py`, the
composition root, and `database.py`, which imports each package's `models` to register its
tables. The two new modules never import each other, the audio router knows nothing of
podcasts, and the podcast views behind the audio and summary seams are built only in the
factory.
"""

import ast
from pathlib import Path

import pytest

APP_DIR = Path(__file__).resolve().parents[2] / "app"
LANGUAGE_DATA_DIR = APP_DIR / "language_data"
FACTORY = APP_DIR / "services" / "factory.py"
DATABASE = APP_DIR / "database.py"
GUARDED = ("app.podcasts", "app.conversation_summary")
FACTORY_ONLY_CLASSES = ("PodcastMessageVoices", "PodcastSpeakerNames")


def _python_files() -> list[Path]:
    return sorted(APP_DIR.rglob("*.py"))


def _imports(path: Path) -> list[str]:
    tree = ast.parse(path.read_text())
    modules = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules += [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.append(node.module)
    return modules


def _package_of(path: Path) -> str:
    return ".".join(("app", *path.relative_to(APP_DIR).parts[:1]))


def _is_submodule_of(module: str, package: str) -> bool:
    return module.startswith(f"{package}.")


def _allowed_submodule_import(path: Path, module: str) -> bool:
    return path == FACTORY or (path == DATABASE and module.endswith(".models"))


@pytest.mark.parametrize("package", GUARDED)
def test_outside_code_imports_only_the_package_root(package):
    offenders = [
        f"{path.relative_to(APP_DIR)}: {module}"
        for path in _python_files()
        if _package_of(path) != package
        for module in _imports(path)
        if _is_submodule_of(module, package) and not _allowed_submodule_import(path, module)
    ]

    assert offenders == []


@pytest.mark.parametrize(("package", "other"), [GUARDED, tuple(reversed(GUARDED))])
def test_podcasts_and_the_summary_never_import_each_other(package, other):
    package_dir = APP_DIR / package.split(".")[1]
    offenders = [
        f"{path.relative_to(APP_DIR)}: {module}"
        for path in package_dir.rglob("*.py")
        for module in _imports(path)
        if module == other or _is_submodule_of(module, other)
    ]

    assert offenders == []


def test_the_audio_router_knows_nothing_of_podcasts():
    imports = _imports(APP_DIR / "routers" / "audio.py")

    assert [module for module in imports if module.startswith("app.podcasts")] == []


@pytest.mark.parametrize("class_name", FACTORY_ONLY_CLASSES)
def test_the_podcast_views_are_built_only_in_the_factory(class_name):
    builders = [
        path.relative_to(APP_DIR)
        for path in _python_files()
        if f"{class_name}(" in path.read_text()
        and path != FACTORY
        and f"class {class_name}(" not in path.read_text()
    ]

    assert builders == []


def test_the_guard_sees_a_submodule_import():
    assert _is_submodule_of("app.podcasts.services.casting", "app.podcasts")
    assert not _is_submodule_of("app.podcasts", "app.podcasts")
    assert not _is_submodule_of("app.podcasts_extra", "app.podcasts")


def test_language_data_imports_nothing_from_the_app():
    offenders = [
        f"{path.relative_to(APP_DIR)}: {module}"
        for path in LANGUAGE_DATA_DIR.rglob("*.py")
        for module in _imports(path)
        if _is_submodule_of(module, "app") and not module.startswith("app.language_data")
    ]

    assert offenders == []


def test_the_app_never_imports_the_language_kit():
    offenders = [
        f"{path.relative_to(APP_DIR)}: {module}"
        for path in _python_files()
        for module in _imports(path)
        if module == "language_kit" or _is_submodule_of(module, "language_kit")
    ]

    assert offenders == []


# --- 010: the series modules (contracts §10) ----------------------------------------------

FACTORY_ONLY_SERIES_MODULES = (
    "app.podcasts.services.series_storage",
    "app.podcasts.services.sqlite_series_storage",
    "app.podcasts.services.series_memory",
    "app.podcasts.services.episode_endings",
)
PODCAST_ROOT_NAMES = [
    "router",
    "PODCAST_SCENARIO_ID",
    "PodcastMessageVoices",
    "PodcastSpeakerNames",
]


@pytest.mark.parametrize("module", FACTORY_ONLY_SERIES_MODULES)
def test_only_the_factory_imports_the_series_modules_from_outside_podcasts(module):
    importers = [
        path.relative_to(APP_DIR)
        for path in _python_files()
        if _package_of(path) != "app.podcasts" and module in _imports(path) and path != FACTORY
    ]

    assert importers == []


def test_the_episode_turns_never_import_the_memory_keeper():
    imports = _imports(APP_DIR / "podcasts" / "services" / "episode_turns.py")

    assert "app.podcasts.services.series_memory" not in imports


def test_the_podcast_package_root_is_unchanged():
    import app.podcasts

    assert app.podcasts.__all__ == PODCAST_ROOT_NAMES
