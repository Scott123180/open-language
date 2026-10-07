"""T016: every evaluation set has the shape the benchmarks rely on (contracts/data-files.md). Runs in CI.

Replaces 006's `test_german_evaluation_set.py`: its assertions now read `evaluation/de.toml`.
"""

import re
from pathlib import Path

import pytest

from app.practice_languages import PRACTICE_LANGUAGES
from app.services.scenario.static import StaticScenarioProvider
from tests.integration.practice_languages.evaluation_set import (
    EVALUATION_DIR,
    EvaluationSetError,
    evaluated_languages,
    evaluation_set,
)

GERMAN_SPECIAL_LETTERS = re.compile("[äöüßÄÖÜ]")
MINIMAL = """\
code = "aa"
special_letters = ""
loanwords = []
dictation = ["One two three."]

[turns]
order-at-restaurant = ["Hello."]
"""


def test_ten_scenarios_of_five_turns():
    turns = evaluation_set("de").turns

    assert len(turns) == 10
    assert all(len(scenario_turns) == 5 for scenario_turns in turns.values())


def test_every_scenario_is_a_real_scenario():
    known = {scenario.id for scenario in StaticScenarioProvider().get_all()}

    assert set(evaluation_set("de").turns) <= known


def test_twenty_dictation_sentences():
    assert len(evaluation_set("de").dictation) == 20


def test_every_dictation_sentence_has_an_umlaut_or_eszett():
    assert all(GERMAN_SPECIAL_LETTERS.search(s) for s in evaluation_set("de").dictation)


def test_the_loanword_allowlist_is_short_and_lowercase():
    assert {"hotel", "taxi", "ticket", "ok"} == evaluation_set("de").loanwords


def test_german_special_letters_are_the_umlauts_and_eszett():
    assert evaluation_set("de").special_letters == "äöüß"


def test_evaluated_languages_are_those_with_a_file_in_catalogue_order():
    with_file = {path.stem for path in EVALUATION_DIR.glob("*.toml")}

    assert evaluated_languages() == tuple(code for code in PRACTICE_LANGUAGES if code in with_file)


def test_a_missing_evaluation_file_names_it():
    with pytest.raises(EvaluationSetError, match="xx.toml"):
        evaluation_set("xx")


def test_a_file_loads_from_another_directory(tmp_path: Path):
    (tmp_path / "aa.toml").write_text(MINIMAL, encoding="utf-8")

    loaded = evaluation_set("aa", tmp_path)

    assert loaded.turns["order-at-restaurant"] == ("Hello.",)
    assert loaded.loanwords == frozenset()


def test_an_unknown_key_is_refused(tmp_path: Path):
    (tmp_path / "aa.toml").write_text(MINIMAL + 'notes = "x"\n', encoding="utf-8")

    with pytest.raises(EvaluationSetError, match="notes"):
        evaluation_set("aa", tmp_path)


def test_a_missing_key_is_refused(tmp_path: Path):
    (tmp_path / "aa.toml").write_text(MINIMAL.replace("loanwords = []\n", ""), encoding="utf-8")

    with pytest.raises(EvaluationSetError, match="loanwords"):
        evaluation_set("aa", tmp_path)


def test_a_wrong_type_is_refused(tmp_path: Path):
    (tmp_path / "aa.toml").write_text(MINIMAL.replace('["Hello."]', "[1]"), encoding="utf-8")

    with pytest.raises(EvaluationSetError, match="turns"):
        evaluation_set("aa", tmp_path)
