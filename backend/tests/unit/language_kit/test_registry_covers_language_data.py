"""T025: the guard. Every per-language record field has a requirement, and back (FR-010, SC-005)."""

from dataclasses import fields

from app.language_data import LanguageRecord, PodcastRecord, VoiceRecord
from language_kit.registry import REQUIREMENTS, orphan_requirements, uncovered_fields
from tests.integration.practice_languages.evaluation_set import EvaluationSet

PATHS = tuple(item.path for item in REQUIREMENTS)


def _record_fields(*records: type) -> dict[str, tuple[str, ...]]:
    return {record.__name__: tuple(field.name for field in fields(record)) for record in records}


RECORDS = _record_fields(LanguageRecord, VoiceRecord, PodcastRecord, EvaluationSet)


def test_every_language_data_field_has_a_requirement():
    missing = uncovered_fields(RECORDS, PATHS)

    assert not missing, "\n".join(missing)


def test_every_requirement_has_a_language_data_field():
    orphans = orphan_requirements(RECORDS, PATHS)

    assert not orphans, "\n".join(orphans)


def test_a_new_field_without_a_requirement_is_named_with_what_to_do():
    records = RECORDS | {"PodcastRecord": (*RECORDS["PodcastRecord"], "example_only_field")}

    assert uncovered_fields(records, PATHS) == [
        "`PodcastRecord.example_only_field` is per-language data with no entry in "
        "`language_kit/registry.py`. Add a Requirement for it (see the language-kit skill, "
        "'Adding a per-language requirement')"
    ]


def test_a_requirement_without_a_field_is_named():
    (orphan,) = orphan_requirements(RECORDS, (*PATHS, "podcast.example_only_field"))

    assert "`podcast.example_only_field`" in orphan
