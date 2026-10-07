"""T030: SC-004. Removing or breaking any one requirement makes `check` name exactly that item.

Runs over every requirement `check` checks, for every language with an evaluation set, on a
temporary copy of that language's two files.
"""

import json
import re

import pytest
import tomli_w

from language_kit.language_files import LanguageData, read_language
from language_kit.registry import REQUIREMENTS
from tests.integration.practice_languages.evaluation_set import evaluated_languages
from tests.unit.language_kit.conftest import make_kit, run_kit

CHECKED = tuple(item for item in REQUIREMENTS if not item.onboarding_only)
BROKEN_VALUES = {
    "code": "ESP",
    "name": "",
    "order": 0,
    "voices": [],
    "voices[].gender": "robot",
    "voices[].speaking_rate": "brisk",
    "default_voice": "xx_XX-nobody-medium",
    "podcast.host_names": {"female": ["Ana"], "male": ["Bo"]},
    "podcast.guest_labels": ["Gast", "gast"],
    "podcast.sample_line": "Hallo ohne Platzhalter.",
    "evaluation.special_letters": "ä1",
    "evaluation.turns": {"order-at-restaurant": ["Hallo."]},
    "evaluation.dictation": ["Nur ein Satz hier."],
    "evaluation.loanwords": ["Hotel"],
}
_INDEX = re.compile(r"\[\d+\]")


def _write(workspace, language: LanguageData) -> None:
    document = language.document
    evaluation = document.pop("evaluation", None)
    (workspace.runtime_dir / f"{language.code}.toml").write_text(
        tomli_w.dumps(document), encoding="utf-8"
    )
    path = workspace.evaluation_dir / f"{language.code}.toml"
    if evaluation is None:
        path.unlink()
    else:
        path.write_text(tomli_w.dumps({"code": language.code} | evaluation), encoding="utf-8")


def _remove(language: LanguageData, path: str) -> LanguageData:
    if "[]" not in path:
        return language.without(path)
    container, field = path.split("[].")
    return language.with_value(container, [_drop(item, field) for item in language.get(container)])


def _break(language: LanguageData, path: str) -> LanguageData:
    if "[]" not in path:
        return language.with_value(path, BROKEN_VALUES[path])
    container, field = path.split("[].")
    items = language.get(container)
    return language.with_value(container, [{**items[0], field: BROKEN_VALUES[path]}, *items[1:]])


def _drop(item: dict, field: str) -> dict:
    return {key: value for key, value in item.items() if key != field}


def _failing_paths(kit, code: str) -> set[str]:
    _, output = run_kit(kit, "check", code, "--json")
    findings = json.loads(output)["findings"]
    return {_INDEX.sub("[]", f["path"]) for f in findings if f["severity"] == "error"}


def _belongs_to(path: str, requirement_path: str) -> bool:
    return path == requirement_path or path.startswith(f"{requirement_path}.")


def test_the_break_table_covers_every_checked_requirement():
    assert set(BROKEN_VALUES) == {item.path for item in CHECKED}


@pytest.mark.parametrize("code", evaluated_languages())
@pytest.mark.parametrize("item", CHECKED, ids=lambda item: item.path)
@pytest.mark.parametrize("change", [_remove, _break], ids=["removed", "broken"])
def test_check_names_exactly_the_seeded_item(workspace, code, item, change):
    kit = make_kit(workspace)
    _write(workspace, change(read_language(code, workspace), item.path))

    failing = _failing_paths(kit, code)

    assert failing, f"{item.path} was not caught"
    assert all(_belongs_to(path, item.path) for path in failing), failing
