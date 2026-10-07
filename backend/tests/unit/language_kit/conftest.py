"""Shared fixtures for the language kit: a temporary repository holding copies of the real data."""

import json
import shutil
from pathlib import Path

import pytest

from language_kit.context import RuleContext
from language_kit.workspace import EVALUATION_DIR, RUNTIME_DIR, Workspace

REPOSITORY = Path(__file__).resolve().parents[4]
SCENARIO_IDS = (
    "buy-train-ticket",
    "check-into-hotel",
    "order-at-restaurant",
    "call-doctors-office",
    "ask-for-directions",
    "job-interview",
    "rent-a-car",
    "visit-pharmacy",
    "report-lost-item",
    "board-airplane",
)


FIXTURE_LANGUAGES = ("es", "de")
"""The languages a temporary repository holds: fixed, so a language added later by data alone
never changes what these tests see (FR-019)."""


def copy_repository(target: Path, codes: tuple[str, ...] = FIXTURE_LANGUAGES) -> Path:
    """A minimal repository: the given languages' data files and `.specify/feature.json`."""
    for relative in (RUNTIME_DIR, EVALUATION_DIR):
        (target / relative).mkdir(parents=True)
        for code in codes:
            source = REPOSITORY / relative / f"{code}.toml"
            if source.is_file():
                shutil.copy2(source, target / relative / source.name)
    (target / "backend" / "pyproject.toml").write_text("", encoding="utf-8")
    specify = target / ".specify"
    specify.mkdir()
    feature = {"feature_directory": "specs/008-language-onboarding-kit"}
    (specify / "feature.json").write_text(json.dumps(feature), encoding="utf-8")
    return target


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    return copy_repository(tmp_path / "repo")


@pytest.fixture
def workspace(repo: Path, tmp_path: Path) -> Workspace:
    voice_dir = tmp_path / "voices"
    voice_dir.mkdir()
    return Workspace.discover(repo, environ={"OPEN_LANGUAGE_VOICE_DIR": str(voice_dir)})


def remove_evaluation(workspace: Workspace, code: str) -> None:
    """Make a language incomplete again: as Spanish was before its backfill."""
    (workspace.evaluation_dir / f"{code}.toml").unlink(missing_ok=True)


def fake_context(**overrides) -> RuleContext:
    facts = {
        "scenario_ids": SCENARIO_IDS,
        "catalogued_codes": frozenset({"es", "de"}),
        "explanation_codes": frozenset({"en"}),
        "whisper_codes": frozenset({"en", "es", "de", "it", "fr", "ar", "zh"}),
        "wordfreq_codes": frozenset({"en", "es", "de", "it", "fr"}),
    }
    return RuleContext(**(facts | overrides))


@pytest.fixture
def context() -> RuleContext:
    return fake_context()


def write_valid_evaluation(workspace: Workspace, code: str) -> None:
    """A minimal evaluation file that passes every rule (no special letters, so any sentence)."""
    import tomli_w

    document = {
        "code": code,
        "special_letters": "",
        "loanwords": ["ok"],
        "dictation": [f"Sentence number {n} here." for n in range(20)],
        "turns": {scenario: [f"Turn {n}." for n in range(5)] for scenario in SCENARIO_IDS},
    }
    path = workspace.evaluation_dir / f"{code}.toml"
    path.write_text(tomli_w.dumps(document), encoding="utf-8")


def make_kit(workspace: Workspace, **overrides):
    from io import StringIO

    from language_kit.composition import Kit
    from tests.unit.language_kit.fakes import FixedClock

    parts = {
        "workspace": workspace,
        "context": fake_context(),
        "clock": FixedClock(),
        "out": StringIO(),
    }
    return Kit(**(parts | overrides))


def run_kit(kit, *argv: str) -> tuple[int, str]:
    from language_kit.cli import main

    before = kit.out.tell()
    code = main(list(argv), kit_factory=lambda: kit)
    return code, kit.out.getvalue()[before:]


@pytest.fixture
def kit(workspace: Workspace):
    return make_kit(workspace)


def snapshot(*directories: Path) -> dict[str, bytes]:
    return {
        str(path): path.read_bytes()
        for directory in directories
        if directory.exists()
        for path in sorted(directory.rglob("*"))
        if path.is_file()
    }


ITALIAN_VOICES = ("it_IT-paola-medium", "it_IT-riccardo-x_low")
DERIVED_PACK_PATHS = ("order",)
DERIVED_VOICE_FIELDS = ("display_name", "locale", "quality")


def italian_pack_document() -> dict:
    """Italian as a complete pack: the committed Italian data minus what `apply` derives.

    Built from the data rather than written out, so a requirement backfilled into every language
    reaches these tests with no edit to them.
    """
    from language_kit.language_files import read_language

    document = read_language("it", Workspace(root=REPOSITORY, voice_dir=REPOSITORY)).document
    for path in DERIVED_PACK_PATHS:
        document.pop(path)
    document["voices"] = [
        {key: value for key, value in voice.items() if key not in DERIVED_VOICE_FIELDS}
        for voice in document["voices"]
    ]
    return document


def italian_pack_text(**changes) -> str:
    import tomli_w

    return tomli_w.dumps(italian_pack_document() | changes)


def italian_catalogue():
    from tests.unit.language_kit.fakes import FakeVoiceCatalogue, candidate

    keys = (*ITALIAN_VOICES, "it_IT-serena-medium", "de_DE-thorsten-medium", "de_DE-kerstin-low")
    keys += ("es_ES-davefx-medium", "es_AR-daniela-high")
    return FakeVoiceCatalogue([candidate(key) for key in keys])


def install_voices(workspace: Workspace, *keys: str) -> None:
    for key in keys:
        (workspace.voice_dir / f"{key}.onnx").write_bytes(b"onnx")
        (workspace.voice_dir / f"{key}.onnx.json").write_bytes(b"{}")


CATALOGUED_VOICES = (
    "es_ES-davefx-medium",
    "es_AR-daniela-high",
    "de_DE-thorsten-medium",
    "de_DE-kerstin-low",
)
