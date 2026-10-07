"""T040: pack text generated from the registry, with guidance before every item (contracts/pack-format.md)."""

import re
import tomllib

from language_kit.checking import catalogued_languages
from language_kit.pack import LanguagePack
from language_kit.registry import REQUIREMENTS, Destination, Producer, Requirement
from language_kit.rules import Required
from language_kit.template import TemplateSources, full_pack, partial_pack
from tests.unit.language_kit.conftest import SCENARIO_IDS, fake_context
from tests.unit.language_kit.fakes import candidate

CANDIDATES = (candidate("it_IT-paola-medium"), candidate("it_IT-riccardo-x_low", megabytes=28))
GUIDANCE_HEADER = re.compile(r"^# ── (\S+) ─+ (\w+) · needed by (\d+)$", re.MULTILINE)


def _sources(workspace, requirements=REQUIREMENTS) -> TemplateSources:
    return TemplateSources(catalogued_languages(workspace), fake_context(), requirements)


def _italian(workspace, requirements=REQUIREMENTS) -> str:
    return full_pack("it", "Italian", _sources(workspace, requirements), CANDIDATES)


def _block(text: str, path: str) -> str:
    start = text.index(f"# ── {path} ")
    following = GUIDANCE_HEADER.search(text, start + 1)
    return text[start : following.start() if following else len(text)]


def test_the_full_pack_is_valid_toml_with_code_and_name_filled(workspace):
    document = tomllib.loads(_italian(workspace))

    assert (document["code"], document["name"]) == ("it", "Italian")


def test_unfilled_values_are_todo_or_empty(workspace):
    document = tomllib.loads(_italian(workspace))

    assert document["default_voice"] == "TODO"
    assert document["podcast"]["sample_line"] == "TODO"
    assert document["podcast"]["guest_labels"] == []
    assert document["podcast"]["host_names"] == {"female": [], "male": []}
    assert document["evaluation"]["special_letters"] == "TODO"
    assert document["evaluation"]["dictation"] == [] and document["evaluation"]["loanwords"] == []


def test_turns_hold_an_empty_list_for_every_current_scenario(workspace):
    turns = tomllib.loads(_italian(workspace))["evaluation"]["turns"]

    assert list(turns) == list(SCENARIO_IDS)
    assert all(value == [] for value in turns.values())


def test_every_item_but_the_derived_ones_has_guidance_once(workspace):
    headers = [match.group(1) for match in GUIDANCE_HEADER.finditer(_italian(workspace))]

    assert sorted(headers) == sorted(item.path for item in REQUIREMENTS if item.path != "order")


def test_items_follow_registry_order_with_sub_tables_after_their_table_keys(workspace):
    """TOML puts a table's plain keys before its sub-tables, so `turns` follows the lists."""
    headers = [match.group(1) for match in GUIDANCE_HEADER.finditer(_italian(workspace))]

    assert headers == [
        "code",
        "name",
        "default_voice",
        "voices",
        "voices[].gender",
        "voices[].speaking_rate",
        "podcast.guest_labels",
        "podcast.sample_line",
        "podcast.host_names",
        "evaluation.special_letters",
        "evaluation.dictation",
        "evaluation.loanwords",
        "evaluation.turns",
    ]


def test_a_guidance_block_holds_producer_description_rules_and_example(workspace):
    block = _block(_italian(workspace), "podcast.sample_line")

    assert "agent · needed by 007" in block
    assert "# What a podcast host says when the learner previews their voice." in block
    assert "# Rules: required; contains {name} exactly once; no other braces." in block
    assert '# Example (German): "Hallo, ich bin {name}. Willkommen zur Sendung!"' in block
    assert block.rstrip().endswith('sample_line = "TODO"')


def test_the_example_comes_from_a_passing_language_when_german_fails(workspace):
    path = workspace.runtime_dir / "de.toml"
    path.write_text(
        path.read_text(encoding="utf-8").replace("{name}. Willkommen", "Willkommen"),
        encoding="utf-8",
    )

    block = _block(_italian(workspace), "podcast.sample_line")

    assert '# Example (Spanish): "Hola, soy {name}. ¡Bienvenidos al programa!"' in block


def test_derived_keys_are_never_written(workspace):
    document = tomllib.loads(_italian(workspace))

    assert "order" not in document and "voices" not in document


def test_voice_candidates_are_listed_above_the_voices(workspace):
    block = _block(_italian(workspace), "voices")

    assert re.search(r"#\s+it_IT-paola-medium\s+it_IT\s+Italy\s+medium\s+60 MB", block)
    assert re.search(r"#\s+it_IT-riccardo-x_low\s+it_IT\s+Italy\s+x_low\s+28 MB", block)


def test_the_voices_guidance_says_display_name_may_override_the_derived_name(workspace):
    text = _italian(workspace)

    assert "display_name" in _block(text, "voices[].speaking_rate") + _block(text, "voices")


def test_a_filled_template_validates(workspace):
    text = _italian(workspace)

    pack = LanguagePack.parse(text, "it")

    assert pack.problems == ()
    assert "default_voice" in {
        f.path for f in pack.findings(fake_context(), others=()) if f.is_error
    }


def test_a_partial_pack_holds_code_and_only_the_given_items(workspace):
    sources = _sources(workspace)
    spanish = sources.languages["es"]

    text = partial_pack(
        spanish, {"podcast.sample_line": None, "evaluation.loanwords": None}, sources
    )

    assert tomllib.loads(text) == {
        "code": "es",
        "podcast": {"sample_line": "TODO"},
        "evaluation": {"loanwords": []},
    }


def test_a_partial_table_holds_only_the_named_keys(workspace):
    sources = _sources(workspace)

    text = partial_pack(sources.languages["de"], {"evaluation.turns": ("rent-a-car",)}, sources)

    assert tomllib.loads(text) == {"code": "de", "evaluation": {"turns": {"rent-a-car": []}}}


def test_a_partial_voice_item_lists_every_voice_by_key(workspace):
    sources = _sources(workspace)

    text = partial_pack(sources.languages["de"], {"voices[].gender": None}, sources)

    assert tomllib.loads(text)["voices"] == [
        {"key": "de_DE-thorsten-medium", "gender": "TODO"},
        {"key": "de_DE-kerstin-low", "gender": "TODO"},
    ]


def test_a_new_requirement_appears_with_no_other_change(workspace):
    greeting = Requirement(
        "podcast.greeting",
        Destination.RUNTIME,
        Producer.AGENT,
        "009",
        "How a host opens a show.",
        (Required(),),
    )

    before = _italian(workspace)
    after = _italian(workspace, (*REQUIREMENTS, greeting))

    assert "# ── podcast.greeting " in after
    assert tomllib.loads(after)["podcast"]["greeting"] == "TODO"
    assert after.replace(_block(after, "podcast.greeting"), "") == before
