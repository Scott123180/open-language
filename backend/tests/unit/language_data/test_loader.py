"""T007: the strict loader for practice-language data files (contracts/data-files.md)."""

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from app.language_data import LanguageDataError, load_language_records

ALPHA = """\
code = "aa"
name = "Alpha"
order = 2
default_voice = "aa_AA-one-medium"

[[voices]]
key = "aa_AA-one-medium"
display_name = "One (Alphaland)"
gender = "female"
locale = "aa_AA"
quality = "medium"
speaking_rate = "natural"

[podcast]
guest_labels = ["Guest"]
sample_line = "Hi, I am {name}."

[podcast.host_names]
female = ["Ana", "Bea"]
"""
BETA = (
    ALPHA.replace('"aa"', '"bb"')
    .replace("aa_AA", "bb_BB")
    .replace("Alpha", "Beta")
    .replace("order = 2", "order = 1")
)


def _write(directory: Path, stem: str, text: str) -> Path:
    path = directory / f"{stem}.toml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.fixture
def two_languages(tmp_path: Path) -> Path:
    _write(tmp_path, "aa", ALPHA)
    _write(tmp_path, "bb", BETA)
    return tmp_path


def _error_for(tmp_path: Path, stem: str, text: str) -> str:
    _write(tmp_path, stem, text)
    with pytest.raises(LanguageDataError) as error:
        load_language_records(tmp_path)
    return str(error.value)


def test_records_are_sorted_by_order(two_languages):
    assert [record.code for record in load_language_records(two_languages)] == ["bb", "aa"]


def test_a_record_holds_every_value_of_its_file(tmp_path):
    _write(tmp_path, "aa", ALPHA)

    (record,) = load_language_records(tmp_path)

    assert (record.code, record.name, record.order) == ("aa", "Alpha", 2)
    assert record.voices[0].display_name == "One (Alphaland)"
    assert dict(record.podcast.host_names) == {"female": ("Ana", "Bea")}
    assert record.podcast.guest_labels == ("Guest",)


def test_an_unknown_key_names_the_file_and_the_key(tmp_path):
    message = _error_for(tmp_path, "aa", ALPHA + 'greeting = "Hi"\n')

    assert "aa.toml" in message and "greeting" in message


def test_an_unknown_voice_key_names_it(tmp_path):
    message = _error_for(tmp_path, "aa", ALPHA.replace('speaking_rate = "natural"', 'pitch = "x"'))

    assert "pitch" in message


def test_a_missing_key_names_the_file_and_the_key(tmp_path):
    message = _error_for(tmp_path, "aa", ALPHA.replace('name = "Alpha"\n', ""))

    assert "aa.toml" in message and "name" in message


def test_a_wrong_type_names_the_key(tmp_path):
    message = _error_for(tmp_path, "aa", ALPHA.replace("order = 2", 'order = "2"'))

    assert "aa.toml" in message and "order" in message


def test_a_non_string_list_item_is_a_wrong_type(tmp_path):
    message = _error_for(tmp_path, "aa", ALPHA.replace('["Guest"]', "[1]"))

    assert "guest_labels" in message


def test_a_toml_syntax_error_names_the_file(tmp_path):
    message = _error_for(tmp_path, "aa", ALPHA + "oops =\n")

    assert "aa.toml" in message


def test_a_duplicate_code_is_refused(two_languages):
    message = _error_for(two_languages, "cc", BETA.replace("order = 1", "order = 3"))

    assert "bb" in message


def test_the_code_must_equal_the_file_stem(tmp_path):
    message = _error_for(tmp_path, "zz", ALPHA)

    assert "zz.toml" in message and "code" in message


def test_a_duplicate_order_is_refused(two_languages):
    message = _error_for(two_languages, "bb", BETA.replace("order = 1", "order = 2"))

    assert "order" in message


def test_a_voice_used_by_two_languages_is_refused(two_languages):
    shared = BETA.replace(
        'default_voice = "bb_BB-one-medium"', 'default_voice = "aa_AA-one-medium"'
    )
    shared = shared.replace('key = "bb_BB-one-medium"', 'key = "aa_AA-one-medium"')

    message = _error_for(two_languages, "bb", shared)

    assert "aa_AA-one-medium" in message


def test_the_default_voice_must_be_one_of_the_voices(tmp_path):
    message = _error_for(
        tmp_path, "aa", ALPHA.replace('default_voice = "aa_AA-one-medium"', 'default_voice = "x"')
    )

    assert "default_voice" in message


def test_a_voice_locale_must_start_with_the_language_code(tmp_path):
    message = _error_for(tmp_path, "aa", ALPHA.replace('locale = "aa_AA"', 'locale = "bb_BB"'))

    assert "locale" in message


def test_records_are_frozen(tmp_path):
    _write(tmp_path, "aa", ALPHA)
    (record,) = load_language_records(tmp_path)

    with pytest.raises(FrozenInstanceError):
        record.name = "Other"  # type: ignore[misc]


def test_host_names_cannot_be_modified(tmp_path):
    _write(tmp_path, "aa", ALPHA)
    (record,) = load_language_records(tmp_path)

    with pytest.raises(TypeError):
        record.podcast.host_names["male"] = ("Bo",)  # type: ignore[index]


def test_the_default_directory_holds_the_committed_languages():
    assert {record.code for record in load_language_records()} >= {"es", "de"}
