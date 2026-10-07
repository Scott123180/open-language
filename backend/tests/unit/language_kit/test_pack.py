"""T039: a language pack: parsing, structure errors, partial packs and merging (contracts/pack-format.md)."""

import pytest

from language_kit.language_files import LanguageData, read_language
from language_kit.pack import LanguagePack
from language_kit.registry import REQUIREMENTS
from tests.unit.language_kit.conftest import fake_context, italian_pack_document, italian_pack_text

CONTEXT = fake_context()


def _parse(text: str, code: str = "it") -> LanguagePack:
    return LanguagePack.parse(text, code)


def _problem_texts(pack: LanguagePack) -> list[str]:
    return [finding.text() for finding in pack.problems]


def test_a_complete_pack_parses_without_problems():
    pack = _parse(italian_pack_text())

    assert pack.problems == ()
    assert pack.data.get("podcast.sample_line") == "Ciao, sono {name}. Benvenuti al programma!"


def test_an_omitted_speaking_rate_defaults_to_natural():
    pack = _parse(italian_pack_text())

    assert pack.data.get("voices[].speaking_rate") == ["natural", "natural"]


def test_a_toml_syntax_error_is_one_finding_with_its_line():
    pack = _parse('code = "it"\nname = \n')

    (text,) = _problem_texts(pack)
    assert text.startswith("FAIL it pack: line 2: ")


def test_an_unknown_key_is_named():
    podcast = italian_pack_document()["podcast"] | {"guest_label": ["Ospite"]}

    (text,) = _problem_texts(_parse(italian_pack_text(podcast=podcast)))

    assert "guest_label" in text


@pytest.mark.parametrize(
    "change",
    [
        {"order": 3},
        {"voices": [{"key": "it_IT-paola-medium", "gender": "female", "locale": "it_IT"}]},
        {"voices": [{"key": "it_IT-paola-medium", "gender": "female", "quality": "medium"}]},
    ],
    ids=["order", "locale", "quality"],
)
def test_a_derived_key_is_refused(change):
    (text,) = _problem_texts(_parse(italian_pack_text(**change)))

    assert "derived by the kit; remove it" in text


def test_a_voice_may_override_its_display_name():
    voices = [{"key": "it_IT-paola-medium", "gender": "female", "display_name": "Paola (Roma)"}]

    assert _parse(italian_pack_text(voices=voices)).problems == ()


@pytest.mark.parametrize("display_name", ["", "x" * 41, 7])
def test_a_display_name_has_one_to_forty_characters(display_name):
    voices = [{"key": "it_IT-paola-medium", "gender": "female", "display_name": display_name}]

    (text,) = _problem_texts(_parse(italian_pack_text(voices=voices)))
    assert "display_name" in text


def test_a_pack_for_another_language_is_refused():
    (text,) = _problem_texts(_parse(italian_pack_text(), code="fr"))

    assert "fr" in text


def test_missing_lists_the_absent_paths_of_a_partial_pack():
    pack = _parse('code = "es"\n[evaluation]\nloanwords = ["ok"]\n', code="es")

    missing = pack.missing()

    assert "evaluation.loanwords" not in missing
    assert "evaluation.turns" in missing and "name" in missing
    assert "code" not in missing and "order" not in missing


def test_merging_replaces_only_the_items_in_the_pack(workspace):
    spanish = read_language("es", workspace)
    pack = _parse('code = "es"\n[podcast]\nsample_line = "¡Hola, soy {name}!"\n', code="es")

    merged = pack.merged_onto(spanish)

    assert merged.get("podcast.sample_line") == "¡Hola, soy {name}!"
    assert (
        merged.document == spanish.with_value("podcast.sample_line", "¡Hola, soy {name}!").document
    )


def test_merging_tables_keeps_the_keys_the_pack_does_not_name(workspace):
    german = read_language("de", workspace)
    pack = _parse(
        'code = "de"\n[evaluation.turns]\nrent-a-car = ["a", "b", "c", "d", "e"]\n', code="de"
    )

    merged = pack.merged_onto(german)

    assert merged.get("evaluation.turns")["rent-a-car"] == ["a", "b", "c", "d", "e"]
    assert (
        merged.get("evaluation.turns")["buy-train-ticket"]
        == german.get("evaluation.turns")["buy-train-ticket"]
    )


def test_merging_voices_keeps_stored_derived_values(workspace):
    german = read_language("de", workspace)
    voices = '[[voices]]\nkey = "de_DE-thorsten-medium"\ngender = "male"\nspeaking_rate = "slow"\n'
    pack = _parse(f'code = "de"\n{voices}', code="de")

    (voice,) = pack.merged_onto(german).get("voices")

    assert voice["display_name"] == "Thorsten (Germany)" and voice["speaking_rate"] == "slow"


def test_merging_onto_nothing_gives_the_pack_data():
    pack = _parse(italian_pack_text())

    assert pack.merged_onto(None).document == pack.data.document


def test_a_complete_pack_has_no_errors():
    findings = _parse(italian_pack_text()).findings(CONTEXT, others=())

    assert [f for f in findings if f.is_error] == []


def test_todo_and_empty_lists_fail_their_rules():
    podcast = italian_pack_document()["podcast"] | {"sample_line": "TODO", "guest_labels": []}

    findings = _parse(italian_pack_text(podcast=podcast)).findings(CONTEXT, others=())

    assert {f.path for f in findings if f.is_error} == {
        "podcast.sample_line",
        "podcast.guest_labels",
    }


def test_warnings_alone_leave_a_pack_valid():
    voices = [{"key": "it_IT-paola-medium", "gender": "female"}]
    names = {"female": italian_pack_document()["podcast"]["host_names"]["female"]}
    podcast = italian_pack_document()["podcast"] | {"host_names": names}

    findings = _parse(italian_pack_text(voices=voices, podcast=podcast)).findings(
        CONTEXT, others=()
    )

    assert findings and not any(f.is_error for f in findings)


def test_structure_problems_are_part_of_the_findings():
    findings = _parse(italian_pack_text(order=3)).findings(CONTEXT, others=())

    assert any(f.path == "order" and f.is_error for f in findings)


def test_a_new_language_is_checked_against_the_others(workspace):
    german = read_language("de", workspace)

    findings = _parse(italian_pack_text(name="German")).findings(CONTEXT, others=(german,))

    assert any(f.path == "name" and f.is_error for f in findings)


def test_a_new_language_runs_the_onboarding_rules():
    context = fake_context(catalogued_codes=frozenset({"es", "de", "it"}))

    findings = _parse(italian_pack_text()).findings(context, others=(), onboarding=True)

    assert any(f.path == "code" for f in findings)


def test_requirements_can_be_passed_in():
    pack = LanguagePack.parse(italian_pack_text(), "it", REQUIREMENTS[:2])

    assert pack.missing() == ()


def test_data_is_language_data():
    assert isinstance(_parse(italian_pack_text()).data, LanguageData)
