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


def copy_repository(target: Path) -> Path:
    """A minimal repository: the two data directories and `.specify/feature.json`."""
    for relative in (RUNTIME_DIR, EVALUATION_DIR):
        shutil.copytree(REPOSITORY / relative, target / relative)
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


ITALIAN_FEMALE = [
    "Giulia",
    "Chiara",
    "Francesca",
    "Sara",
    "Martina",
    "Elena",
    "Alessia",
    "Valentina",
    "Federica",
    "Silvia",
]
ITALIAN_MALE = [
    "Marco",
    "Luca",
    "Matteo",
    "Andrea",
    "Davide",
    "Simone",
    "Lorenzo",
    "Paolo",
    "Stefano",
    "Giorgio",
]
ITALIAN_VOICES = ("it_IT-paola-medium", "it_IT-riccardo-x_low")


def italian_pack_document() -> dict:
    """A complete, valid Italian pack as a document (what an agent writes, minus the comments)."""
    return {
        "code": "it",
        "name": "Italian",
        "default_voice": "it_IT-paola-medium",
        "voices": [
            {"key": "it_IT-paola-medium", "gender": "female"},
            {"key": "it_IT-riccardo-x_low", "gender": "male", "speaking_rate": "natural"},
        ],
        "podcast": {
            "guest_labels": ["Ospite", "Ascoltatore", "Ascoltatrice"],
            "sample_line": "Ciao, sono {name}. Benvenuti al programma!",
            "host_names": {"female": ITALIAN_FEMALE, "male": ITALIAN_MALE},
        },
        "evaluation": {
            "special_letters": "àèéìòù",
            "loanwords": ["hotel", "taxi"],
            "dictation": [f"Frase numero {n} è qui." for n in range(20)],
            "turns": {scenario: [f"Turno {n}." for n in range(5)] for scenario in SCENARIO_IDS},
        },
    }


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
