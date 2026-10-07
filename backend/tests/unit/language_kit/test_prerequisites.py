"""T056: `prereq` checks a code can be onboarded, in order, stopping at the first failure (R7)."""

import pytest

from language_kit.cli import EXIT_OK, EXIT_USAGE
from tests.unit.language_kit.conftest import (
    fake_context,
    italian_catalogue,
    make_kit,
    run_kit,
    snapshot,
)
from tests.unit.language_kit.fakes import FakeVoiceCatalogue, candidate


@pytest.fixture
def kit(workspace):
    return make_kit(workspace, voice_catalogue=italian_catalogue())


def test_a_language_that_can_be_onboarded_lists_its_voices(kit):
    code, output = run_kit(kit, "prereq", "it")

    lines = output.splitlines()
    assert code == EXIT_OK
    assert lines[0] == "prereq it: Italian can be onboarded (6/6 checks, 0 warnings)"
    assert lines[1].split() == ["voice", "it_IT-paola-medium", "Italy", "medium", "60", "MB"]
    assert lines[-1] == "→ next: kit.sh scaffold it --name Italian"


@pytest.mark.parametrize(
    ("code", "reason"),
    [
        ("ITA", "ISO 639-1"),
        ("de", "already catalogued"),
        ("en", "explanations"),
        ("ar", "right to left"),
        ("zh", "spaces"),
        ("xx", "Whisper"),
    ],
)
def test_the_first_failing_check_stops_with_its_reason(kit, code, reason):
    exit_code, output = run_kit(kit, "prereq", code)

    assert exit_code == EXIT_USAGE
    assert reason in output
    assert sum(line.startswith("FAIL") for line in output.splitlines()) == 1


def test_a_catalogued_language_points_to_check_and_backfill(kit):
    _, output = run_kit(kit, "prereq", "de")

    assert "kit.sh check de" in output and "kit.sh backfill de" in output


def test_a_language_without_a_single_speaker_voice_cannot_be_onboarded(workspace):
    kit = make_kit(workspace, voice_catalogue=FakeVoiceCatalogue([]), context=fake_context())

    code, output = run_kit(kit, "prereq", "fr")

    assert code == EXIT_USAGE
    assert "single-speaker" in output


def test_a_wordfreq_gap_is_a_warning_that_does_not_stop(workspace):
    context = fake_context(wordfreq_codes=frozenset({"en"}))
    kit = make_kit(workspace, voice_catalogue=italian_catalogue(), context=context)

    code, output = run_kit(kit, "prereq", "it")

    assert code == EXIT_OK
    assert "(6/6 checks, 1 warning)" in output
    assert any(
        line.startswith("WARN it wordfreq") and "not run" in line for line in output.splitlines()
    )


def test_a_single_voice_warns_that_podcasts_get_one_gender(workspace):
    kit = make_kit(workspace, voice_catalogue=FakeVoiceCatalogue([candidate("fr_FR-anne-medium")]))

    _, output = run_kit(kit, "prereq", "fr")

    assert any(
        line.startswith("WARN fr voices") and "one gender" in line for line in output.splitlines()
    )


def test_prereq_writes_nothing(kit):
    before = snapshot(kit.workspace.root)

    run_kit(kit, "prereq", "it")

    assert snapshot(kit.workspace.root) == before


def test_prereq_needs_the_voice_catalogue(workspace):
    from language_kit.cli import EXIT_EXTERNAL

    assert run_kit(make_kit(workspace), "prereq", "it")[0] == EXIT_EXTERNAL
