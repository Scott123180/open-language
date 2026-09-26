"""T035: the benchmark's evaluation set has the shape research R9 promises."""

from app.services.scenario.static import StaticScenarioProvider
from tests.integration.conversation_levels.evaluation_set import (
    EVALUATION_SET,
    FR_012,
    FR_013,
    FR_014,
    REVIEW_QUESTIONS,
)

DOCTOR_OR_BANK = {"call-doctors-office", "open-bank-account"}


def _all_turns():
    return [turn for conversation in EVALUATION_SET for turn in conversation.turns]


def test_is_four_built_in_scenarios_of_five_turns():
    built_in = {scenario.id for scenario in StaticScenarioProvider().get_all()}

    assert len(EVALUATION_SET) == 4
    assert all(conversation.scenario_id in built_in for conversation in EVALUATION_SET)
    assert all(len(conversation.turns) == 5 for conversation in EVALUATION_SET)


def test_probes_each_behaviour_requirement():
    probed = {turn.probes for turn in _all_turns()}

    assert {FR_012, FR_013, FR_014} <= probed


def test_the_specialist_words_probe_is_in_a_doctor_or_bank_scenario():
    scenarios = {c.scenario_id for c in EVALUATION_SET if any(t.probes == FR_012 for t in c.turns)}

    assert scenarios and scenarios <= DOCTOR_OR_BANK


def test_every_tag_has_a_review_question():
    assert {turn.probes for turn in _all_turns()} - {None} <= set(REVIEW_QUESTIONS)
