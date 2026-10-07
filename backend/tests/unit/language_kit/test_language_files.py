"""T027: a catalogued language's two data files, read as values addressed by registry path."""

from language_kit.language_files import LanguageData, catalogued_codes, read_language
from language_kit.registry import REQUIREMENTS
from language_kit.workspace import Workspace


def test_runtime_values_are_addressed_by_registry_path(workspace: Workspace):
    german = read_language("de", workspace)

    assert german.code == "de"
    assert german.get("name") == "German"
    assert german.get("podcast.sample_line") == "Hallo, ich bin {name}. Willkommen zur Sendung!"
    assert german.get("voices[].gender") == ["male", "female"]


def test_evaluation_values_sit_under_evaluation(workspace: Workspace):
    german = read_language("de", workspace)

    assert german.get("evaluation.special_letters") == "äöüß"
    assert len(german.get("evaluation.dictation")) == 20


def test_without_an_evaluation_file_every_evaluation_path_is_none(workspace: Workspace):
    (workspace.evaluation_dir / "de.toml").unlink()
    german = read_language("de", workspace)

    evaluation = [item.path for item in REQUIREMENTS if item.path.startswith("evaluation.")]
    assert [german.get(path) for path in evaluation] == [None] * len(evaluation)


def test_items_of_a_list_path_carry_their_index():
    language = LanguageData("it", {"voices": [{"gender": "female"}, {}]})

    assert language.items("voices[].gender") == [
        ("voices[0].gender", "female"),
        ("voices[1].gender", None),
    ]


def test_items_of_a_list_path_are_empty_when_the_list_is_malformed():
    assert LanguageData("it", {"voices": "x"}).items("voices[].gender") == []


def test_a_missing_path_is_none():
    assert LanguageData("it", {}).get("podcast.sample_line") is None


def test_with_value_and_without_leave_the_original_unchanged():
    original = LanguageData("it", {"podcast": {"sample_line": "a"}})

    changed = original.with_value("podcast.guest_labels", ["Ospite"]).without("podcast.sample_line")

    assert changed.get("podcast.guest_labels") == ["Ospite"]
    assert changed.get("podcast.sample_line") is None
    assert original.get("podcast.sample_line") == "a"


def test_catalogued_codes_follow_the_order_values(workspace: Workspace):
    assert catalogued_codes(workspace) == ("es", "de")


def test_a_malformed_file_reads_as_empty_data(workspace: Workspace):
    (workspace.runtime_dir / "de.toml").write_text("oops =", encoding="utf-8")

    assert read_language("de", workspace).get("name") is None
