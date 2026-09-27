"""T066: the German evaluation set has the shape the benchmarks rely on. Runs in CI."""

import re

from app.services.scenario.static import StaticScenarioProvider
from tests.integration.practice_languages.german_evaluation_set import (
    DICTATION_SENTENCES,
    GERMAN_TURNS,
    LOANWORD_ALLOWLIST,
)

SPECIAL_LETTERS = re.compile("[äöüßÄÖÜ]")


def test_ten_scenarios_of_five_turns():
    assert len(GERMAN_TURNS) == 10
    assert all(len(turns) == 5 for turns in GERMAN_TURNS.values())


def test_every_scenario_is_a_real_scenario():
    known = {scenario.id for scenario in StaticScenarioProvider().get_all()}

    assert set(GERMAN_TURNS) <= known


def test_twenty_dictation_sentences():
    assert len(DICTATION_SENTENCES) == 20


def test_every_dictation_sentence_has_an_umlaut_or_eszett():
    assert all(SPECIAL_LETTERS.search(sentence) for sentence in DICTATION_SENTENCES)


def test_the_loanword_allowlist_is_short_and_lowercase():
    assert {"hotel", "taxi", "ticket", "ok"} == LOANWORD_ALLOWLIST
